# KI-News Briefing

Tägliches KI-Tagesbriefing – sammelt, analysiert und präsentiert KI-News kompakt auf Deutsch.

## Schnellstart

### 1. Abhängigkeiten installieren

```bash
cd ai-briefing-app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
# .env öffnen und ausfüllen:
#   SUPABASE_URL          → Projekt-URL aus Supabase-Dashboard
#   SUPABASE_SECRET_KEY   → service_role-Key (bypasses RLS)
#   OPENAI_API_KEY        → OpenAI API Key
#   REDDIT_CLIENT_ID      → Reddit App Client-ID (reddit.com/prefs/apps)
#   REDDIT_CLIENT_SECRET  → Reddit App Client-Secret
#   REDDIT_USER_AGENT     → z.B. KI-News-Bot/1.0 (optional, hat Default)
```

> **Reddit App anlegen:** https://www.reddit.com/prefs/apps → "create another app" → Typ: **script**, redirect uri: `http://localhost:8080`

### 3. Supabase-Datenbank vorbereiten

Schema **einmalig** im Supabase SQL-Editor ausführen:

```bash
# Inhalt von schema.sql kopieren und im Supabase SQL-Editor ausführen
```

Tabellen: `sources`, `articles`, `article_analysis`, `briefings`, `briefing_items`, `reddit_posts`, `reddit_post_analysis`

### 4. App starten

```bash
cd ai-briefing-app
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Öffne [http://localhost:8000](http://localhost:8000)

### 5. Ersten Lauf ausführen

```bash
# Feeds testen (kein DB-Zugriff)
.venv/bin/python scripts/test_feeds.py

# Vollständiger Lauf: Quellen → Artikel → KI-Analyse → Briefing
.venv/bin/python scripts/run_daily_briefing.py
```

---

## Projektstruktur

```
ai-briefing-app/
├── app/
│   ├── main.py                 ← FastAPI-App + alle Routen
│   ├── config.py               ← Einstellungen aus .env
│   ├── prompts.py              ← KI-Prompt-Templates
│   ├── db/
│   │   ├── models.py             ← Pydantic-Modelle (Eingabevalidierung)
│   │   └── supabase_client.py    ← Supabase Python Client (Singleton)
│   ├── services/
│   │   ├── source_loader.py      ← sources.yaml → DB (upsert)
│   │   ├── source_fetcher.py     ← RSS-Abruf + Duplikaterkennung
│   │   ├── ai_analyzer.py        ← OpenAI-Analyse je Artikel
│   │   ├── briefing_generator.py ← Tagesbriefing generieren
│   │   ├── reddit_fetcher.py     ← PRAW: hot + new Posts je Subreddit
│   │   └── reddit_analyzer.py   ← OpenAI-Analyse Reddit-Posts (Community-Fokus)
│   ├── templates/              ← Jinja2-Templates
│   └── static/                 ← CSS
├── scripts/
│   ├── run_daily_briefing.py   ← Cronjob-Script (Phase 2–6, inkl. Reddit)
│   └── test_feeds.py           ← Feed-Test ohne DB
├── schema.sql                  ← Supabase-Schema (einmalig ausführen)
├── sources.yaml                ← RSS-Quellen + Reddit-Subreddits
├── requirements.txt
└── .env.example
```

---

## Entwicklungsphasen

| Phase | Inhalt | Status |
|-------|--------|--------|
| 1 | FastAPI-Grundgerüst, Supabase, Dashboard, Quellen laden | ✅ |
| 2 | RSS-Abruf, Artikel speichern, Duplikaterkennung, Altersfilter | ✅ |
| 3 | OpenAI-Analyse (gpt-4o-mini), Scores speichern | ✅ |
| 4 | Briefing-Generator, Dashboard, manueller Run | ✅ |
| 5 | Reddit-Pipeline: Fetch (PRAW), eigene DB-Tabellen, KI-Analyse, eigener Tab | ✅ |
| 6 | Reddit im Briefing (eigener Abschnitt) | ⏳ |
| 7 | Cronjob, Logging | ⏳ |
| 8 | Suche, Filter, Deployment | ⏳ |

---

## API-Routen

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/` | Dashboard (aktuelles Briefing) |
| GET | `/briefings` | Archiv aller Briefings |
| GET | `/briefings/{id}` | Einzelnes Briefing |
| GET | `/sources` | Quellenliste + Formular |
| POST | `/sources` | Neue Quelle anlegen |
| POST | `/sources/{id}/toggle` | Quelle aktivieren/deaktivieren |
| GET | `/articles` | Artikelübersicht (Datumsfilter) |
| GET | `/reddit` | Reddit-Posts (Filter: Subreddit, Sort, Datum) |
| POST | `/run` | Manueller Briefing-Lauf (Phase 2–4) |
| POST | `/run-reddit` | Manueller Reddit-Fetch + Analyse |
| GET | `/health` | App-Status + DB-Check |

---

## Wichtige Konfiguration

| Parameter | Datei | Beschreibung |
|-----------|-------|--------------|
| `MAX_ARTICLE_AGE_DAYS` | `source_fetcher.py` | Altersfilter beim Fetch (Standard: 2) |
| `MAX_ARTICLES_PER_RUN` | `ai_analyzer.py` | Max. Artikel pro Analyse-Lauf (Standard: 50) |
| `MAX_POST_AGE_DAYS` | `reddit_fetcher.py` | Altersfilter Reddit-Posts (Standard: 2) |
| `MAX_POSTS_PER_RUN` | `reddit_analyzer.py` | Max. Posts pro Analyse-Lauf (Standard: 60) |

---

## Reddit-Konfiguration

Subreddits werden in `sources.yaml` unter dem Schlüssel `reddit:` konfiguriert:

```yaml
reddit:
  - name: "r/artificial"
    subreddit: "artificial"
    category: "KI-Modelle"
    language: "en"
    priority: 5
    post_limit: 10      # Anzahl Posts pro Sort-Typ
    sort: [hot, new]    # beide Sortierungen täglich holen
```

Die Reddit-Pipeline läuft **getrennt** von der News-Pipeline:
- Eigene DB-Tabellen (`reddit_posts`, `reddit_post_analysis`)
- Eigener KI-Prompt (Community-Perspektive, Score/Kommentare als Signal)
- Eigener Dashboard-Tab `/reddit`
- Eigener Refresh-Button
| `MAX_INPUT_ARTICLES` | `briefing_generator.py` | Max. Artikel ans Briefing-Modell (Standard: 40) |
| `MODEL` | `ai_analyzer.py` | OpenAI-Modell (Standard: gpt-4o-mini) |

---

## Cronjob (Phase 5)

```cron
0 7 * * * /pfad/zum/venv/bin/python /pfad/zum/ai-briefing-app/scripts/run_daily_briefing.py >> /var/log/ki-briefing.log 2>&1
```

## Feed-Test

```bash
# Alle Feeds testen
.venv/bin/python scripts/test_feeds.py

# Nur funktionierende anzeigen
.venv/bin/python scripts/test_feeds.py --only-ok

# Mit Artikel-Vorschau
.venv/bin/python scripts/test_feeds.py --verbose
```

---

## Sicherheit

- Secrets ausschließlich in `.env` (nie im Code)
- `.env` ist in `.gitignore` eingetragen
- `/run` sollte in Produktion durch Authentifizierung geschützt werden
