-- KI-News Briefing – Datenbankschema für Supabase
-- Einmalig im Supabase SQL-Editor ausführen.

-- ── sources ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sources (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    url         text NOT NULL UNIQUE,
    type        text DEFAULT 'RSS',         -- RSS | Blog | arXiv | API | Webseite
    category    text,
    language    text DEFAULT 'en',
    priority    integer DEFAULT 3,          -- 1 (niedrig) – 5 (hoch)
    is_active   boolean DEFAULT true,
    created_at  timestamptz DEFAULT now()
);

-- ── articles ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS articles (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id    uuid REFERENCES sources(id),
    title        text NOT NULL,
    url          text NOT NULL,
    published_at timestamptz,
    fetched_at   timestamptz DEFAULT now(),
    summary_raw  text,
    content      text,
    language     text DEFAULT 'en',
    hash         text,                      -- SHA-256 für Duplikaterkennung
    is_duplicate boolean DEFAULT false,
    created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS articles_hash_idx      ON articles(hash);
CREATE INDEX IF NOT EXISTS articles_source_id_idx ON articles(source_id);
CREATE INDEX IF NOT EXISTS articles_fetched_at_idx ON articles(fetched_at DESC);

-- ── article_analysis ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS article_analysis (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id            uuid UNIQUE REFERENCES articles(id),
    relevance_score       integer,          -- 1–5
    practical_value_score integer,          -- 1–5
    hype_level            text,             -- niedrig | mittel | hoch
    priority              text,             -- niedrig | mittel | hoch
    category              text,
    summary_de            text,
    why_important         text,
    practical_relevance   text,
    kai_relevance         text,
    created_at            timestamptz DEFAULT now()
);

-- ── briefings ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS briefings (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    briefing_date    date UNIQUE NOT NULL,
    title            text,
    daily_summary    text,
    content_markdown text,
    created_at       timestamptz DEFAULT now()
);

-- ── briefing_items ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS briefing_items (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    briefing_id uuid REFERENCES briefings(id) ON DELETE CASCADE,
    article_id  uuid REFERENCES articles(id),
    rank        integer DEFAULT 0,
    section     text,       -- Top-Meldungen | Für Kai | Nur beobachten | Hype
    title       text,
    summary     text,
    importance  text,
    source_url  text
);

CREATE INDEX IF NOT EXISTS briefing_items_briefing_id_idx ON briefing_items(briefing_id);


-- ── reddit_posts ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reddit_posts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    reddit_post_id  text NOT NULL UNIQUE,   -- Reddit's eigene ID (z.B. "1abc2d")
    subreddit       text NOT NULL,
    title           text NOT NULL,
    url             text,                   -- externer Link (falls Link-Post)
    permalink       text,                   -- reddit.com/r/.../comments/...
    selftext        text,                   -- Post-Text (falls Self-Post)
    author          text,
    flair           text,
    score           integer DEFAULT 0,
    upvote_ratio    real DEFAULT 0,         -- 0.0 – 1.0
    num_comments    integer DEFAULT 0,
    sort_type       text DEFAULT 'hot',     -- hot | new
    language        text DEFAULT 'en',
    fetched_at      timestamptz DEFAULT now(),
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS reddit_posts_subreddit_idx  ON reddit_posts(subreddit);
CREATE INDEX IF NOT EXISTS reddit_posts_fetched_at_idx ON reddit_posts(fetched_at DESC);
CREATE INDEX IF NOT EXISTS reddit_posts_score_idx      ON reddit_posts(score DESC);


-- ── reddit_post_analysis ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reddit_post_analysis (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id               uuid UNIQUE REFERENCES reddit_posts(id),
    relevance_score       integer,          -- 1–5
    practical_value_score integer,          -- 1–5
    hype_level            text,             -- niedrig | mittel | hoch
    priority              text,             -- niedrig | mittel | hoch
    category              text,
    summary_de            text,
    why_important         text,
    practical_relevance   text,
    community_signal      text,             -- z.B. "breite Zustimmung", "kontrovers"
    kai_relevance         text,
    created_at            timestamptz DEFAULT now()
);

-- ── Migrations ────────────────────────────────────────────────────────────────
-- Fehlende Felder aus KI-Analyse-Antwort (was_passiert, fuer_wen_relevant, hype_oder_substanz)
ALTER TABLE article_analysis ADD COLUMN IF NOT EXISTS what_happened     text;
ALTER TABLE article_analysis ADD COLUMN IF NOT EXISTS for_whom          text;
ALTER TABLE article_analysis ADD COLUMN IF NOT EXISTS hype_or_substance text;


-- ── Row Level Security ────────────────────────────────────────────────────────
-- Das Backend verwendet den service_role-Key → bypassed RLS automatisch.
-- RLS wird aktiviert damit der anon-Key KEINEN Direktzugriff bekommt.
-- Für spätere Auth (Phase 6+): Policies für "authenticated" ergänzen.

ALTER TABLE sources        ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles       ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE briefings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE reddit_posts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE reddit_post_analysis  ENABLE ROW LEVEL SECURITY;
ALTER TABLE briefing_items ENABLE ROW LEVEL SECURITY;

-- Lesezugriff für eingeloggte Nutzer (für späteres Auth-Feature vorbereitet)
-- Solange kein Login existiert, sind diese Policies wirkungslos;
-- der service_role-Key des Backends greift immer durch.

CREATE POLICY "authenticated_read_sources"
    ON sources FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_articles"
    ON articles FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_article_analysis"
    ON article_analysis FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_briefings"
    ON briefings FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_briefing_items"
    ON briefing_items FOR SELECT TO authenticated USING (true);
