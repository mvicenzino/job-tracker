"""Vercel serverless function entry point."""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web.app import create_app

# Create app - will use DATABASE_URL env var if set, otherwise falls back to SQLite
app = create_app()
