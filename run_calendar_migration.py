"""Run database migration on aLEXy Railway deployment."""
import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:wbhFBvRFaGFXfcopBWKWecSAKKJYgRta@postgres.railway.internal:5432/railway'

import sys
sys.path.insert(0, '/Users/olesiarasing/aLEXy')

from wsgi import app
from crm.extensions import db
from flask_migrate import upgrade
from sqlalchemy import text
from sqlalchemy.orm import Session

with app.app_context():
    # Try to connect
    try:
        result = db.session.execute(text("SELECT 1"))
        print("DB connection OK:", result.fetchone())

        # List current alembic version
        result = db.session.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        print(f"Current alembic version: {row[0] if row else 'none'}")

        # List existing tables
        result = db.session.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
        tables = [r[0] for r in result]
        print(f"Existing tables: {tables}")

        print("\nRunning migration...")
        upgrade()
        print("Migration successful!")

        # Verify new table
        result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'calendar_events' ORDER BY ordinal_position"))
        columns = [r[0] for r in result]
        print(f"\ncalendar_events columns: {columns}")

    except Exception as e:
        print(f"Error: {e}")
        print("\nTrying proxy connection...")
        # Fallback: use proxy connection
        from flask_migrate import upgrade as _upgrade
        from sqlalchemy import create_engine as _ce
        
        proxy_url = "postgresql://postgres:wbhFBvRFaGFXfcopBWKWecSAKKJYgRta@sakura.proxy.rlwy.net:33833/railway?sslmode=require"
        engine = _ce(proxy_url)
        print(f"Connected via proxy: {engine.url}")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            print(f"Alembic version: {row[0] if row else 'none'}")
            
        # Run migration via alembic command
        import subprocess
        result = subprocess.run(
            ['DATABASE_URL=' + proxy_url, '.venv.local/bin/flask', 'db', 'upgrade'],
            cwd='/Users/olesiarasing/aLEXy',
            capture_output=True, text=True,
            env={**os.environ, 'DATABASE_URL': proxy_url}
        )
        print(result.stdout)
        print(result.stderr)
        print(f"Return code: {result.returncode}")
