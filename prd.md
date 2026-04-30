PDR – KI Daily Briefing Webapp (Supabase Edition)

1. Projektziel

Ziel ist der Bau einer kleinen Webapp, die täglich aktuelle KI-News, Blogposts, Studien und Produktupdates sammelt, analysiert, bewertet und als kompaktes deutschsprachiges Briefing darstellt.

Die Webapp soll ohne n8n oder externe Automatisierungsplattform funktionieren. Die Automatisierung erfolgt über einen serverseitigen Cronjob.

2. Zielgruppe

Primäre Nutzerin:

* Kai
* interessiert an KI, Automatisierung, Microsoft Copilot, Power Platform, Softwareentwicklung, Datenschutz, Pflege/Management, Marketing und Voice-over/Video

Sekundäre Nutzer:

* eventuell Kolleg:innen oder andere interessierte Personen im Unternehmen

⸻

3. Kernnutzen

Die Webapp soll täglich beantworten:

* Was ist in der KI-Welt wirklich wichtig?
* Welche Entwicklungen sind nur Hype?
* Welche News sind praktisch relevant?
* Welche Auswirkungen haben sie für Softwareunternehmen, Pflege/Management, Marketing oder persönliche Produktivität?
* Wo finde ich die Originalquellen?

⸻

4. MVP-Funktionsumfang

4.1 Dashboard

Die Startseite zeigt das aktuelle Tagesbriefing.

Inhalte:

* Datum des Briefings
* kurze Zusammenfassung des Tages
* Top-News des Tages
* Kategorien
* Relevanzbewertung
* Quellenlinks
* Zeitpunkt der letzten Aktualisierung

Beispiel:

KI Briefing – 29.04.2026
Kurzfazit:
Heute gab es mehrere relevante Entwicklungen im Bereich KI-Agenten, Microsoft Copilot und Regulierung.
Top 5:
1. OpenAI veröffentlicht ...
2. Microsoft erweitert ...
3. Neue Studie zu ...

⸻

4.2 Briefing-Archiv

Funktionen:

* Liste vergangener Briefings
* Detailansicht pro Tag
* Suche nach Stichworten
* Filter nach Kategorie

⸻

4.3 Quellenverwaltung

Felder pro Quelle:

* Name
* URL
* Typ (RSS, Webseite, Blog, arXiv, API)
* Kategorie
* Aktiv/Inaktiv
* Sprache
* Priorität

Beispielquellen:

* OpenAI Blog
* Anthropic News
* Google DeepMind Blog
* Microsoft AI Blog
* Microsoft Power Platform Blog
* Heise KI
* The Decoder
* arXiv cs.AI
* arXiv cs.CL
* Hacker News
* TechCrunch AI
* MIT Technology Review AI
* European Commission AI Act

⎺

4.3b Reddit-Quellen

Reddit-Posts werden als **eigene Pipeline** separat von News-Artikeln behandelt.
Sie haben eigene DB-Tabellen, einen eigenen KI-Prompt und einen eigenen Dashboard-Tab.

Konfiguriert in `sources.yaml` unter dem Schlüssel `reddit:`:

Aktive Subreddits:

* r/artificial (allgemeine KI-News)
* r/MachineLearning (Forschung)
* r/LocalLLaMA (lokale Modelle, Tools)
* r/ChatGPT (OpenAI-Praxis)
* r/MicrosoftCopilot
* r/PowerAutomate

Pro Subreddit: Top-10 Posts, Sort: hot + new täglich

⸻

4.3c arXiv / Research-Pipeline

arXiv-Artikel werden als **eigene Pipeline** behandelt und **nicht** in die Mainstream-Analyse und das Tagesbriefing eingemischt.

Begründung: arXiv liefert täglich 200–300+ Papers (Grundlagenforschung), die thematisch und inhaltlich eine andere Zielgruppe ansprechen als tagesaktuelle KI-News. Eine Vermischung würde das Briefing verwässern.

