"""
Reddit KI-Analyse – neue Posts via OpenAI analysieren und in reddit_post_analysis speichern.

Für jeden reddit_post ohne Analyse:
  1. Prompt mit Post-Daten (Titel, Text, Score, Kommentare) bauen
  2. OpenAI JSON-Antwort holen
  3. Ergebnis in reddit_post_analysis speichern

Aufruf:
    from app.services.reddit_analyzer import analyze_new_reddit_posts
    stats = analyze_new_reddit_posts()
"""

import json
import time
from typing import Any

from openai import OpenAI

from app.config import settings
from app.prompts import REDDIT_ANALYSIS_PROMPT

# Maximale Posts pro Lauf (Kostensteuerung)
MAX_POSTS_PER_RUN = 60

# Pause zwischen API-Calls
RATE_LIMIT_SLEEP = 0.5

MODEL = "gpt-4o-mini"


def _get_client() -> OpenAI:
    if not settings.openai_configured:
        raise RuntimeError("OPENAI_API_KEY nicht gesetzt.")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _build_prompt(post: dict) -> str:
    return REDDIT_ANALYSIS_PROMPT.format(
        subreddit=post.get("subreddit", ""),
        title=post.get("title", ""),
        author=post.get("author", ""),
        score=post.get("score", 0),
        upvote_ratio=post.get("upvote_ratio", 0.0),
        num_comments=post.get("num_comments", 0),
        flair=post.get("flair", "") or "–",
        selftext=post.get("selftext", "") or "",
    )


def _call_openai(client: OpenAI, prompt: str) -> dict[str, Any] | None:
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


def _map_to_db(post_id: str, data: dict) -> dict:
    def clamp(val, lo=1, hi=5):
        try:
            return max(lo, min(hi, int(val)))
        except (TypeError, ValueError):
            return 3

    return {
        "post_id": post_id,
        "relevance_score": clamp(data.get("relevanz_score", 3)),
        "practical_value_score": clamp(data.get("praxisnutzen_score", 3)),
        "hype_level": data.get("hype_level", "mittel"),
        "priority": data.get("prioritaet", "mittel"),
        "category": data.get("kategorie", ""),
        "summary_de": data.get("zusammenfassung_de", ""),
        "why_important": data.get("warum_wichtig", ""),
        "practical_relevance": data.get("praktische_relevanz", ""),
        "community_signal": data.get("community_signal", ""),
        "kai_relevance": data.get("kai_relevanz", ""),
    }


def analyze_new_reddit_posts() -> dict[str, int]:
    """
    Analysiert alle Reddit-Posts ohne Analyse-Eintrag via OpenAI.

    Rückgabe: {"analyzed": N, "skipped": N, "errors": N}
    """
    from app.db.supabase_client import get_supabase

    if not settings.openai_configured:
        print("  ⚠  OPENAI_API_KEY nicht gesetzt – Reddit-Analyse übersprungen.")
        return {"analyzed": 0, "skipped": 0, "errors": 0}

    sb = get_supabase()

    # Posts ohne Analyse laden (LEFT JOIN via Supabase: nicht-existente Analyse)
    # Supabase unterstützt kein direktes LEFT JOIN – daher: alle post_ids aus Analyse laden
    analyzed_res = sb.table("reddit_post_analysis").select("post_id").execute()
    analyzed_ids: set[str] = {r["post_id"] for r in analyzed_res.data if r.get("post_id")}

    posts_res = (
        sb.table("reddit_posts")
        .select("id, subreddit, title, author, score, upvote_ratio, num_comments, flair, selftext")
        .order("score", desc=True)
        .limit(MAX_POSTS_PER_RUN + len(analyzed_ids))
        .execute()
    )

    posts = [p for p in posts_res.data if p["id"] not in analyzed_ids][:MAX_POSTS_PER_RUN]

    if not posts:
        print("  Keine neuen Reddit-Posts zur Analyse vorhanden.")
        return {"analyzed": 0, "skipped": 0, "errors": 0}

    print(f"  {len(posts)} Reddit-Posts zur Analyse.\n")

    client = _get_client()
    total_analyzed = 0
    total_errors = 0

    for post in posts:
        title_short = post["title"][:60] + "…" if len(post["title"]) > 60 else post["title"]
        print(f"    → r/{post['subreddit']}: {title_short}", end=" … ", flush=True)

        prompt = _build_prompt(post)
        result = _call_openai(client, prompt)

        if result is None:
            total_errors += 1
            print("✗")
            continue

        db_row = _map_to_db(post["id"], result)

        try:
            sb.table("reddit_post_analysis").insert(db_row).execute()
            total_analyzed += 1
            score = db_row["relevance_score"]
            print(f"✓  Relevanz {score}/5")
        except Exception as exc:
            print(f"✗  DB-Fehler: {exc}")
            total_errors += 1

        time.sleep(RATE_LIMIT_SLEEP)

    print(
        f"\n  Reddit-Analyse: {total_analyzed} analysiert, "
        f"{total_errors} Fehler."
    )

    return {
        "analyzed": total_analyzed,
        "skipped": 0,
        "errors": total_errors,
    }
