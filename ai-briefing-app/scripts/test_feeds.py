#!/usr/bin/env python3
"""
Feed-Test – prüft welche Quellen aus sources.yaml erreichbar sind.
Kein DB-Zugriff nötig. Einfach ausführen:

    python scripts/test_feeds.py

Optionale Filter:
    python scripts/test_feeds.py --only-ok       # nur funktionierende Feeds
    python scripts/test_feeds.py --verbose        # erste 3 Artikel pro Feed zeigen
"""

import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml
import feedparser

SOURCES_YAML = ROOT / "sources.yaml"
TIMEOUT = 15  # Sekunden pro Feed


def parse_date(entry) -> str:
    """Gibt publizierten Datum als String zurück, oder '-' falls nicht vorhanden."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None)
        if parsed:
            try:
                dt = datetime(*parsed[:6], tzinfo=timezone.utc)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    return "-"


def test_feed(source: dict, verbose: bool) -> dict:
    """Testet eine einzelne Quelle und gibt Ergebnis-Dict zurück."""
    url = source["url"]
    name = source["name"]
    result = {
        "name": name,
        "url": url,
        "category": source.get("category", ""),
        "priority": source.get("priority", 3),
        "ok": False,
        "entries": 0,
        "latest_title": "",
        "latest_date": "",
        "error": "",
        "elapsed_ms": 0,
    }

    t0 = time.monotonic()
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "KI-News-Bot/1.0"})
        elapsed = int((time.monotonic() - t0) * 1000)
        result["elapsed_ms"] = elapsed

        # feedparser gibt keinen HTTP-Fehler als Exception – Status prüfen
        status = getattr(feed, "status", 200)
        if status >= 400:
            result["error"] = f"HTTP {status}"
            return result

        entries = feed.entries
        result["entries"] = len(entries)

        if entries:
            result["ok"] = True
            first = entries[0]
            raw_title = getattr(first, "title", "")
            result["latest_title"] = raw_title[:80] + ("…" if len(raw_title) > 80 else "")
            result["latest_date"] = parse_date(first)

            if verbose:
                result["preview"] = [
                    {
                        "title": getattr(e, "title", "")[:80],
                        "date": parse_date(e),
                        "link": getattr(e, "link", ""),
                    }
                    for e in entries[:3]
                ]
        else:
            result["error"] = "Feed leer (0 Einträge)"
    except Exception as exc:
        result["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        result["error"] = str(exc)[:100]

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Testet alle RSS-Feeds aus sources.yaml")
    parser.add_argument("--only-ok", action="store_true", help="Nur funktionierende Feeds anzeigen")
    parser.add_argument("--verbose", "-v", action="store_true", help="Erste 3 Artikel pro Feed zeigen")
    args = parser.parse_args()

    if not SOURCES_YAML.exists():
        print(f"✗ sources.yaml nicht gefunden: {SOURCES_YAML}")
        return 1

    with open(SOURCES_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sources = data.get("sources", [])
    if not sources:
        print("Keine Quellen in sources.yaml gefunden.")
        return 1

    print(f"\nTeste {len(sources)} Feeds …\n")
    print("─" * 80)

    results = []
    ok_count = 0
    total_articles = 0

    for i, source in enumerate(sources, 1):
        name = source.get("name", source["url"])
        sys.stdout.write(f"  [{i:2}/{len(sources)}] {name[:45]:<45} ")
        sys.stdout.flush()

        r = test_feed(source, args.verbose)
        results.append(r)

        if r["ok"]:
            ok_count += 1
            total_articles += r["entries"]
            print(f"✓  {r['entries']:3} Artikel  ({r['elapsed_ms']:4} ms)")
        else:
            print(f"✗  {r['error']}")

    print("\n" + "═" * 80)
    print(f"Ergebnis: {ok_count}/{len(sources)} Feeds OK  │  {total_articles} Artikel total\n")

    # Detailansicht
    ok_results = [r for r in results if r["ok"]]
    fail_results = [r for r in results if not r["ok"]]

    if ok_results and not args.only_ok:
        print("✓ FUNKTIONIERENDE FEEDS")
        print("─" * 80)
        for r in sorted(ok_results, key=lambda x: -x["priority"]):
            print(f"  [{r['priority']}★] {r['name']}")
            print(f"       Kategorie : {r['category']}")
            print(f"       Artikel   : {r['entries']}  │  Neuester: {r['latest_date']}")
            print(f"       Titel     : {r['latest_title']}")
            if args.verbose and "preview" in r:
                for j, p in enumerate(r["preview"], 1):
                    print(f"         {j}. [{p['date']}] {p['title']}")
            print()

    if fail_results:
        print("✗ FEHLERHAFTE FEEDS")
        print("─" * 80)
        for r in fail_results:
            print(f"  {r['name']}")
            print(f"    URL  : {r['url']}")
            print(f"    Grund: {r['error']}")
            print()

    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