Umsetzung:
* `type: "arXiv"` in `sources.yaml` flaggt eine Quelle als Research-Quelle
* `ai_analyzer.py` schließt arXiv-Quellen aus (keine OpenAI-Kosten)
* `briefing_generator.py` schließt arXiv-Quellen aus
* Eigene Seite `/research` mit collapsible Cards und vollem Abstract (kein extra KI nötig – Abstract ist bereits im RSS enthalten)
* Keyword-Highlighting: Papers mit Begriffen wie `agent`, `LLM`, `RAG`, `multimodal`, `reasoning` etc. werden als ⭐ Highlight markiert
* Dashboard-Widget: Top 5 Highlight-Papers des Tages direkt sichtbar

⸻

4.4 Artikel-Sammlung

Speichern:

* Titel
* URL
* Quelle
* Veröffentlichungsdatum
* Kurzbeschreibung
* Volltext (wenn extrahierbar)
* Sprache
* Kategorie
* Abrufdatum
* Hash/URL zur Duplikaterkennung

⸻

4.5 KI-Auswertung

Bewertung nach:

* Relevanz
* Neuigkeitswert
* praktischem Nutzen
* Vertrauenswürdigkeit
* Relevanz für Kai
* Hype-Faktor

Skala:

Relevanz: 1–5
Praxisnutzen: 1–5
Hype-Faktor: niedrig / mittel / hoch
Priorität: niedrig / mittel / hoch

⸻

4.6 Tagesbriefing generieren

Bestandteile:

* Tagesfazit
* 5–10 wichtigste Meldungen
* Pro Meldung:
    * Titel
    * Was ist passiert?
    * Warum wichtig?
    * praktische Relevanz
    * Einschätzung
    * Quelle

Zusätzliche Sektionen:

* Für dich besonders relevant
* Nur beobachten
* Hype / wenig Substanz

⸻

4.7 Manueller Start

Buttons:

* **Briefing jetzt aktualisieren** → News-Pipeline (Phase 2–4)
* **Reddit aktualisieren** → Reddit-Pipeline (Fetch + Analyse)

⸻

4.8 Automatisierung

Cronjob:

0 7 * * * python run_daily_briefing.py

Phasen pro Lauf:
1. Quellen aus sources.yaml in DB synchronisieren
2. RSS-Feeds abrufen, Artikel speichern
3. Mainstream-Artikel via OpenAI analysieren (arXiv ausgeschlossen)
4. Tagesbriefing generieren (arXiv ausgeschlossen)
5. Reddit-Posts abrufen (PRAW, read-only)
6. Reddit-Posts via OpenAI analysieren

⸻

5. Nicht Teil des MVP

Noch nicht:

* Mehrbenutzerverwaltung
* Newsletter
* Teams-/Slack-Integration
* PDF-Export
* Mobile App
* Bezahlmodell

⸻

6. Technischer Stack

Backend

Python
FastAPI
SQLAlchemy

Datenbank

Supabase (PostgreSQL)

Verwendung für:

* Relationale Datenhaltung
* REST + SQL Zugriff
* spätere Row Level Security
* Auth optional später nutzbar
* pgvector später für semantische Suche/RAG möglich

Warum Supabase statt SQLite:

* produktionsreifer
* sofort Cloud-ready
* keine spätere Migration nötig
* PostgreSQL Features
* später embeddings möglich

⸻

Frontend

MVP:

Jinja2 Templates
HTML/CSS
Optional Tailwind

Später:

React / Next.js

⸻

Scheduler

Cron
oder systemd timer

⸻

Hosting

Hetzner VPS
oder Docker Deployment

⸻

7. Projektstruktur

