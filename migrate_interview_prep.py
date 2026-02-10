"""Database migration script for adding interview_preps table."""
import os
import sys

# Get DATABASE_URL from command line or environment
DATABASE_URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("Usage: python migrate_interview_prep.py <DATABASE_URL>")
    print("Or set DATABASE_URL environment variable")
    sys.exit(1)

# Fix URL format for SQLAlchemy
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
elif DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg2://', 1)

from sqlalchemy import create_engine, text

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check if interview_preps table exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'interview_preps'
        );
    """))
    table_exists = result.scalar()

    if not table_exists:
        print("Creating interview_preps table...")
        conn.execute(text("""
            CREATE TABLE interview_preps (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                resume_version_id INTEGER REFERENCES resume_versions(id),
                questions JSONB,
                talking_points JSONB,
                questions_to_ask JSONB,
                company_brief JSONB,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(text("CREATE INDEX ix_interview_preps_user_id ON interview_preps (user_id);"))
        conn.execute(text("CREATE INDEX ix_interview_preps_application_id ON interview_preps (application_id);"))
        print("interview_preps table created!")
    else:
        print("interview_preps table already exists.")

    conn.commit()
    print("\nMigration complete!")
