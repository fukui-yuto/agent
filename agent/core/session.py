"""
SQLite-backed session persistence.
Saves and loads conversation history across runs.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Session

from agent.config import DB_PATH
from agent.utils.logger import log_info, log_warning


class Base(DeclarativeBase):
    pass


class ConversationRecord(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True, nullable=False)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SessionManager:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        Base.metadata.create_all(self.engine)

    def save(self, session_id: str, messages: list[dict]) -> None:
        """Persist a list of messages for a session."""
        with Session(self.engine) as session:
            # Clear existing records for this session
            session.query(ConversationRecord).filter_by(session_id=session_id).delete()
            for msg in messages:
                content = msg.get("content") or json.dumps(msg)
                session.add(ConversationRecord(
                    session_id=session_id,
                    role=msg.get("role", "unknown"),
                    content=content,
                ))
            session.commit()

    def load(self, session_id: str) -> list[dict]:
        """Load messages for a session."""
        with Session(self.engine) as session:
            records = (
                session.query(ConversationRecord)
                .filter_by(session_id=session_id)
                .order_by(ConversationRecord.id)
                .all()
            )
            return [{"role": r.role, "content": r.content} for r in records]

    def list_sessions(self) -> list[str]:
        """Return all known session IDs."""
        with Session(self.engine) as session:
            rows = session.query(ConversationRecord.session_id).distinct().all()
            return [r[0] for r in rows]

    def delete(self, session_id: str) -> None:
        with Session(self.engine) as session:
            session.query(ConversationRecord).filter_by(session_id=session_id).delete()
            session.commit()
