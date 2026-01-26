import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from ..models.base import Base


class DatabaseConnection:
    """Manages database connection and session creation."""

    def __init__(self, db_path: str = None, database_url: str = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file (for local development).
            database_url: Full database URL (for production, e.g., PostgreSQL).
        """
        if database_url:
            # Use provided database URL (PostgreSQL, etc.)
            self.db_path = None
            self.engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True
            )
        else:
            # Fall back to SQLite for local development
            if db_path is None:
                home = os.path.expanduser("~")
                db_dir = os.path.join(home, ".job-hunt-tracker")
                os.makedirs(db_dir, exist_ok=True)
                db_path = os.path.join(db_dir, "job_hunt.db")

            self.db_path = db_path
            self.engine = create_engine(
                f"sqlite:///{db_path}",
                echo=False,
                connect_args={"check_same_thread": False}
            )
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        """Drop all tables in the database. Use with caution!"""
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope around a series of operations.

        Usage:
            with db.session_scope() as session:
                session.add(some_object)
                # Changes are automatically committed if no exception
                # and rolled back if there is an exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database instance (lazy initialization)
_db_instance: DatabaseConnection = None


def get_db(db_path: str = None) -> DatabaseConnection:
    """Get or create the global database connection."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection(db_path)
    return _db_instance


def get_session() -> Session:
    """Convenience function to get a session from the global database."""
    return get_db().get_session()
