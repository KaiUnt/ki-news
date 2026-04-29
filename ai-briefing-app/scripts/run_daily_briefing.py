#!/usr/bin/env python3
"""
Täglicher Briefing-Runner – wird per Cronjob um 07:00 aufgerufen.

Crontab-Eintrag:
    0 7 * * * /path/to/venv/bin/python /path/to/ai-briefing-app/scripts/run_daily_briefing.py

Phasen:
    Phase 2: Artikel via RSS sammeln + Duplikate erkennen
    Phase 3: Artikel mit OpenAI analysieren + Scores speichern
    Phase 4: Tagesbriefing generieren + in DB schreiben
"""

import sys
from pathlib import Path

# Projekt-Root zum Python-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db.supabase_client import check_connection


def main() -> int:
    print("=" * 50)
    print("KI-News Briefing – Täglicher Lauf")
    print("=" * 50)

    # Voraussetzungen prüfen
    if not settings.supabase_configured:
        print("✗ DATABASE_URL nicht gesetzt. Abbruch.")
        return 1

    if not check_connection():
        print("✗ Datenbank nicht erreichbar. Abbruch.")
        return 1

    if not settings.openai_configured:
        print("⚠  OPENAI_API_KEY nicht gesetzt – KI-Analyse wird übersprungen.")

    print("\nPhase 2 – Artikel sammeln")
    from app.services.source_fetcher import fetch_all_sources
    from app.services.source_loader import load_sources_from_yaml
    load_sources_from_yaml()
    fetch_all_sources()

    print("Phase 3 – KI-Analyse")
    from app.services.ai_analyzer import analyze_new_articles
    analyze_new_articles()

    print("Phase 4 – Briefing generieren")
    from app.services.briefing_generator import generate_today
    generate_today()

    print("\nPhase 5 – Reddit sammeln")
    if settings.reddit_configured:
        from app.services.reddit_fetcher import fetch_all_reddit
        fetch_all_reddit()
    else:
        print("  ⚠  REDDIT_CLIENT_ID/SECRET nicht gesetzt – Reddit-Fetch übersprungen.")

    print("Phase 6 – Reddit analysieren")
    if settings.openai_configured and settings.reddit_configured:
        from app.services.reddit_analyzer import analyze_new_reddit_posts
        analyze_new_reddit_posts()
    else:
        print("  ⚠  OpenAI oder Reddit nicht konfiguriert – Reddit-Analyse übersprungen.")

    print("\n✓ Lauf abgeschlossen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
