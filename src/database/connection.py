import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from ..models.base import Base


class DatabaseConnection:
    """Manages database connection and session creation."""

    def __init__(self, db_path: str = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to user's home directory
            home = os.path.expanduser("~")
            db_dir = os.path.join(home, ".job-hunt-tracker")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "job_hunt.db")

        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,  # Set to True for SQL debugging
            connect_args={"check_same_thread": False}  # Needed for SQLite
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
