import os
import logging
import pathlib
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

MIGRATIONS_DIR = str(pathlib.Path(__file__).with_name("migrations"))
VERSION_TABLE = "alembic_version_omeroadi"


def _mask_url(url: str) -> str:
    try:
        # Basic masking: replace password between ://user:pass@ with ******
        if '://' in url and '@' in url and ':' in url.split('://', 1)[1]:
            scheme, rest = url.split('://', 1)
            creds, tail = rest.split('@', 1)
            if ':' in creds:
                user, _ = creds.split(':', 1)
                return f"{scheme}://{user}:******@{tail}"
    except Exception:
        pass
    return url


def run_migrations_on_startup():
    if os.getenv("ADI_RUN_MIGRATIONS", "1") != "1":
        return

    # Prefer the DB URL already used by IngestTracker (initialized earlier)
    db_url = None
    try:
        from .utils.ingest_tracker import get_ingest_tracker
        tracker = get_ingest_tracker()
        if tracker and getattr(tracker, 'database_url', None):
            db_url = tracker.database_url
    except Exception:
        pass
    # Fallback to env vars if tracker not available
    if not db_url:
        db_url = (
            os.getenv("INGEST_TRACKING_DB_URL")
            or os.getenv("SQLALCHEMY_URL")
        )
    if not db_url:
        raise RuntimeError(
            "ADI migrations: No DB URL found. Ensure IngestTracker is "
            "initialized or set INGEST_TRACKING_DB_URL/SQLALCHEMY_URL."
        )

    logger = logging.getLogger(__name__)
    logger.info(f"ADI Alembic DB: {_mask_url(db_url)}")
    engine = create_engine(db_url)

    cfg = Config()
    cfg.set_main_option("script_location", MIGRATIONS_DIR)
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("version_table", VERSION_TABLE)

    insp = inspect(engine)
    has_version_table = insp.has_table(VERSION_TABLE)
    # Heuristic: if we already have ADI tables but no version table,
    # allow auto-stamp
    # so existing installs can adopt Alembic without recreating tables.
    # Disable by setting ADI_ALLOW_AUTO_STAMP=0
    # Default to not auto-stamping so first real migrations actually apply.
    # Enable explicitly with ADI_ALLOW_AUTO_STAMP=1 if you are adopting Alembic
    # on a database that already matches the head schema.
    # Allow auto-stamp if explicitly enabled OR if tables were just created
    # in this process (fresh install detected by Base.metadata.after_create).
    # We import lazily to avoid import cycles.
    allow_stamp = os.getenv("ADI_ALLOW_AUTO_STAMP", "0") == "1"
    try:
        from .utils.ingest_tracker import CREATED_ANY_TABLES
        allow_stamp = allow_stamp or CREATED_ANY_TABLES
    except Exception:
        pass

    # Postgres advisory lock to prevent concurrent migrations
    # from multiple replicas
    is_pg = engine.dialect.name == "postgresql"

    with engine.begin() as conn:
        if is_pg:
            conn.execute(
                text(
                    "SELECT pg_advisory_lock("
                    "hashtext('omeroadi_migrations'))"
                )
            )
        try:
            if allow_stamp and not has_version_table:
                # Check if any ADI table already exists (reliable table name)
                known_tables = {"imports"}  # add/adjust if needed
                if any(insp.has_table(t) for t in known_tables):
                    command.stamp(cfg, "head")  # baseline existing DB
            command.upgrade(cfg, "head")
        finally:
            if is_pg:
                conn.execute(
                    text(
                        "SELECT pg_advisory_unlock("
                        "hashtext('omeroadi_migrations'))"
                    )
                )