ai-briefing-app/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── prompts.py
│   │
│   ├── db/
│   │   ├── supabase_client.py
│   │   └── models.py
│   │
│   ├── services/
│   │   ├── source_loader.py
│   │   ├── source_fetcher.py
│   │   ├── ai_analyzer.py        ← Mainstream-Analyse (exkl. arXiv)
│   │   ├── briefing_generator.py ← Tagesbriefing (exkl. arXiv)
│   │   ├── reddit_fetcher.py     ← NEU: PRAW-basierter Reddit-Fetcher
│   │   └── reddit_analyzer.py   ← NEU: KI-Analyse Reddit-Posts
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html        ← inkl. Research-Widget
│   │   ├── reddit.html           ← eigener Reddit-Tab
│   │   ├── research.html         ← NEU: arXiv Research-Seite
│   │   └── ...
│   └── static/
│
├── scripts/
│   └── run_daily_briefing.py
│
├── sources.yaml            ← RSS-Quellen + Reddit-Subreddits
├── requirements.txt
├── .env
└── PRD.md

⸻

8. Datenmodell (Supabase)

Table: sources

id uuid primary key,
name text,
url text,
type text,
category text,
language text,
priority int,
is_active boolean,
created_at timestamp

⸻

Table: articles

id uuid primary key,
source_id uuid,
title text,
url text,
published_at timestamp,
fetched_at timestamp,
summary_raw text,
content text,
language text,
hash text,
is_duplicate boolean,
created_at timestamp

⸻

Table: article_analysis

id uuid primary key,
article_id uuid,
relevance_score int,
practical_value_score int,
hype_level text,
priority text,
category text,
summary_de text,
why_important text,
practical_relevance text,
kai_relevance text,
created_at timestamp

⎺

Table: reddit_posts  (NEU)

id uuid primary key,
reddit_post_id text unique,    -- Reddit's eigene ID
subreddit text,
title text,
url text,                      -- externer Link (falls Link-Post)
permalink text,                -- reddit.com/r/.../comments/...
selftext text,                 -- Post-Text (Self-Posts)
author text,
flair text,
score int,
upvote_ratio real,             -- 0.0 – 1.0
num_comments int,
sort_type text,                -- hot | new
language text,
fetched_at timestamp,
created_at timestamp

⎺

Table: reddit_post_analysis  (NEU)

id uuid primary key,
post_id uuid,
relevance_score int,
practical_value_score int,
hype_level text,
priority text,
category text,
summary_de text,
why_important text,
practical_relevance text,
community_signal text,         -- z.B. "breite Zustimmung", "kontrovers"
kai_relevance text,
created_at timestamp

⸻

Table: briefings

id uuid primary key,
briefing_date date,
title text,
daily_summary text,
content_markdown text,
created_at timestamp

⸻

Table: briefing_items

id uuid primary key,
briefing_id uuid,
article_id uuid,
rank int,
section text,
title text,
summary text,
importance text,
source_url text

⸻

Optional später: Embeddings mit pgvector

Tabelle:

article_embeddings
- article_id
- embedding vector(1536)

Use Cases:

* semantische Suche
* ähnliche News clustern
* eigenes RAG aufbauen

⸻

9. Kategorien

KI-Modelle
KI-Agenten
Microsoft Copilot
Power Platform
Softwareentwicklung
Datenschutz & Regulierung
Pflege & Gesundheit
Marketing & Content
Voice-over & Video
Forschung
Tools & Produktivität
Hype / Beobachten

⸻

10. Prompts

Artikelanalyse Prompt

Du bist ein KI-News-Analyst.
Analysiere den Artikel für:
- KI im Unternehmen
- Copilot
- Power Platform
- Softwareentwicklung
- Pflege und Management
- Datenschutz
- Marketing und Video
Bewerte:
1 Was ist passiert?
2 Warum wichtig?
3 Praktische Relevanz?
4 Für wen relevant?
5 Hype oder substanziell?
6 Relevanz 1–5
7 Praxisnutzen 1–5
JSON ausgeben.

⸻

Tagesbriefing Prompt

Erstelle ein kompaktes deutsches KI-Tagesbriefing.
Struktur:
1 Kurzfazit
2 Top-Meldungen
3 Für Kai besonders relevant
4 Nur beobachten
5 Hype
6 Quellen

⸻

