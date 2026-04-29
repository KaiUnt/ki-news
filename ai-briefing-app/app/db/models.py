"""
Pydantic-Modelle für Eingabevalidierung (z. B. POST-Requests).

Die tatsächliche DB-Struktur ist in schema.sql definiert –
bitte einmalig im Supabase SQL-Editor ausführen.
"""

from pydantic import BaseModel
from typing import Optional


class SourceCreate(BaseModel):
    name: str
    url: str
    type: str = "RSS"
    category: str = ""
    language: str = "en"
    priority: int = 3


# ── Platzhalter damit bestehende Imports nicht brechen ──────────────────────
Source = None
Article = None
ArticleAnalysis = None
Briefing = None
BriefingItem = None


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    type = Column(String, default="RSS")       # RSS | Webseite | Blog | arXiv | API
    category = Column(String)
    language = Column(String, default="en")
    priority = Column(Integer, default=3)      # 1 (niedrig) – 5 (hoch)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    articles = relationship("Article", back_populates="source")

    def __repr__(self) -> str:
        return f"<Source {self.name}>"


class Article(Base):
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"))
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    summary_raw = Column(Text)
    content = Column(Text)
    language = Column(String, default="en")
    hash = Column(String)                      # SHA-256 für Duplikaterkennung
    is_duplicate = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="articles")
    analysis = relationship("ArticleAnalysis", back_populates="article", uselist=False)

    def __repr__(self) -> str:
        return f"<Article {self.title[:60]}>"


class ArticleAnalysis(Base):
    __tablename__ = "article_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), unique=True)
    relevance_score = Column(Integer)          # 1–5
    practical_value_score = Column(Integer)    # 1–5
    hype_level = Column(String)                # niedrig | mittel | hoch
    priority = Column(String)                  # niedrig | mittel | hoch
    category = Column(String)
    summary_de = Column(Text)
    why_important = Column(Text)
    practical_relevance = Column(Text)
    kai_relevance = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    article = relationship("Article", back_populates="analysis")


class Briefing(Base):
    __tablename__ = "briefings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    briefing_date = Column(Date, unique=True, nullable=False)
    title = Column(Text)
    daily_summary = Column(Text)
    content_markdown = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship(
        "BriefingItem",
        back_populates="briefing",
        order_by="BriefingItem.rank",
    )

    def __repr__(self) -> str:
        return f"<Briefing {self.briefing_date}>"


class BriefingItem(Base):
    __tablename__ = "briefing_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    briefing_id = Column(UUID(as_uuid=True), ForeignKey("briefings.id"))
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=True)
    rank = Column(Integer, default=0)
    section = Column(String)   # Top-Meldungen | Für Kai | Nur beobachten | Hype
    title = Column(Text)
    summary = Column(Text)
    importance = Column(Text)
    source_url = Column(Text)

    briefing = relationship("Briefing", back_populates="items")
