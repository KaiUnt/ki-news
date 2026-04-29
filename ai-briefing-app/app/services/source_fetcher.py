"""
Phase 2 – RSS-Artikel sammeln und in Supabase speichern.

Für jeden aktiven Source-Eintrag in der DB:
  1. RSS-Feed via feedparser laden
  2. SHA-256-Hash je Artikel berechnen (title + url)
  3. Bereits bekannte Hashes überspringen (Duplikaterkennung)
  4. Neue Artikel in articles-Tabelle einfügen

Aufruf:
    from app.services.source_fetcher import fetch_all_sources
    stats = fetch_all_sources()
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

FEED_TIMEOUT = 15  # Sekunden
USER_AGENT = "KI-News-Bot/1.0"

# Maximales Alter eines Artikels – ältere werden ignoriert.
# Täglicher Betrieb: 2 Tage (verhindert historische Artikel beim Fetch).
MAX_ARTICLE_AGE_DAYS = 2


def _make_hash(title: str, url: str) -> str:
    """SHA-256 aus Titel + URL zur Duplikaterkennung."""
    raw = f"{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_published(entry) -> str | None:
    """Gibt ISO-8601-Timestamp zurück oder None."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None)
        if parsed:
            try:
                dt = datetime(*parsed[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
    # Fallback: roher String (z. B. arXiv liefert 'published' als RFC-2822-String)
    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw and isinstance(raw, str):
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(raw)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass
    return None


def _fetch_rss(source: dict) -> list[dict[str, Any]]:
    """Holt einen RSS-Feed und gibt eine Liste normalisierter Artikel zurück."""
    url = source["url"]
    source_id = source["id"]
    language = source.get("language", "en")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=FEED_TIMEOUT,
        )
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as exc:
        print(f"    ✗ {source['name']}: {exc}")
        return []

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS)

    articles = []
    for entry in feed.entries:
        title = (getattr(entry, "title", "") or "").strip()
        link = (getattr(entry, "link", "") or "").strip()

        if not title or not link:
            continue

        published_iso = _parse_published(entry)

        # Altersfilter: Artikel ohne Datum werden trotzdem aufgenommen
        # (manche Feeds liefern kein published_at).
        if published_iso:
            try:
                pub_dt = datetime.fromisoformat(published_iso)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue  # Zu alt – überspringen
            except ValueError:
                pass

        summary = (
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
            or ""
        ).strip()

        # Volltext aus entry.content extrahieren (Atom-Feeds, content:encoded)
        # HTML-Tags werden via BeautifulSoup entfernt, damit der Prompt reinen Text enthält.
        entry_content_list = getattr(entry, "content", None)
        if entry_content_list:
            raw_html = (entry_content_list[0].get("value", "") or "").strip()
            if raw_html:
                content_text = BeautifulSoup(raw_html, "html.parser").get_text(separator=" ", strip=True)
                content_text = content_text[:8000] or None
            else:
                content_text = None
        else:
            content_text = None

        articles.append(
            {
                "source_id": source_id,
                "title": title,
                "url": link,
                "published_at": published_iso,
                "summary_raw": summary[:4000] if summary else None,
                "content": content_text,
                "language": language,
                "hash": _make_hash(title, link),
                "is_duplicate": False,
            }
        )

    return articles


def fetch_all_sources() -> dict[str, int]:
    """
    Holt alle aktiven Quellen aus der DB, lädt deren RSS-Feeds
    und speichert neue Artikel.

    Rückgabe: {"fetched": N, "new": N, "skipped": N, "errors": N}
    """
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Aktive Quellen laden
    sources_res = sb.table("sources").select("*").eq("is_active", True).execute()
    sources = sources_res.data
    if not sources:
        print("  Keine aktiven Quellen in der DB gefunden.")
        return {"fetched": 0, "new": 0, "skipped": 0, "errors": 0}

    print(f"  {len(sources)} aktive Quellen geladen.\n")

    # Bekannte Hashes nur für aktuelle Artikel laden (skaliert mit wachsender DB)
    hash_cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS + 1)).isoformat()
    hashes_res = sb.table("articles").select("hash").gte("fetched_at", hash_cutoff).execute()
    known_hashes: set[str] = {row["hash"] for row in hashes_res.data if row.get("hash")}

    total_fetched = 0
    total_new = 0
    total_skipped = 0
    total_errors = 0

    for source in sources:
        print(f"  ← {source['name']}", end=" … ", flush=True)

        articles = _fetch_rss(source)
        if not articles:
            total_errors += 1
            print("✗")
            continue

        total_fetched += len(articles)

        # Nur neue Artikel einfügen
        new_articles = [a for a in articles if a["hash"] not in known_hashes]
        skipped = len(articles) - len(new_articles)
        total_skipped += skipped

        if new_articles:
            # Hashes sofort merken damit Duplikate innerhalb eines Laufs erkannt werden
            for a in new_articles:
                known_hashes.add(a["hash"])

            sb.table("articles").insert(new_articles).execute()
            total_new += len(new_articles)

        print(f"✓  {len(new_articles)} neu, {skipped} bekannt  ({len(articles)} gesamt)")

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
