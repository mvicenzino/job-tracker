"""Update the admin user's email and password."""
import os
import sys

if len(sys.argv) < 3:
    print("Usage: python update_user.py <new_email> <new_password> [DATABASE_URL]")
    print("Example: python update_user.py myemail@gmail.com MyNewPassword123")
    sys.exit(1)

new_email = sys.argv[1]
new_password = sys.argv[2]
DATABASE_URL = sys.argv[3] if len(sys.argv) > 3 else os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("Please provide DATABASE_URL as third argument or set it as environment variable")
    sys.exit(1)

# Fix URL format for SQLAlchemy
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
elif DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg2://', 1)

from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check if admin user exists
    result = conn.execute(text("SELECT id, email FROM users WHERE email = 'admin@example.com';"))
    admin_user = result.fetchone()

    if not admin_user:
        print("No admin@example.com user found.")
        sys.exit(1)

    # Check if new email already exists
    result = conn.execute(text("SELECT id FROM users WHERE email = :email;"), {"email": new_email})
    existing = result.fetchone()

    if existing:
        print(f"Error: A user with email {new_email} already exists.")
        sys.exit(1)

    # Update the admin user
    password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    conn.execute(text("""
        UPDATE users
        SET email = :email, password_hash = :password_hash, updated_at = NOW()
        WHERE email = 'admin@example.com';
    """), {"email": new_email, "password_hash": password_hash})

    conn.commit()
    print(f"Success! Updated admin account:")
    print(f"  New email: {new_email}")
    print(f"  New password: {new_password}")
    print(f"\nYou can now log in with these credentials.")