11. User Stories

User Story 1

Als Nutzerin möchte ich das aktuelle Briefing auf der Startseite sehen.

Akzeptanz:

* aktuelles Briefing sichtbar
* Datum sichtbar
* Quellen pro Meldung vorhanden

⸻

User Story 2

Als Nutzerin möchte ich alte Briefings durchsuchen.

Akzeptanz:

* Archiv vorhanden
* nach Datum sortiert
* einzelne Detailansicht

⸻

User Story 3

Als Nutzerin möchte ich Quellen aktivieren/deaktivieren.

Akzeptanz:

* Quellenliste
* Toggle aktiv/inaktiv
* neue Quellen ergänzbar

⸻

User Story 4

Als Nutzerin möchte ich Briefing manuell neu erzeugen.

Akzeptanz:

* Button vorhanden
* Prozess läuft
* Fehler werden angezeigt

⸻

12. API Routen

GET  /
GET  /briefings
GET  /briefings/{id}
GET  /sources
POST /sources
POST /sources/{id}/toggle
GET  /articles
POST /run
GET  /health

⸻

13. UI Anforderungen

Design:

* schlicht
* übersichtlich
* responsive
* Kartenlayout

Karte:

[KI-Agenten] [Relevanz 5/5]
Titel
Was ist passiert
Warum wichtig
Relevanz für dich
Quelle

⸻

14. Sicherheit

* OpenAI Keys in .env
* Supabase Keys in .env
* .gitignore
* Input Validation
* /run später absichern

⸻

15. Environment Variablen

OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
APP_ENV=development
APP_SECRET_KEY=

⸻

16. requirements.txt

fastapi
uvicorn
jinja2
sqlalchemy
supabase
python-dotenv
feedparser
requests
beautifulsoup4
readability-lxml
openai
pydantic
python-multipart
pyyaml
psycopg2-binary

⸻

17. Entwicklungsphasen

Phase 1

* FastAPI Grundgerüst
* Supabase anbinden
* Dashboard bauen
* sources.yaml laden

⸻

Phase 2

* RSS Abruf
* Artikel speichern
* Duplikaterkennung
* Artikelübersicht

⸻

Phase 3

* OpenAI Analyse
* Bewertung speichern

⸻

Phase 4

* Tagesbriefing erzeugen
* Dashboard Anzeige

⸻

Phase 5

* Cronjob
* Logging

⸻

Phase 6

* Suche
* Filter
* Quellenverwaltung UI
* Deployment

⸻

18. Definition of Done

Fertig wenn:

* App via uvicorn läuft
* Supabase angebunden
* Quellen werden ausgelesen
* Artikel gespeichert
* KI bewertet Artikel
* Tagesbriefing wird erzeugt
* Archiv funktioniert
* Button “Jetzt aktualisieren” läuft
* Cronjob funktioniert

⸻

19. Beispiel sources.yaml

sources:
- name: OpenAI Blog
  url: https://openai.com/news/rss.xml
  type: rss
  category: KI-Modelle
  priority: 5
  active: true
- name: Anthropic News
  url: https://www.anthropic.com/news/rss.xml
  type: rss
  category: KI-Modelle
  priority: 5
  active: true
- name: Google DeepMind Blog
  url: https://deepmind.google/discover/blog/rss.xml
  type: rss
  category: Forschung
  priority: 4
  active: true
- name: Microsoft AI Blog
  url: https://blogs.microsoft.com/ai/feed/
  type: rss
  category: Microsoft Copilot
  priority: 5
  active: true
- name: Heise KI
  url: https://www.heise.de/thema/Kuenstliche-Intelligenz?view=atom
  type: rss
  category: KI-News
  priority: 4
  active: true

⸻

20. Erstes Entwicklungsziel

Zuerst nur:

1 FastAPI App mit Dashboard
2 Supabase anbinden
3 RSS Feeds abrufen und anzeigen

Danach:

4 KI Analyse
5 Briefing Generator
6 Cronjob

⸻