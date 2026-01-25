"""Vercel serverless function entry point."""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web.app import create_app

# Use /tmp for SQLite on Vercel (ephemeral storage)
db_path = "/tmp/job_hunt.db"
app = create_app(db_path=db_path)

# Vercel expects the app to be named 'app'
