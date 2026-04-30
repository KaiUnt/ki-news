"""
Phase 3 – KI-Analyse neuer Artikel via OpenAI.

Für jeden Artikel ohne article_analysis-Eintrag:
  1. Prompt mit Titel + Zusammenfassung bauen
  2. OpenAI strukturierte JSON-Antwort holen
  3. Ergebnis in article_analysis speichern

Aufruf:
    from app.services.ai_analyzer import analyze_new_articles
    stats = analyze_new_articles()
"""

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from openai import OpenAI

from app.config import settings
from app.prompts import ARTICLE_ANALYSIS_PROMPT

# Maximale Anzahl Artikel pro Lauf (Kostensteuerung)
MAX_ARTICLES_PER_RUN = 50

# Pause zwischen API-Calls (Rate-Limit-Schutz)
RATE_LIMIT_SLEEP = 0.5  # Sekunden

# OpenAI-Modell
MODEL = "gpt-4o-mini"


def _get_client() -> OpenAI:
    if not settings.openai_configured:
        raise RuntimeError("OPENAI_API_KEY nicht gesetzt.")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _build_prompt(article: dict) -> str:
    return ARTICLE_ANALYSIS_PROMPT.format(
        title=article.get("title", ""),
        source=article.get("source_name", ""),
        published_at=article.get("published_at", ""),
        summary=article.get("summary_raw", "") or "",
        content=article.get("content", "") or "",
    )


def _call_openai(client: OpenAI, prompt: str) -> dict[str, Any] | None:
    """Ruft OpenAI auf und gibt geparste JSON-Antwort zurück, oder None bei Fehler."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"      ✗ JSON-Fehler: {exc}")
        return None
    except Exception as exc:
        print(f"      ✗ OpenAI-Fehler: {exc}")
        return None


def _map_to_db(article_id: str, data: dict) -> dict:
    """Mapped OpenAI-Antwort auf article_analysis-Tabellenstruktur."""
    def clamp(val, lo=1, hi=5):
        try:
            return max(lo, min(hi, int(val)))
        except (TypeError, ValueError):
            return 3

    return {
        "article_id": article_id,
        "relevance_score": clamp(data.get("relevanz_score", 3)),
        "practical_value_score": clamp(data.get("praxisnutzen_score", 3)),
        "hype_level": data.get("hype_level", "mittel"),
        "priority": data.get("prioritaet", "mittel"),
        "category": data.get("kategorie", ""),
        "summary_de": data.get("zusammenfassung_de", ""),
        "why_important": data.get("warum_wichtig", ""),
        "practical_relevance": data.get("praktische_relevanz", ""),
        "kai_relevance": data.get("kai_relevanz", ""),
        "what_happened": data.get("was_passiert", ""),
        "for_whom": data.get("fuer_wen_relevant", ""),
        "hype_or_substance": data.get("hype_oder_substanz", ""),
    }


def analyze_new_articles(max_articles: int = MAX_ARTICLES_PER_RUN) -> dict[str, int]:
    """
    Analysiert alle Artikel ohne vorhandene article_analysis.
    Limitiert auf max_articles pro Lauf.

    Rückgabe: {"analyzed": N, "skipped": N, "errors": N}
    """
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    client = _get_client()

    # arXiv-Quellen aus Mainstream-Analyse ausschließen
    arxiv_res = sb.table("sources").select("id").eq("type", "arXiv").execute()
    arxiv_source_ids = [r["id"] for r in arxiv_res.data]

    # Nur Artikel der letzten 24h betrachten – ein Lauf pro Tag reicht.
    fetch_cutoff = (
        datetime.now(tz=timezone.utc) - timedelta(hours=24)
    ).isoformat()

    query = (
        sb.table("articles")
        .select("id, title, summary_raw, content, published_at, source_id, sources(name)")
        .eq("is_duplicate", False)
        .gte("fetched_at", fetch_cutoff)
        .order("published_at", desc=True)
    )
    if arxiv_source_ids:
        query = query.not_.in_("source_id", arxiv_source_ids)
    articles_res = query.execute()

    if not articles_res.data:
        print("  Keine Artikel in der DB.")
        return {"analyzed": 0, "skipped": 0, "errors": 0}

    # Analyse-Status nur für diese Kandidaten abfragen
    # In Chunks aufteilen, da PostgREST bei großen .in_()-Listen 400 zurückgibt
    candidate_ids = [a["id"] for a in articles_res.data]
    CHUNK_SIZE = 100
    analyzed_ids: set[str] = set()
    for chunk_start in range(0, len(candidate_ids), CHUNK_SIZE):
        chunk = candidate_ids[chunk_start : chunk_start + CHUNK_SIZE]
        chunk_res = (
            sb.table("article_analysis")
            .select("article_id")
            .in_("article_id", chunk)
            .execute()
        )
        analyzed_ids.update(row["article_id"] for row in chunk_res.data)

    # Noch nicht analysierte Artikel filtern, auf max_articles begrenzen
    to_analyze = [
        a for a in articles_res.data
        if a["id"] not in analyzed_ids
    ][:max_articles]

    if not to_analyze:
        print("  Keine neuen Artikel zur Analyse.")
        return {"analyzed": 0, "skipped": 0, "errors": 0}

    print(f"  {len(to_analyze)} Artikel zur Analyse (Modell: {MODEL}).\n")

    analyzed = 0
    errors = 0

    for i, article in enumerate(to_analyze, 1):
        title = article.get("title", "")[:60]
        print(f"  [{i:3}/{len(to_analyze)}] {title:<60}", end=" … ", flush=True)

        # Source-Name aus Join
        source_info = article.get("sources") or {}
        article["source_name"] = source_info.get("name", "") if isinstance(source_info, dict) else ""

        prompt = _build_prompt(article)
        result = _call_openai(client, prompt)

        if result is None:
            errors += 1
            print("✗")
            continue

        db_row = _map_to_db(article["id"], result)

        try:
            sb.table("article_analysis").insert(db_row).execute()
            score = db_row["relevance_score"]
            prio = db_row["priority"]
            print(f"✓  Relevanz {score}/5  Priorität {prio}")
            analyzed += 1
        except Exception as exc:
            print(f"✗ DB: {exc}")
            errors += 1

        if i < len(to_analyze):
            time.sleep(RATE_LIMIT_SLEEP)

    skipped = len(articles_res.data) - len(to_analyze)
    print(
        f"\n  Gesamt: {analyzed} analysiert, "
        f"{skipped} bereits analysiert/übersprungen, "
        f"{errors} Fehler."
    )
    return {"analyzed": analyzed, "skipped": skipped, "errors": errors}
