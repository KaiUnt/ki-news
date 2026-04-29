"""
Lädt Quellen aus sources.yaml in die Datenbank.
Bestehende Quellen (gleiche URL) werden aktualisiert (upsert).
"""

from pathlib import Path
import yaml

SOURCES_YAML = Path(__file__).resolve().parent.parent.parent / "sources.yaml"


def load_sources_from_yaml() -> None:
    """Liest sources.yaml und legt fehlende Quellen in der DB an (upsert bei bestehender URL)."""
    from app.db.supabase_client import get_supabase

    if not SOURCES_YAML.exists():
        print(f"  Keine sources.yaml gefunden unter {SOURCES_YAML}")
        return

    with open(SOURCES_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    entries = data.get("sources", [])
    if not entries:
        return

    try:
        sb = get_supabase()

        to_upsert = [
            {
                "name": s.get("name", s["url"]),
                "url": s["url"],
                "type": s.get("type", "RSS"),
                "category": s.get("category", ""),
                "language": s.get("language", "en"),
                "priority": s.get("priority", 3),
                "is_active": True,
            }
            for s in entries
            if s.get("url")
        ]

        if to_upsert:
            sb.table("sources").upsert(to_upsert, on_conflict="url").execute()

        print(f"✓ Quellen: {len(to_upsert)} synchronisiert (upsert).")
    except Exception as exc:
        print(f"✗ Fehler beim Laden der Quellen: {exc}")
