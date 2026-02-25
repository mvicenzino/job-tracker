import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
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
        self._run_migrations()

    def _run_migrations(self):
        """Run simple schema migrations for new columns and enum values."""
        try:
            inspector = inspect(self.engine)
            is_postgres = 'postgresql' in str(self.engine.url)

            # PostgreSQL enum migrations - add new values to existing enum types
            if is_postgres:
                with self.engine.connect() as conn:
                    # Add ARCHIVED to applicationstatus enum if missing
                    try:
                        # Check if ARCHIVED already exists in the enum
                        result = conn.execute(text("""
                            SELECT EXISTS (
                                SELECT 1 FROM pg_enum
                                WHERE enumlabel = 'ARCHIVED'
                                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'applicationstatus')
                            )
                        """))
                        exists = result.scalar()
                        if not exists:
                            conn.execute(text("ALTER TYPE applicationstatus ADD VALUE 'ARCHIVED'"))
                            conn.commit()
                            print("[Migration] Added ARCHIVED to applicationstatus enum")
                    except Exception as e:
                        print(f"[Migration] Failed to add ARCHIVED enum value: {e}")

            # Check if users table exists and add new columns if missing
            if 'users' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('users')]
                print(f"[Migration] Existing users columns: {columns}")

                with self.engine.connect() as conn:
                    if 'onboarding_completed' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE'))
                            conn.commit()
                            print("[Migration] Added onboarding_completed column")
                        except Exception as e:
                            print(f"[Migration] Failed to add onboarding_completed: {e}")

                    if 'onboarding_dismissed' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN onboarding_dismissed BOOLEAN DEFAULT FALSE'))
                            conn.commit()
                            print("[Migration] Added onboarding_dismissed column")
                        except Exception as e:
                            print(f"[Migration] Failed to add onboarding_dismissed: {e}")

                    # Notification preferences
                    if 'email_digest_enabled' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN email_digest_enabled BOOLEAN DEFAULT FALSE'))
                            conn.commit()
                            print("[Migration] Added email_digest_enabled column")
                        except Exception as e:
                            print(f"[Migration] Failed to add email_digest_enabled: {e}")

                    if 'email_digest_frequency' not in columns:
                        try:
                            conn.execute(text("ALTER TABLE users ADD COLUMN email_digest_frequency VARCHAR(20) DEFAULT 'weekly'"))
                            conn.commit()
                            print("[Migration] Added email_digest_frequency column")
                        except Exception as e:
                            print(f"[Migration] Failed to add email_digest_frequency: {e}")

                    if 'browser_notifications_enabled' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN browser_notifications_enabled BOOLEAN DEFAULT TRUE'))
                            conn.commit()
                            print("[Migration] Added browser_notifications_enabled column")
                        except Exception as e:
                            print(f"[Migration] Failed to add browser_notifications_enabled: {e}")

                    if 'notify_interview_reminders' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN notify_interview_reminders BOOLEAN DEFAULT TRUE'))
                            conn.commit()
                            print("[Migration] Added notify_interview_reminders column")
                        except Exception as e:
                            print(f"[Migration] Failed to add notify_interview_reminders: {e}")

                    if 'notify_follow_up_nudges' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN notify_follow_up_nudges BOOLEAN DEFAULT TRUE'))
                            conn.commit()
                            print("[Migration] Added notify_follow_up_nudges column")
                        except Exception as e:
                            print(f"[Migration] Failed to add notify_follow_up_nudges: {e}")

                    if 'follow_up_nudge_days' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN follow_up_nudge_days INTEGER DEFAULT 7'))
                            conn.commit()
                            print("[Migration] Added follow_up_nudge_days column")
                        except Exception as e:
                            print(f"[Migration] Failed to add follow_up_nudge_days: {e}")

                    # Profile fields
                    if 'avatar_url' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)'))
                            conn.commit()
                            print("[Migration] Added avatar_url column")
                        except Exception as e:
                            print(f"[Migration] Failed to add avatar_url: {e}")

                    # Widen avatar_url to TEXT for base64 data URIs (Postgres only; SQLite TEXT is already unlimited)
                    if is_postgres and 'avatar_url' in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ALTER COLUMN avatar_url TYPE TEXT'))
                            conn.commit()
                            print("[Migration] Widened avatar_url column to TEXT")
                        except Exception as e:
                            # Ignore if already TEXT
                            pass

                    if 'display_name' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN display_name VARCHAR(100)'))
                            conn.commit()
                            print("[Migration] Added display_name column")
                        except Exception as e:
                            print(f"[Migration] Failed to add display_name: {e}")

                    # Subscription & usage tracking
                    if 'subscription_tier' not in columns:
                        try:
                            conn.execute(text("ALTER TABLE users ADD COLUMN subscription_tier VARCHAR(20) DEFAULT 'free'"))
                            conn.commit()
                            print("[Migration] Added subscription_tier column")
                        except Exception as e:
                            print(f"[Migration] Failed to add subscription_tier: {e}")

                    if 'subscription_started_at' not in columns:
                        try:
                            if is_postgres:
                                conn.execute(text('ALTER TABLE users ADD COLUMN subscription_started_at TIMESTAMP'))
                            else:
                                conn.execute(text('ALTER TABLE users ADD COLUMN subscription_started_at DATETIME'))
                            conn.commit()
                            print("[Migration] Added subscription_started_at column")
                        except Exception as e:
                            print(f"[Migration] Failed to add subscription_started_at: {e}")

                    if 'usage_reset_month' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN usage_reset_month VARCHAR(7)'))
                            conn.commit()
                            print("[Migration] Added usage_reset_month column")
                        except Exception as e:
                            print(f"[Migration] Failed to add usage_reset_month: {e}")

                    if 'ai_scores_used' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN ai_scores_used INTEGER DEFAULT 0'))
                            conn.commit()
                            print("[Migration] Added ai_scores_used column")
                        except Exception as e:
                            print(f"[Migration] Failed to add ai_scores_used: {e}")

                    if 'ai_cover_letters_used' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN ai_cover_letters_used INTEGER DEFAULT 0'))
                            conn.commit()
                            print("[Migration] Added ai_cover_letters_used column")
                        except Exception as e:
                            print(f"[Migration] Failed to add ai_cover_letters_used: {e}")

                    if 'ai_interview_preps_used' not in columns:
                        try:
                            conn.execute(text('ALTER TABLE users ADD COLUMN ai_interview_preps_used INTEGER DEFAULT 0'))
                            conn.commit()
                            print("[Migration] Added ai_interview_preps_used column")
                        except Exception as e:
                            print(f"[Migration] Failed to add ai_interview_preps_used: {e}")

            # Check if applications table needs new columns
            if 'applications' in inspector.get_table_names():
                app_columns = [col['name'] for col in inspector.get_columns('applications')]
                with self.engine.connect() as conn:
                    if 'resume_version_id' not in app_columns:
                        try:
                            conn.execute(text('ALTER TABLE applications ADD COLUMN resume_version_id INTEGER'))
                            conn.commit()
                            print("[Migration] Added resume_version_id column to applications")
                        except Exception as e:
                            print(f"[Migration] Failed to add resume_version_id: {e}")

                    if 'fit_score' not in app_columns:
                        try:
                            conn.execute(text('ALTER TABLE applications ADD COLUMN fit_score INTEGER'))
                            conn.commit()
                            print("[Migration] Added fit_score column to applications")
                        except Exception as e:
                            print(f"[Migration] Failed to add fit_score: {e}")

            # Check if jobs table needs fit scoring columns
            if 'jobs' in inspector.get_table_names():
                job_columns = [col['name'] for col in inspector.get_columns('jobs')]
                with self.engine.connect() as conn:
                    if 'fit_score' not in job_columns:
                        try:
                            conn.execute(text('ALTER TABLE jobs ADD COLUMN fit_score INTEGER'))
                            conn.commit()
                            print("[Migration] Added fit_score column to jobs")
                        except Exception as e:
                            print(f"[Migration] Failed to add fit_score: {e}")

                    if 'fit_analysis' not in job_columns:
                        try:
                            conn.execute(text('ALTER TABLE jobs ADD COLUMN fit_analysis TEXT'))
                            conn.commit()
                            print("[Migration] Added fit_analysis column to jobs")
                        except Exception as e:
                            print(f"[Migration] Failed to add fit_analysis: {e}")

                    if 'scored_at' not in job_columns:
                        try:
                            if is_postgres:
                                conn.execute(text('ALTER TABLE jobs ADD COLUMN scored_at TIMESTAMP'))
                            else:
                                conn.execute(text('ALTER TABLE jobs ADD COLUMN scored_at DATETIME'))
                            conn.commit()
                            print("[Migration] Added scored_at column to jobs")
                        except Exception as e:
                            print(f"[Migration] Failed to add scored_at: {e}")

                    if 'scored_with_resume_id' not in job_columns:
                        try:
                            conn.execute(text('ALTER TABLE jobs ADD COLUMN scored_with_resume_id INTEGER'))
                            conn.commit()
                            print("[Migration] Added scored_with_resume_id column to jobs")
                        except Exception as e:
                            print(f"[Migration] Failed to add scored_with_resume_id: {e}")

            # Add is_flagged to companies table
            if 'companies' in inspector.get_table_names():
                company_columns = [col['name'] for col in inspector.get_columns('companies')]
                if 'is_flagged' not in company_columns:
                    with self.engine.connect() as conn:
                        try:
                            conn.execute(text('ALTER TABLE companies ADD COLUMN is_flagged BOOLEAN DEFAULT FALSE'))
                            conn.commit()
                            print("[Migration] Added is_flagged column to companies")
                        except Exception as e:
                            print(f"[Migration] Failed to add is_flagged to companies: {e}")

            # Create note_mentions table if it doesn't exist
            if 'note_mentions' not in inspector.get_table_names():
                with self.engine.connect() as conn:
                    try:
                        conn.execute(text("""
                            CREATE TABLE note_mentions (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                                UNIQUE(note_id, contact_id)
                            )
                        """) if not is_postgres else text("""
                            CREATE TABLE note_mentions (
                                id SERIAL PRIMARY KEY,
                                note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                                updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
                                UNIQUE(note_id, contact_id)
                            )
                        """))
                        conn.commit()
                        print("[Migration] Created note_mentions table")
                    except Exception as e:
                        print(f"[Migration] Failed to create note_mentions table: {e}")

            # Add user_id to notes table
            if 'notes' in inspector.get_table_names():
                note_columns = [col['name'] for col in inspector.get_columns('notes')]
                if 'user_id' not in note_columns:
                    with self.engine.connect() as conn:
                        try:
                            conn.execute(text('ALTER TABLE notes ADD COLUMN user_id INTEGER REFERENCES users(id)'))
                            conn.commit()
                            print("[Migration] Added user_id column to notes")
                            # Backfill user_id from parent entities
                            try:
                                conn.execute(text("""
                                    UPDATE notes SET user_id = (
                                        SELECT COALESCE(
                                            (SELECT user_id FROM applications WHERE applications.id = notes.application_id),
                                            (SELECT user_id FROM contacts WHERE contacts.id = notes.contact_id),
                                            (SELECT user_id FROM companies WHERE companies.id = notes.company_id),
                                            (SELECT user_id FROM jobs WHERE jobs.id = notes.job_id)
                                        )
                                    ) WHERE user_id IS NULL
                                """))
                                conn.commit()
                                print("[Migration] Backfilled user_id on existing notes")
                            except Exception as e:
                                print(f"[Migration] Failed to backfill notes user_id: {e}")
                        except Exception as e:
                            print(f"[Migration] Failed to add user_id to notes: {e}")

            # Add new columns to interview_preps if they exist
            if 'interview_preps' in inspector.get_table_names():
                prep_columns = [col['name'] for col in inspector.get_columns('interview_preps')]
                with self.engine.connect() as conn:
                    for col_name in ('red_flags', 'closing_strategy'):
                        if col_name not in prep_columns:
                            try:
                                if is_postgres:
                                    conn.execute(text(f'ALTER TABLE interview_preps ADD COLUMN {col_name} JSONB'))
                                else:
                                    conn.execute(text(f'ALTER TABLE interview_preps ADD COLUMN {col_name} JSON'))
                                conn.commit()
                                print(f"[Migration] Added {col_name} column to interview_preps")
                            except Exception as e:
                                print(f"[Migration] Failed to add {col_name}: {e}")

            # --- Workspace tables ---
            table_names = inspector.get_table_names()

            if 'workspaces' not in table_names:
                with self.engine.connect() as conn:
                    try:
                        if is_postgres:
                            conn.execute(text("""
                                CREATE TABLE workspaces (
                                    id SERIAL PRIMARY KEY,
                                    name VARCHAR(255) NOT NULL,
                                    created_by INTEGER NOT NULL REFERENCES users(id),
                                    invite_code VARCHAR(32) UNIQUE NOT NULL,
                                    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                                    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
                                )
                            """))
                        else:
                            conn.execute(text("""
                                CREATE TABLE workspaces (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    name VARCHAR(255) NOT NULL,
                                    created_by INTEGER NOT NULL REFERENCES users(id),
                                    invite_code VARCHAR(32) UNIQUE NOT NULL,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                                )
                            """))
                        conn.commit()
                        print("[Migration] Created workspaces table")
                    except Exception as e:
                        print(f"[Migration] Failed to create workspaces table: {e}")

            if 'workspace_members' not in table_names:
                with self.engine.connect() as conn:
                    try:
                        if is_postgres:
                            conn.execute(text("""
                                CREATE TABLE workspace_members (
                                    id SERIAL PRIMARY KEY,
                                    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                    role VARCHAR(20) NOT NULL DEFAULT 'member',
                                    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                                    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
                                    UNIQUE(workspace_id, user_id)
                                )
                            """))
                        else:
                            conn.execute(text("""
                                CREATE TABLE workspace_members (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                    role VARCHAR(20) NOT NULL DEFAULT 'member',
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                                    UNIQUE(workspace_id, user_id)
                                )
                            """))
                        conn.commit()
                        print("[Migration] Created workspace_members table")
                    except Exception as e:
                        print(f"[Migration] Failed to create workspace_members table: {e}")

            # Add workspace_id and created_by to shared entity tables
            shared_tables = ['companies', 'jobs', 'applications', 'contacts', 'events', 'notes']
            for tbl in shared_tables:
                if tbl in table_names:
                    tbl_columns = [col['name'] for col in inspector.get_columns(tbl)]
                    with self.engine.connect() as conn:
                        if 'workspace_id' not in tbl_columns:
                            try:
                                conn.execute(text(f'ALTER TABLE {tbl} ADD COLUMN workspace_id INTEGER REFERENCES workspaces(id)'))
                                conn.commit()
                                print(f"[Migration] Added workspace_id column to {tbl}")
                            except Exception as e:
                                print(f"[Migration] Failed to add workspace_id to {tbl}: {e}")
                        if 'created_by' not in tbl_columns:
                            try:
                                conn.execute(text(f'ALTER TABLE {tbl} ADD COLUMN created_by INTEGER REFERENCES users(id)'))
                                conn.commit()
                                print(f"[Migration] Added created_by column to {tbl}")
                            except Exception as e:
                                print(f"[Migration] Failed to add created_by to {tbl}: {e}")

        except Exception as e:
            print(f"[Migration] Migration check failed: {e}")

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
