from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from models import Letter, Task

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "letters.db"


def _get_engine(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


_engine = _get_engine()
SessionLocal = sessionmaker(bind=_engine)


def get_session() -> Session:
    return SessionLocal()


def init_db():
    """Run Alembic migrations to bring the database up to date."""
    alembic_cfg = Config(str(Path(__file__).parent / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
    command.upgrade(alembic_cfg, "head")


# --- CRUD operations ---


def insert_letter(
    session: Session,
    title: str | None = None,
    summary: str | None = None,
    sender: str | None = None,
    receiver: str | None = None,
    creation_date: date | None = None,
    keywords: str | None = None,
    full_text: str | None = None,
    pdf_path: str | None = None,
    page_count: int | None = None,
    raw_llm_response: str | None = None,
) -> Letter:
    letter = Letter(
        title=title,
        summary=summary,
        sender=sender,
        receiver=receiver,
        creation_date=creation_date,
        keywords=keywords,
        full_text=full_text,
        pdf_path=pdf_path,
        page_count=page_count,
        raw_llm_response=raw_llm_response,
    )
    session.add(letter)
    session.flush()
    return letter


def insert_task(
    session: Session,
    letter_id: int,
    description: str,
    deadline: date | None = None,
) -> Task:
    task = Task(letter_id=letter_id, description=description, deadline=deadline)
    session.add(task)
    session.flush()
    return task


def search_letters(session: Session, query: str) -> list[Letter]:
    """Full-text search using FTS5."""
    result = session.execute(
        text(
            "SELECT rowid FROM letters_fts WHERE letters_fts MATCH :query ORDER BY rank"
        ),
        {"query": query},
    )
    ids = [row[0] for row in result]
    if not ids:
        return []
    return session.query(Letter).filter(Letter.id.in_(ids)).all()


def get_all_letters(session: Session, order_by: str = "creation_date") -> list[Letter]:
    col = getattr(Letter, order_by, Letter.creation_date)
    return session.query(Letter).order_by(col.desc()).all()


def get_letter(session: Session, letter_id: int) -> Letter | None:
    return session.get(Letter, letter_id)


def get_pending_tasks(session: Session) -> list[Task]:
    return (
        session.query(Task)
        .filter(Task.is_done == False)  # noqa: E712
        .order_by(Task.deadline.asc().nullslast())
        .all()
    )


def update_task(
    session: Session,
    task_id: int,
    is_done: bool | None = None,
    description: str | None = None,
    deadline: date | None = None,
) -> Task | None:
    task = session.get(Task, task_id)
    if task is None:
        return None
    if is_done is not None:
        task.is_done = is_done
    if description is not None:
        task.description = description
    if deadline is not None:
        task.deadline = deadline
    session.flush()
    return task


def delete_task(session: Session, task_id: int) -> bool:
    task = session.get(Task, task_id)
    if task is None:
        return False
    session.delete(task)
    session.flush()
    return True
