"""
KI-News Briefing – FastAPI Hauptanwendung
Phase 1: Grundgerüst, Dashboard, Quellenverwaltung, Supabase-Anbindung
"""

from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Any

from fastapi import FastAPI, Request, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db.supabase_client import get_supabase, check_connection
from app.services.source_loader import load_sources_from_yaml

BASE_DIR = Path(__file__).resolve().parent


# ── Dict → SimpleNamespace für Template-Kompatibilität ───────────────────────

_DATE_FIELDS = {"briefing_date"}
_DATETIME_FIELDS = {"created_at", "fetched_at", "published_at"}


def _parse_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in _DATE_FIELDS and isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    if key in _DATETIME_FIELDS and isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value


def _to_ns(d: dict) -> SimpleNamespace:
    """Rekursiv: Dict → SimpleNamespace damit Templates .attribut nutzen können."""
    obj = SimpleNamespace()
    for k, v in d.items():
        if isinstance(v, list):
            setattr(obj, k, [_to_ns(i) if isinstance(i, dict) else i for i in v])
        elif isinstance(v, dict):
            setattr(obj, k, _to_ns(v))
        else:
            setattr(obj, k, _parse_value(k, v))
    return obj


# ── Lifespan (Startup / Shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("── KI-News Briefing startet ──")
    if settings.supabase_configured:
        load_sources_from_yaml()
    else:
        print("⚠  SUPABASE_URL/KEY nicht gesetzt – DB-Features deaktiviert.")
    yield
    print("── KI-News Briefing beendet ──")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="KI-News Briefing", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _db_error_response(request: Request, error: Exception) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "error.html",
        context={"error": str(error)},
        status_code=503,
    )


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "db": check_connection() if settings.supabase_configured else "not_configured",
        "openai": "configured" if settings.openai_configured else "not_configured",
    }


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    try:
        sb = get_supabase()
        res = (
            sb.table("briefings")
            .select("*, briefing_items(*)")
            .order("briefing_date", desc=True)
            .limit(1)
            .execute()
        )
        briefing = None
        items_by_section: dict = {}
        if res.data:
            raw = res.data[0]
            raw_items = sorted(raw.pop("briefing_items", []), key=lambda x: x.get("rank", 0))
            raw["items"] = raw_items
            briefing = _to_ns(raw)
            for item in raw_items:
                items_by_section.setdefault(item.get("section", ""), []).append(_to_ns(item))

        return templates.TemplateResponse(request, "dashboard.html", context={
            "briefing": briefing,
            "items_by_section": items_by_section,
            "today": date.today(),
        })
    except Exception as exc:
        return _db_error_response(request, exc)


# ── Briefing-Archiv ────────────────────────────────────────────────────────────

@app.get("/briefings", response_class=HTMLResponse)
def briefings_list(request: Request):
    try:
        sb = get_supabase()
        res = (
            sb.table("briefings")
            .select("*, briefing_items(id)")
            .order("briefing_date", desc=True)
            .execute()
        )
        briefings = []
        for raw in res.data:
            raw["items"] = raw.pop("briefing_items", [])
            briefings.append(_to_ns(raw))
        return templates.TemplateResponse(request, "briefings.html", context={
            "briefings": briefings,
        })
    except Exception as exc:
        return _db_error_response(request, exc)


@app.get("/briefings/{briefing_id}", response_class=HTMLResponse)
def briefing_detail(briefing_id: str, request: Request):
    try:
        sb = get_supabase()
        res = (
            sb.table("briefings")
            .select("*, briefing_items(*)")
            .eq("id", briefing_id)
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Briefing nicht gefunden")

        raw = res.data
        raw_items = sorted(raw.pop("briefing_items", []), key=lambda x: x.get("rank", 0))
        raw["items"] = raw_items
        briefing = _to_ns(raw)
        items_by_section: dict = {}
        for item in raw_items:
            items_by_section.setdefault(item.get("section", ""), []).append(_to_ns(item))

        return templates.TemplateResponse(request, "briefing_detail.html", context={
            "briefing": briefing,
            "items_by_section": items_by_section,
        })
    except HTTPException:
        raise
    except Exception as exc:
        return _db_error_response(request, exc)


# ── Quellenverwaltung ──────────────────────────────────────────────────────────

@app.get("/sources", response_class=HTMLResponse)
def sources_list(request: Request):
    try:
        sb = get_supabase()
        res = (
            sb.table("sources")
            .select("*")
            .order("priority", desc=True)
            .order("name")
            .execute()
        )
        sources = [_to_ns(s) for s in res.data]
        categories = sorted({s.category for s in sources if s.category})
        return templates.TemplateResponse(request, "sources.html", context={
            "sources": sources,
            "categories": categories,
        })
    except Exception as exc:
        return _db_error_response(request, exc)


@app.post("/sources", response_class=RedirectResponse)
def add_source(
    name: str = Form(...),
    url: str = Form(...),
    type: str = Form("RSS"),
    category: str = Form(""),
    language: str = Form("en"),
    priority: int = Form(3),
):
    sb = get_supabase()
    existing = sb.table("sources").select("id").eq("url", url).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diese URL ist bereits als Quelle vorhanden.",
        )
    sb.table("sources").insert({
        "name": name,
        "url": url,
        "type": type,
        "category": category,
        "language": language,
        "priority": priority,
        "is_active": True,
    }).execute()
    return RedirectResponse(url="/sources", status_code=303)


