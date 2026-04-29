"""
Supabase Python Client – zentrale Datenbankverbindung.

Konfiguration über SUPABASE_URL + SUPABASE_KEY in .env.
Tabellen einmalig über schema.sql im Supabase SQL-Editor anlegen.
"""

from supabase import create_client, Client
from app.config import settings

_client: Client | None = None


def get_supabase() -> Client:
    """Gibt den Supabase-Client zurück (Singleton, verwendet service_role key)."""
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
            raise RuntimeError(
                "SUPABASE_URL oder SUPABASE_SECRET_KEY nicht konfiguriert. "
                "Bitte .env Datei anlegen (siehe .env.example)."
            )
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
    return _client


def check_connection() -> bool:
    """Gibt True zurück wenn die DB-Verbindung funktioniert."""
    try:
        get_supabase().table("sources").select("id").limit(1).execute()
        return True
    except Exception:
        return False
