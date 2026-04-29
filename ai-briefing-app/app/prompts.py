"""
Prompt-Templates für KI-Analyse und Briefing-Generierung.
Werden in ai_analyzer.py und briefing_generator.py verwendet.
"""

ARTICLE_ANALYSIS_PROMPT = """\
Du bist ein KI-News-Analyst. Analysiere den folgenden Artikel für diese Zielgruppe:
- KI im Unternehmen
- Microsoft Copilot und Power Platform
- Softwareentwicklung
- Pflege und Management
- Datenschutz und Regulierung
- Marketing und Video/Voice-over

Artikel:
Titel: {title}
Quelle: {source}
Veröffentlicht: {published_at}
Zusammenfassung: {summary}
Volltext:
{content}

Antworte ausschließlich als JSON (kein Markdown, kein Fließtext):
{{
    "was_passiert": "string – 1-2 Sätze, was konkret passiert ist",
    "warum_wichtig": "string – warum das relevant ist",
    "praktische_relevanz": "string – konkreter Nutzen oder Handlungsbedarf",
    "fuer_wen_relevant": "string – Zielgruppe(n) aus der Liste oben",
    "hype_oder_substanz": "string – kurze Einschätzung",
    "relevanz_score": <1-5>,
    "praxisnutzen_score": <1-5>,
    "hype_level": "<niedrig|mittel|hoch>",
    "prioritaet": "<niedrig|mittel|hoch>",
    "kategorie": "string – eine Kategorie aus: KI-Modelle & Agenten | Microsoft Copilot | Power Platform | Softwareentwicklung | Datenschutz & Regulierung | Pflege & Gesundheit | Marketing & Content Creation | Forschung & Wissenschaft | Tools & Produktivität",
    "zusammenfassung_de": "string – 2-3 Sätze auf Deutsch",
    "kai_relevanz": "string – persönliche Relevanz für Kai, 1-2 Sätze"
}}

Skalen:
- relevanz_score: 1 (kaum relevant) bis 5 (sehr wichtig)
- praxisnutzen_score: 1 (theoretisch) bis 5 (sofort nutzbar)
- hype_level: niedrig | mittel | hoch
- prioritaet: hoch wenn relevanz_score ≥ 4 UND praxisnutzen_score ≥ 3; niedrig wenn beide ≤ 2; sonst mittel
"""

BRIEFING_GENERATION_PROMPT = """\
Du bist ein KI-News-Redakteur. Erstelle ein kompaktes deutsches KI-Tagesbriefing für Kai.

Kai ist interessiert an: KI im Unternehmen, Microsoft Copilot, Power Platform, Softwareentwicklung,
Datenschutz, Pflege/Management, Marketing, Voice-over/Video.

Heutige Artikel (JSON-Array):
{articles_json}

Erstelle das Briefing ausschließlich als JSON (kein Markdown drum herum):
{{
    "titel": "KI Briefing – {date}",
    "kurzfazit": "string – 2-3 Sätze: was war heute das Wichtigste",
    "top_meldungen": [
        {{
            "rang": 1,
            "artikel_id": "uuid",
            "einschaetzung": "string – warum dieser Artikel heute besonders wichtig ist (1-2 Sätze)",
            "quelle": "string (URL)"
        }}
    ],
    "fuer_kai": ["artikel_id1", "artikel_id2"],
    "nur_beobachten": ["artikel_id1"],
    "hype": ["artikel_id1"]
}}

Regeln:
- Wähle 5–10 Top-Meldungen, sortiert nach Relevanz
- Für jede Top-Meldung nur rang, artikel_id, einschaetzung und quelle angeben – Titel und Beschreibungen stammen aus der Voranalyse
- fuer_kai: Artikel mit besonderer persönlicher Relevanz für Kai
- nur_beobachten: interessant, aber kein sofortiger Handlungsbedarf
- hype: wenig Substanz, viel Lärm
- Alle Texte auf Deutsch
- Jede Top-Meldung braucht eine Quellen-URL
"""

REDDIT_ANALYSIS_PROMPT = """\
Du bist ein KI-Community-Analyst. Analysiere den folgenden Reddit-Post für diese Zielgruppe:
- KI im Unternehmen
- Microsoft Copilot und Power Platform
- Softwareentwicklung
- Pflege und Management
- Datenschutz und Regulierung
- Marketing und Video/Voice-over

Reddit-Post:
Subreddit: r/{subreddit}
Titel: {title}
Autor: {author}
Score: {score} (Upvote-Ratio: {upvote_ratio:.0%}, {num_comments} Kommentare)
Kategorie/Flair: {flair}
Post-Text:
{selftext}

Antworte ausschließlich als JSON (kein Markdown, kein Fließtext):
{{
    "was_diskutiert_die_community": "string – 1-2 Sätze: worum geht es in diesem Post",
    "warum_wichtig": "string – warum ist das für die Zielgruppe relevant",
    "praktische_relevanz": "string – konkreter Nutzen oder Handlungsbedarf",
    "fuer_wen_relevant": "string – Zielgruppe(n) aus der Liste oben",
    "community_signal": "string – Einschätzung der Community-Reaktion, z.B. breite Zustimmung | kontrovers | Nischen-Interesse | viel Diskussion | Skepsis",
    "hype_oder_substanz": "string – kurze Einschätzung ob echte Erfahrungen oder Hype",
    "relevanz_score": <1-5>,
    "praxisnutzen_score": <1-5>,
    "hype_level": "<niedrig|mittel|hoch>",
    "prioritaet": "<niedrig|mittel|hoch>",
    "kategorie": "string – eine Kategorie aus: KI-Modelle & Agenten | Microsoft Copilot | Power Platform | Softwareentwicklung | Datenschutz & Regulierung | Pflege & Gesundheit | Marketing & Content Creation | Forschung & Wissenschaft | Tools & Produktivität",
    "zusammenfassung_de": "string – 2-3 Sätze auf Deutsch, Community-Perspektive betonen",
    "kai_relevanz": "string – persönliche Relevanz für Kai, 1-2 Sätze"
}}

Skalen:
- relevanz_score: 1 (kaum relevant) bis 5 (sehr wichtig)
- praxisnutzen_score: 1 (theoretisch) bis 5 (sofort nutzbar)
- hype_level: niedrig | mittel | hoch
- prioritaet: hoch wenn relevanz_score ≥ 4 UND praxisnutzen_score ≥ 3; niedrig wenn beide ≤ 2; sonst mittel

Wichtig: Berücksichtige Score ({score}) und Kommentaranzahl ({num_comments}) als Signal
für Community-Interesse. Ein hoher Score = breite Zustimmung. Viele Kommentare = aktive Diskussion.
"""
