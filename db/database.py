from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from db.models import Base

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "bank_products.db"

_NEW_PRODUCT_COLUMNS = {
    "grace_period_months": "INTEGER",
    "payment_method": "VARCHAR(50)",
    "special_terms": "TEXT",
}

_NEW_USER_COLUMNS = {
    # NOT NULL columns MUST carry a DEFAULT here - SQLite's ADD COLUMN
    # rejects NOT NULL with no default outright on a non-empty table, which
    # would otherwise surface as a production crash on init_db() rather
    # than at review time.
    "token_version": "INTEGER NOT NULL DEFAULT 0",
}


def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    # Default SQLite journaling takes an exclusive file lock for the whole
    # duration of a write transaction, blocking every other reader/writer —
    # including a login lookup — until it commits or the 5s default busy
    # timeout expires and raises "database is locked". The scraper (run on
    # every deploy and every SCRAPE_INTERVAL_HOURS) writes for a long time,
    # so under WAL mode readers no longer block on it, and busy_timeout is
    # raised as a safety net for the remaining brief writer-vs-writer case.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def get_engine(db_path: Path | None = None):
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    event.listen(engine, "connect", _set_sqlite_pragma)
    return engine


def _ensure_columns(engine, table_name: str, new_columns: dict[str, str]) -> None:
    """SQLAlchemy's create_all() only creates missing tables, not missing
    columns on tables that already exist. Since data/bank_products.db is a
    real file (not managed by a migration tool), new columns are added here
    via ALTER TABLE so existing databases pick them up without losing data.

    Limitations - there is no path here for anything beyond adding a column:
    renaming or dropping a column requires a manual ALTER TABLE plus a code
    change outside this mechanism, and a column that becomes obsolete will
    otherwise silently linger with stale data forever."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns(table_name)}
    missing = {name: sql_type for name, sql_type in new_columns.items() if name not in existing}
    if not missing:
        return
    with engine.begin() as conn:
        for name, sql_type in missing.items():
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {sql_type}"))


def init_db(engine) -> None:
    Base.metadata.create_all(engine)
    _ensure_columns(engine, "products", _NEW_PRODUCT_COLUMNS)
    _ensure_columns(engine, "users", _NEW_USER_COLUMNS)


def get_session_factory(engine):
    return sessionmaker(bind=engine)
