from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    index_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)  # processing | ready | failed
    created_at: Mapped[str] = mapped_column(String)  # ISO-8601 string
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
