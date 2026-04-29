"""
Reddit-Pipeline – Posts aus konfigurierten Subreddits holen und in Supabase speichern.

Für jeden Subreddit in sources.yaml (Abschnitt 'reddit'):
  1. PRAW-Client initialisieren (read-only, script-App)
  2. hot + new Posts holen (je post_limit)
  3. Duplikaterkennung via reddit_post_id (Reddit's eigene ID)
  4. Neue Posts in reddit_posts speichern

Aufruf:
    from app.services.reddit_fetcher import fetch_all_reddit
    stats = fetch_all_reddit()
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.config import settings

SOURCES_YAML = Path(__file__).resolve().parent.parent.parent / "sources.yaml"

# Maximales Alter eines Posts in Tagen
MAX_POST_AGE_DAYS = 2


def _get_reddit_client():
    """Erstellt einen read-only PRAW-Client."""
    try:
        import praw
    except ImportError:
        raise RuntimeError("praw ist nicht installiert. Bitte: pip install praw")

    if not settings.reddit_configured:
        raise RuntimeError(
            "REDDIT_CLIENT_ID und/oder REDDIT_CLIENT_SECRET nicht gesetzt."
        )

    return praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
        # read_only=True → kein Login nötig
    )


def _load_reddit_sources() -> list[dict]:
    """Liest den 'reddit'-Abschnitt aus sources.yaml."""
    if not SOURCES_YAML.exists():
        return []
    with open(SOURCES_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("reddit", [])


def _fetch_subreddit(
    reddit,
    source: dict,
    known_ids: set[str],
) -> list[dict[str, Any]]:
    """Holt hot + new Posts eines Subreddits, gibt neue Posts zurück."""
    subreddit_name = source["subreddit"]
    post_limit = source.get("post_limit", 10)
    sort_types = source.get("sort", ["hot", "new"])
    language = source.get("language", "en")

    try:
        sub = reddit.subreddit(subreddit_name)
    except Exception as exc:
        print(f"    ✗ r/{subreddit_name}: {exc}")
        return []

    cutoff_ts = (
        datetime.now(tz=timezone.utc).timestamp()
        - MAX_POST_AGE_DAYS * 86400
    )

    posts: list[dict[str, Any]] = []
    seen_in_run: set[str] = set()

    for sort_type in sort_types:
        try:
            if sort_type == "hot":
                listing = sub.hot(limit=post_limit)
            elif sort_type == "new":
                listing = sub.new(limit=post_limit)
            else:
                continue

            for submission in listing:
                # Altersfilter
                if submission.created_utc < cutoff_ts:
                    continue

                rid = submission.id
                # Duplikat innerhalb dieses Laufs (hot + new können überlappen)
                if rid in seen_in_run or rid in known_ids:
                    continue
                seen_in_run.add(rid)

                selftext = (submission.selftext or "").strip()
                # [deleted] / [removed] ignorieren
                if selftext in ("[deleted]", "[removed]"):
                    selftext = ""

                posts.append(
                    {
                        "reddit_post_id": rid,
                        "subreddit": subreddit_name,
                        "title": submission.title.strip(),
                        "url": submission.url if not submission.is_self else None,
                        "permalink": f"https://www.reddit.com{submission.permalink}",
                        "selftext": selftext[:8000] if selftext else None,
                        "author": str(submission.author) if submission.author else "[deleted]",
                        "flair": submission.link_flair_text or None,
                        "score": submission.score,
                        "upvote_ratio": submission.upvote_ratio,
                        "num_comments": submission.num_comments,
                        "sort_type": sort_type,
                        "language": language,
                    }
                )

        except Exception as exc:
            print(f"    ✗ r/{subreddit_name} ({sort_type}): {exc}")

    return posts


def fetch_all_reddit() -> dict[str, int]:
    """
    Holt Posts aller konfigurierten Reddit-Quellen und speichert neue in der DB.

    Rückgabe: {"fetched": N, "new": N, "skipped": N, "errors": N}
    """
    from app.db.supabase_client import get_supabase

    sources = _load_reddit_sources()
    if not sources:
        print("  Keine Reddit-Quellen in sources.yaml gefunden.")
        return {"fetched": 0, "new": 0, "skipped": 0, "errors": 0}

    if not settings.reddit_configured:
        print("  ⚠  REDDIT_CLIENT_ID/SECRET nicht gesetzt – Reddit-Fetch übersprungen.")
        return {"fetched": 0, "new": 0, "skipped": 0, "errors": 0}

    try:
        reddit = _get_reddit_client()
    except Exception as exc:
        print(f"  ✗ Reddit-Client konnte nicht erstellt werden: {exc}")
        return {"fetched": 0, "new": 0, "skipped": 0, "errors": 1}

    sb = get_supabase()

    # Alle bekannten Post-IDs einmalig laden
    known_res = sb.table("reddit_posts").select("reddit_post_id").execute()
    known_ids: set[str] = {r["reddit_post_id"] for r in known_res.data if r.get("reddit_post_id")}

    total_fetched = 0
    total_new = 0
    total_skipped = 0
    total_errors = 0

    for source in sources:
        name = source.get("name", f"r/{source.get('subreddit', '?')}")
        print(f"  ← {name}", end=" … ", flush=True)

        posts = _fetch_subreddit(reddit, source, known_ids)

        if posts is None:
            total_errors += 1
            print("✗")
            continue

        total_fetched += len(posts)
        skipped = 0

        # Noch einmal gegen known_ids prüfen (andere Subreddits könnten denselben Post haben)
        new_posts = []
        for p in posts:
            if p["reddit_post_id"] in known_ids:
                skipped += 1
            else:
                known_ids.add(p["reddit_post_id"])
                new_posts.append(p)

        total_skipped += skipped

        if new_posts:
            sb.table("reddit_posts").insert(new_posts).execute()
            total_new += len(new_posts)

        print(f"✓  {len(new_posts)} neu, {skipped} bekannt  ({len(posts)} gesamt)")

    print(
        f"\n  Gesamt: {total_fetched} geladen, "
        f"{total_new} neu gespeichert, "
        f"{total_skipped} übersprungen, "
        f"{total_errors} Fehler."
    )

    return {
        "fetched": total_fetched,
        "new": total_new,
        "skipped": total_skipped,
        "errors": total_errors,
    }
