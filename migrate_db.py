"""Database migration script for adding user authentication."""
import os
import sys

# Get DATABASE_URL from command line or environment
DATABASE_URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("Usage: python migrate_db.py <DATABASE_URL>")
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
    # Check if users table exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'users'
        );
    """))
    users_exists = result.scalar()

    if not users_exists:
        print("Creating users table...")
        conn.execute(text("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                api_key VARCHAR(64) UNIQUE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(text("CREATE INDEX ix_users_email ON users (email);"))
        conn.execute(text("CREATE INDEX ix_users_api_key ON users (api_key);"))
        print("Users table created!")
    else:
        print("Users table already exists.")
        # Check if api_key column exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'api_key'
            );
        """))
        if not result.scalar():
            print("Adding api_key column to users...")
            conn.execute(text("ALTER TABLE users ADD COLUMN api_key VARCHAR(64) UNIQUE;"))
            conn.execute(text("CREATE INDEX ix_users_api_key ON users (api_key);"))

    # Check if resume_text column exists in users
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'resume_text'
        );
    """))
    if not result.scalar():
        print("Adding resume_text column to users...")
        conn.execute(text("ALTER TABLE users ADD COLUMN resume_text TEXT;"))
        print("resume_text column added!")
    else:
        print("Users table already has resume_text.")

    # Check if resume_filename column exists in users
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'resume_filename'
        );
    """))
    if not result.scalar():
        print("Adding resume_filename column to users...")
        conn.execute(text("ALTER TABLE users ADD COLUMN resume_filename VARCHAR(255);"))
        print("resume_filename column added!")
    else:
        print("Users table already has resume_filename.")

    # Check if user_id column exists in companies
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'companies' AND column_name = 'user_id'
        );
    """))
    companies_has_user_id = result.scalar()

    # Check if user_id column exists in contacts
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'contacts' AND column_name = 'user_id'
        );
    """))
    contacts_has_user_id = result.scalar()

    # If we need to add user_id columns, first create a default user
    if not companies_has_user_id or not contacts_has_user_id:
        # Check if there's existing data
        result = conn.execute(text("SELECT COUNT(*) FROM companies;"))
        company_count = result.scalar()

        result = conn.execute(text("SELECT COUNT(*) FROM contacts;"))
        contact_count = result.scalar()

        default_user_id = None
        if company_count > 0 or contact_count > 0:
            # Create a default user for existing data
            print("Creating default user for existing data...")
            # Use a placeholder password - user should change it
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash('changeme123', method='pbkdf2:sha256')

            result = conn.execute(text("""
                INSERT INTO users (email, password_hash, is_active, created_at, updated_at)
                VALUES ('admin@example.com', :password_hash, TRUE, NOW(), NOW())
                ON CONFLICT (email) DO UPDATE SET email = users.email
                RETURNING id;
            """), {"password_hash": password_hash})
            default_user_id = result.scalar()
            print(f"Default user created with ID: {default_user_id}")
            print("  Email: admin@example.com")
            print("  Password: changeme123")
            print("  (Please change this password after logging in!)")

    if not companies_has_user_id:
        print("Adding user_id column to companies...")
        conn.execute(text("ALTER TABLE companies ADD COLUMN user_id INTEGER;"))

        if default_user_id:
            print("Assigning existing companies to default user...")
            conn.execute(text("UPDATE companies SET user_id = :user_id WHERE user_id IS NULL;"),
                        {"user_id": default_user_id})

        conn.execute(text("ALTER TABLE companies ALTER COLUMN user_id SET NOT NULL;"))
        conn.execute(text("ALTER TABLE companies ADD CONSTRAINT fk_companies_user FOREIGN KEY (user_id) REFERENCES users(id);"))
        conn.execute(text("CREATE INDEX ix_companies_user_id ON companies (user_id);"))
        print("Companies table updated!")
    else:
        print("Companies table already has user_id.")

    if not contacts_has_user_id:
        print("Adding user_id column to contacts...")
        conn.execute(text("ALTER TABLE contacts ADD COLUMN user_id INTEGER;"))

        if default_user_id:
            print("Assigning existing contacts to default user...")
            conn.execute(text("UPDATE contacts SET user_id = :user_id WHERE user_id IS NULL;"),
                        {"user_id": default_user_id})

        conn.execute(text("ALTER TABLE contacts ALTER COLUMN user_id SET NOT NULL;"))
        conn.execute(text("ALTER TABLE contacts ADD CONSTRAINT fk_contacts_user FOREIGN KEY (user_id) REFERENCES users(id);"))
        conn.execute(text("CREATE INDEX ix_contacts_user_id ON contacts (user_id);"))
        print("Contacts table updated!")
    else:
        print("Contacts table already has user_id.")

    conn.commit()
    print("\nMigration complete!")
