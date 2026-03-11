from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Letter(Base):
    __tablename__ = "letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    sender: Mapped[str | None] = mapped_column(Text)
    receiver: Mapped[str | None] = mapped_column(Text)
    creation_date: Mapped[date | None] = mapped_column(Date)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    keywords: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    raw_llm_response: Mapped[str | None] = mapped_column(Text)

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="letter", cascade="all, delete-orphan"
    )
    translations: Mapped[list["LetterTranslation"]] = relationship(
        back_populates="letter", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    letter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("letters.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    letter: Mapped["Letter"] = relationship(back_populates="tasks")


class LetterTranslation(Base):
    __tablename__ = "letter_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    letter_id: Mapped[int] = mapped_column(Integer, ForeignKey("letters.id"), nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str | None] = mapped_column(Text)
    translated_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    letter: Mapped["Letter"] = relationship(back_populates="translations")


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False, server_default="[]")