@app.post("/sources/{source_id}/toggle", response_class=RedirectResponse)
def toggle_source(source_id: str):
    sb = get_supabase()
    res = sb.table("sources").select("id, is_active").eq("id", source_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Quelle nicht gefunden")
    sb.table("sources").update({"is_active": not res.data["is_active"]}).eq("id", source_id).execute()
    return RedirectResponse(url="/sources", status_code=303)


# ── Artikel ────────────────────────────────────────────────────────────────────

@app.get("/articles", response_class=HTMLResponse)
def articles_list(
    request: Request,
    q: Optional[str] = None,
    date_filter: Optional[str] = None,  # "YYYY-MM-DD" oder "all"
):
    """
    Zeigt Artikel aus der DB.
    Standardmäßig nur Artikel von heute (fetched_at-Datum = heute).
    ?date_filter=all  → alle Artikel
    ?date_filter=YYYY-MM-DD → Artikel eines bestimmten Tages
    """
    try:
        sb = get_supabase()

        # Datumsgrenze bestimmen
        today_str = date.today().isoformat()  # "YYYY-MM-DD"
        if date_filter == "all":
            selected_date = None
        elif date_filter:
            selected_date = date_filter
        else:
            selected_date = today_str  # Standard: heute

        query = (
            sb.table("articles")
            .select("*, sources(name), article_analysis(relevance_score)")
            .eq("is_duplicate", False)
            .order("published_at", desc=True)
            .limit(200)
        )

        # Datumsfilter: fetched_at >= Tagesbeginn AND < nächster Tag
        if selected_date:
            query = (
                query
                .gte("fetched_at", f"{selected_date}T00:00:00+00:00")
                .lt("fetched_at", f"{selected_date}T23:59:59+00:00")
            )

        if q:
            query = query.ilike("title", f"%{q}%")

        res = query.execute()
        articles = []
        for a in res.data:
            a["source"] = a.pop("sources", None)
            a["analysis"] = a.pop("article_analysis", None)
            articles.append(_to_ns(a))

        return templates.TemplateResponse(request, "articles.html", context={
            "articles": articles,
            "q": q or "",
            "date_filter": date_filter or "",
            "selected_date": selected_date or "",
            "today": today_str,
        })
    except Exception as exc:
        return _db_error_response(request, exc)


# ── Manueller Run ──────────────────────────────────────────────────────────────

@app.post("/run", response_class=RedirectResponse)
def run_briefing():
    """
    Löst den täglichen Briefing-Lauf manuell aus (Phase 2–4).
    Danach Redirect zum Dashboard mit Status-Meldung.
    """
    from app.services.source_loader import load_sources_from_yaml
    from app.services.source_fetcher import fetch_all_sources
    from app.services.ai_analyzer import analyze_new_articles
    from app.services.briefing_generator import generate_today

    errors = []

    try:
        load_sources_from_yaml()
        fetch_all_sources()
    except Exception as exc:
        errors.append(f"Fetch: {exc}")

    try:
        analyze_new_articles()
    except Exception as exc:
        errors.append(f"Analyse: {exc}")

    try:
        generate_today()
    except Exception as exc:
        errors.append(f"Briefing: {exc}")

    if errors:
        return RedirectResponse(url="/?run_error=1", status_code=303)
    return RedirectResponse(url="/?updated=1", status_code=303)


# ── Reddit ─────────────────────────────────────────────────────────────────────

@app.get("/reddit", response_class=HTMLResponse)
def reddit_list(
    request: Request,
    subreddit: Optional[str] = None,
    sort: Optional[str] = None,       # hot | new
    date_filter: Optional[str] = None,
    q: Optional[str] = None,
):
    try:
        sb = get_supabase()

        today_str = date.today().isoformat()
        if date_filter == "all":
            selected_date = None
        elif date_filter:
            selected_date = date_filter
        else:
            selected_date = today_str

        query = (
            sb.table("reddit_posts")
            .select("*, reddit_post_analysis(relevance_score, priority, category, community_signal, summary_de)")
            .order("score", desc=True)
            .limit(300)
        )

        if selected_date:
            query = (
                query
                .gte("fetched_at", f"{selected_date}T00:00:00+00:00")
                .lt("fetched_at", f"{selected_date}T23:59:59+00:00")
            )

        if subreddit:
            query = query.eq("subreddit", subreddit)

        if sort:
            query = query.eq("sort_type", sort)

        if q:
            query = query.ilike("title", f"%{q}%")

        res = query.execute()
        posts = []
        for p in res.data:
            p["analysis"] = p.pop("reddit_post_analysis", None)
            posts.append(_to_ns(p))

        # Subreddit-Liste für Filter-Dropdown
        subs_res = sb.table("reddit_posts").select("subreddit").execute()
        subreddits = sorted({r["subreddit"] for r in subs_res.data if r.get("subreddit")})

        return templates.TemplateResponse(request, "reddit.html", context={
            "posts": posts,
            "subreddits": subreddits,
            "selected_subreddit": subreddit or "",
            "selected_sort": sort or "",
            "date_filter": date_filter or "",
            "selected_date": selected_date or "",
            "today": today_str,
            "q": q or "",
            "reddit_configured": settings.reddit_configured,
        })
    except Exception as exc:
        return _db_error_response(request, exc)


@app.post("/run-reddit", response_class=RedirectResponse)
def run_reddit():
    """Löst den Reddit-Fetch + Analyse manuell aus."""
    from app.services.reddit_fetcher import fetch_all_reddit
    from app.services.reddit_analyzer import analyze_new_reddit_posts

    errors = []

    try:
        fetch_all_reddit()
    except Exception as exc:
        errors.append(f"Reddit-Fetch: {exc}")

    try:
        analyze_new_reddit_posts()
    except Exception as exc:
        errors.append(f"Reddit-Analyse: {exc}")

    if errors:
        return RedirectResponse(url="/reddit?run_error=1", status_code=303)
    return RedirectResponse(url="/reddit?updated=1", status_code=303)

