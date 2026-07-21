"""Run database migration on aLEXy Railway deployment."""
import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:wbhFBvRFaGFXfcopBWKWecSAKKJYgRta@sakura.proxy.rlwy.net:33833/railway?sslmode=require'

import sys
sys.path.insert(0, '/Users/olesiarasing/aLEXy')

from wsgi import app
from crm.extensions import db
from flask_migrate import upgrade
from sqlalchemy import text

with app.app_context():
    # Verify connection
    result = db.session.execute(text("SELECT 1"))
    print("DB connection OK:", result.fetchone())
    
    print("\nRunning migration...")
    try:
        upgrade()
        print("Migration successful!")
    except Exception as e:
        print(f"Migration error: {e}")
        raise

    # Create admin user (using pbkdf2_sha256 for Python 3.9 compat)
    from crm.models.user import User
    from werkzeug.security import generate_password_hash
    
    admin = User.query.filter_by(email='admin@alexy.test').first()
    if not admin:
        admin = User()
        admin.email = 'admin@alexy.test'
        admin.role = 'admin'
        # Use pbkdf2_sha256 for Python 3.9 compatibility (no scrypt)
        admin.password_hash = generate_password_hash('Admin123!', method='pbkdf2:sha256')
        db.session.add(admin)
        db.session.commit()
        print(f"Created admin user: {admin.email} (id={admin.id})")
    else:
        print(f"Admin exists: {admin.email} (id={admin.id})")
    
    # List all tables
    result = db.session.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
    tables = [row[0] for row in result]
    print(f"Tables created: {tables}")
    
    # List alembic version
    result = db.session.execute(text("SELECT version_num FROM alembic_version"))
    row = result.fetchone()
    print(f"Alembic version: {row[0] if row else 'none'}")
