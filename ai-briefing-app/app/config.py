import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")           # anon key (public)
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")  # service role (backend)
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "change-me-in-production")

    # Reddit API (script-App, read-only)
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "KI-News-Bot/1.0")

    # Schutz der manuellen Run-Endpunkte (/run, /run-reddit)
    # Wird nur erzwungen wenn APP_ENV=production und RUN_PASSWORD gesetzt ist.
    RUN_PASSWORD: str = os.getenv("RUN_PASSWORD", "")

    @property
    def run_auth_enabled(self) -> bool:
        return self.APP_ENV == "production" and bool(self.RUN_PASSWORD)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SECRET_KEY)

    @property
    def openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def reddit_configured(self) -> bool:
        return bool(self.REDDIT_CLIENT_ID and self.REDDIT_CLIENT_SECRET)


settings = Settings()
