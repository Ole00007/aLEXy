"""WSGI entry point for Railway deployment."""

import os
from crm import create_app
from crm.extensions import db

# Force rebuild marker
BUILD_VERSION = "20260720_v2"

app = create_app()

def ensure_webhook_tables():
    """Ensure webhook tables exist (migration may not auto-run on Railway)."""
    try:
        from sqlalchemy import text
        result = db.session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'webhook_subscriptions')"
        )).scalar()
        if not result:
            print("Creating webhook tables (migration missing from Railway)...")
            db.session.execute(text("""
                CREATE TABLE webhook_subscriptions (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    url VARCHAR(500) NOT NULL,
                    events JSON NOT NULL,
                    secret VARCHAR(64) NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """))
            db.session.execute(text("""
                CREATE TABLE webhook_deliveries (
                    id INTEGER PRIMARY KEY,
                    subscription_id INTEGER NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
                    url VARCHAR(500) NOT NULL,
                    payload JSON NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    http_status_code INTEGER,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """))
            db.session.commit()
            print("Webhook tables created successfully via SQL.")
    except Exception as e:
        db.session.rollback()
        print(f"Warning: Could not auto-create webhook tables: {e}")

# Run migration check on startup
with app.app_context():
    ensure_webhook_tables()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
