# AGENT.md

## Ziel
Baue eine kleine Webapp, die taeglich KI-News sammelt, analysiert und als kompaktes deutsches Tagesbriefing darstellt.
Fokus: Relevanz vor Volumen, klare Quellen, praxisnahe Einordnung fuer Kai.

## Produktkontext
- Nutzerin: Kai (KI, Copilot, Power Platform, Softwareentwicklung, Datenschutz, Marketing, Voice-over/Video, OpenAI)
- Kernfragen:
  - Was ist wirklich wichtig?
  - Was ist Hype?
  - Was ist praktisch relevant?
  - Welche Auswirkungen auf Business/Alltag?

## MVP-Umfang
- Dashboard mit aktuellem Tagesbriefing
- Briefing-Archiv mit Suche/Filter
- Quellenverwaltung (aktiv/inaktiv, Kategorie, Prioritaet)
- Artikelsammlung mit Duplikaterkennung
- KI-Auswertung mit Scores und Hype-Level
- Tagesbriefing-Generator (5-10 Top-Meldungen)
- Manueller Run per Button
- Automatischer Run per Cronjob (07:00)

## Nicht im MVP
- Mehrbenutzerverwaltung
- Newsletter
- Teams/Slack
- PDF-Export
- Mobile App
- Bezahlmodell

## Tech-Stack
- Backend: Python 3.14, FastAPI
- DB: Supabase (PostgreSQL) via supabase-py (service_role key)
- Frontend MVP: Jinja2 + Tailwind CSS (CDN)
- KI: OpenAI gpt-4o-mini
- Scheduler: Cron
- Hosting: lokal / VPS

**Wichtig:** Kein SQLAlchemy – direkter Supabase REST API Client.
Kein ORM, kein Alembic. Schema liegt in schema.sql.

## Datenmodell (Kern)
- `sources`
- `articles`
- `article_analysis`
- `briefings`
- `briefing_items`
- spaeter optional: `article_embeddings` (pgvector)

## API-Routen (MVP)
- GET /
- GET /briefings
- GET /briefings/{id}
- GET /sources
- POST /sources
- POST /sources/{id}/toggle
- GET /articles
- POST /run
- GET /health

## Analyse- und Briefingregeln
- Pro Artikel bewerten:
  - Relevanz (1-5)
  - Praxisnutzen (1-5)
  - Hype-Level (niedrig/mittel/hoch)
  - Prioritaet (niedrig/mittel/hoch)
- Antwortstruktur je Meldung:
  - Was ist passiert?
  - Warum wichtig?
  - Praktische Relevanz
  - Einschätzung
  - Quelle
- Tagesbriefing-Struktur:
  1. Kurzfazit
  2. Top-Meldungen
  3. Fuer Kai besonders relevant
  4. Nur beobachten
  5. Hype
  6. Quellen

## Umsetzungspfade
1. ✅ FastAPI Grundgeruest + Dashboard + Supabase + Quellen laden
2. ✅ RSS Abruf + Artikel speichern + Dedup + Altersfilter (2 Tage)
3. ✅ KI-Analyse (gpt-4o-mini) + Persistenz
4. ✅ Briefing-Generator + Dashboard-Anzeige + manueller Run
5. ⏳ Cronjob + Logging
6. ⏳ Suche/Filter + Deployment

## Aktuelle Implementierungsdetails

### Altersfilter
- `MAX_ARTICLE_AGE_DAYS = 2` in `source_fetcher.py`
- Beim ersten Lauf temporaer auf 10 setzen fuer guten Datenstart

### Duplikaterkennung
- SHA-256 Hash aus `title + url`
- Alle bekannten Hashes beim Start eines Fetch-Laufs einmalig laden
- Duplikate innerhalb eines Laufs und gegen DB-Bestand werden erkannt

### Briefing-Update-Logik
- Bereits bekannte Artikel werden nicht erneut gefetcht (Hash-Dedup)
- Bereits analysierte Artikel werden nicht erneut analysiert (article_id Check)
- Briefing wird nur neu generiert wenn seit der letzten Generierung neue Analysen vorliegen
- Wenn Regenerierung noetig: altes Briefing + briefing_items loeschen (CASCADE), neu generieren

### Starlette 1.0 Kompatibilitaet
- `TemplateResponse(request, "template.html", context={...})` – request als erstes Argument
- Altes Format `TemplateResponse("template.html", {"request": ...})` funktioniert nicht mehr

## Definition of Done
- [x] App laeuft mit uvicorn
- [x] Supabase angebunden
- [x] Quellen werden aus sources.yaml geladen (upsert)
- [x] Artikel werden gespeichert (992 beim Erstlauf)
- [x] KI bewertet Artikel (gpt-4o-mini)
- [x] Tagesbriefing wird erzeugt
- [x] Dashboard zeigt Briefing
- [x] Archiv funktioniert
- [x] Manueller Run funktioniert
- [ ] Cronjob funktioniert

## Betriebsregeln fuer den Agenten
- Schreibe alle Texte im Briefing auf Deutsch.
- Priorisiere vertrauenswuerdige Originalquellen.
- Vermeide Duplikate und Hype ohne Substanz.
- Jede Top-Meldung braucht einen Quellenlink.
- Fehler im Run sichtbar machen (Logs + UI Rueckmeldung).
- Secrets nur aus `.env`, nie im Code hardcoden.
- Kein SQLAlchemy verwenden – nur supabase-py Client.
- TemplateResponse immer mit neuem Starlette 1.0 API aufrufen.
