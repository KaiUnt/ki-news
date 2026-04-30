"""
Phase 4 – Tagesbriefing generieren.

Nimmt alle analysierten Artikel des heutigen Tages,
schickt die Top-Kandidaten an OpenAI und speichert das
fertige Briefing + briefing_items in Supabase.

Aufruf:
    from app.services.briefing_generator import generate_today
    result = generate_today()
"""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from openai import OpenAI

from app.config import settings
from app.prompts import BRIEFING_GENERATION_PROMPT

MODEL = "gpt-4o-mini"

# Maximale Artikel die ans Modell geschickt werden (Token-Limit)
MAX_INPUT_ARTICLES = 40


def _get_client() -> OpenAI:
    if not settings.openai_configured:
        raise RuntimeError("OPENAI_API_KEY nicht gesetzt.")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _call_openai(client: OpenAI, prompt: str) -> dict[str, Any] | None:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"  ✗ JSON-Fehler: {exc}")
        return None
    except Exception as exc:
        print(f"  ✗ OpenAI-Fehler: {exc}")
        return None


def generate_today(target_date: date | None = None) -> dict[str, Any] | None:
    """
    Generiert das Briefing für target_date (Standard: heute).
    Gibt das gespeicherte Briefing-Dict zurück oder None bei Fehler.
    """
    from app.db.supabase_client import get_supabase

    if target_date is None:
        target_date = date.today()

    date_str = target_date.isoformat()
    sb = get_supabase()

    # Existiert bereits ein Briefing für heute?
    existing = sb.table("briefings").select("id, created_at").eq("briefing_date", date_str).execute()
    if existing.data:
        old_id = existing.data[0]["id"]
        old_created_at = existing.data[0]["created_at"]

        # Nur neu generieren wenn es seit dem letzten Briefing neue analysierte Artikel gibt
        new_analyses = (
            sb.table("article_analysis")
            .select("id")
            .gt("created_at", old_created_at)
            .limit(1)
            .execute()
        )
        if not new_analyses.data:
            print(f"  ✓ Briefing für {date_str} ist aktuell – keine neuen Analysen seit letzter Generierung.")
            return None

        # Neue Artikel vorhanden → altes Briefing löschen und neu generieren
        sb.table("briefings").delete().eq("id", old_id).execute()
        print(f"  ↺ {len(new_analyses.data)}+ neue Analysen gefunden – Briefing wird neu generiert.")

    # arXiv-Quellen aus Briefing ausschließen (Research-Seite behandelt diese separat)
    arxiv_res = sb.table("sources").select("id").eq("type", "arXiv").execute()
    arxiv_source_ids = [r["id"] for r in arxiv_res.data]

    # Analysierte Artikel der letzten 2 Tage laden (fetched heute oder gestern)
    since = (datetime.combine(target_date, datetime.min.time()) - timedelta(days=1)).replace(tzinfo=timezone.utc).isoformat()
    until = (datetime.combine(target_date, datetime.max.time())).replace(tzinfo=timezone.utc).isoformat()

    query = (
        sb.table("articles")
        .select("id, title, url, published_at, summary_raw, sources(name), article_analysis(*)")
        .eq("is_duplicate", False)
        .gte("fetched_at", since)
        .lte("fetched_at", until)
    )
    if arxiv_source_ids:
        query = query.not_.in_("source_id", arxiv_source_ids)
    articles_res = query.execute()

    articles = articles_res.data
    if not articles:
        print(f"  ✗ Keine Artikel für {date_str} gefunden.")
        return None

    # Nur Artikel mit Analyse, sortiert nach Relevanz
    analyzed = [
        a for a in articles
        if a.get("article_analysis")
    ]
    analyzed.sort(
        key=lambda a: (
            -(a["article_analysis"].get("relevance_score") or 0),
            -(a["article_analysis"].get("practical_value_score") or 0),
        )
    )

    top = analyzed[:MAX_INPUT_ARTICLES]
    print(f"  {len(articles)} Artikel geladen, {len(analyzed)} analysiert → {len(top)} ans Modell.")

    if not top:
        print("  ✗ Keine analysierten Artikel – Phase 3 zuerst ausführen.")
        return None

    # Kompaktes JSON für den Prompt bauen
    articles_for_prompt = [
        {
            "id": a["id"],
            "titel": a["title"],
            "quelle": (a.get("sources") or {}).get("name", ""),
            "url": a["url"],
            "zusammenfassung": a.get("summary_raw", "") or "",
            "relevanz": (a["article_analysis"] or {}).get("relevance_score", 3),
            "praxisnutzen": (a["article_analysis"] or {}).get("practical_value_score", 3),
            "prioritaet": (a["article_analysis"] or {}).get("priority", "mittel"),
            "kategorie": (a["article_analysis"] or {}).get("category", ""),
            "was_passiert": (a["article_analysis"] or {}).get("summary_de", ""),
            "warum_wichtig": (a["article_analysis"] or {}).get("why_important", ""),
            "praktische_relevanz": (a["article_analysis"] or {}).get("practical_relevance", ""),
            "kai_relevanz": (a["article_analysis"] or {}).get("kai_relevance", ""),
        }
        for a in top
    ]

    prompt = BRIEFING_GENERATION_PROMPT.format(
        articles_json=json.dumps(articles_for_prompt, ensure_ascii=False, indent=2),
        date=target_date.strftime("%d.%m.%Y"),
    )

    print(f"  → OpenAI aufrufen ({MODEL}) …", flush=True)
    briefing_data = _call_openai(_get_client(), prompt)
    if not briefing_data:
        return None

    # article_id → url Mapping für source_url in briefing_items
    url_map = {a["id"]: a["url"] for a in articles}

    # Briefing in DB speichern
    briefing_row = {
        "briefing_date": date_str,
        "title": briefing_data.get("titel", f"KI Briefing – {date_str}"),
        "daily_summary": briefing_data.get("kurzfazit", ""),
        "content_markdown": json.dumps(briefing_data, ensure_ascii=False),
    }
    briefing_res = sb.table("briefings").insert(briefing_row).execute()
    briefing_id = briefing_res.data[0]["id"]
    print(f"  ✓ Briefing gespeichert (id={briefing_id})")

    # article_id → Artikeldaten inkl. Phase-3-Analyse
    analysis_map = {a["id"]: a for a in articles}

    # briefing_items speichern
    items_to_insert = []

    # Top-Meldungen
    for entry in briefing_data.get("top_meldungen", []):
        article_id = entry.get("artikel_id")
        article = analysis_map.get(article_id, {})
        analysis = (article.get("article_analysis") or {})
        items_to_insert.append({
            "briefing_id": briefing_id,
            "article_id": article_id if article_id in url_map else None,
            "rank": entry.get("rang", 99),
            "section": "Top-Meldungen",
            "title": article.get("title", ""),
            "summary": analysis.get("summary_de", ""),
            "importance": entry.get("einschaetzung", analysis.get("why_important", "")),
            "source_url": url_map.get(article_id, entry.get("quelle", "")),
        })

    # Für Kai
    for rank, article_id in enumerate(briefing_data.get("fuer_kai", []), 1):
        items_to_insert.append({
            "briefing_id": briefing_id,
            "article_id": article_id if article_id in url_map else None,
            "rank": rank,
            "section": "Für Kai",
            "title": next((a["title"] for a in articles if a["id"] == article_id), ""),
            "summary": next(
                ((a["article_analysis"] or {}).get("summary_de", "") for a in articles if a["id"] == article_id), ""
            ),
            "importance": "",
            "source_url": url_map.get(article_id, ""),
        })

    # Nur beobachten
    for rank, article_id in enumerate(briefing_data.get("nur_beobachten", []), 1):
        items_to_insert.append({
            "briefing_id": briefing_id,
            "article_id": article_id if article_id in url_map else None,
            "rank": rank,
            "section": "Nur beobachten",
            "title": next((a["title"] for a in articles if a["id"] == article_id), ""),
            "summary": "",
            "importance": "",
            "source_url": url_map.get(article_id, ""),
        })

    # Hype
    for rank, article_id in enumerate(briefing_data.get("hype", []), 1):
        items_to_insert.append({
            "briefing_id": briefing_id,
            "article_id": article_id if article_id in url_map else None,
            "rank": rank,
            "section": "Hype",
            "title": next((a["title"] for a in articles if a["id"] == article_id), ""),
            "summary": "",
            "importance": "",
            "source_url": url_map.get(article_id, ""),
        })

    if items_to_insert:
        sb.table("briefing_items").insert(items_to_insert).execute()

    print(
        f"  ✓ {len(items_to_insert)} Briefing-Items gespeichert "
        f"({len(briefing_data.get('top_meldungen', []))} Top, "
        f"{len(briefing_data.get('fuer_kai', []))} für Kai, "
        f"{len(briefing_data.get('nur_beobachten', []))} beobachten, "
        f"{len(briefing_data.get('hype', []))} Hype)"
    )

    return briefing_row
