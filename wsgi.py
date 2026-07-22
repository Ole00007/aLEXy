"""WSGI entry point for Railway deployment."""

import os
from crm import create_app
from crm.extensions import db
from crm.models.webhook import WebhookSubscription, WebhookDelivery

# Force rebuild marker
BUILD_VERSION = "20260720_v2"

app = create_app()

def ensure_webhook_tables():
    """Ensure webhook tables exist (migration may not auto-run on Railway)."""
    try:
        # Check if webhook_subscriptions table exists
        from sqlalchemy import text
        result = db.session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'webhook_subscriptions')"
        )).scalar()
        if not result:
            print("Creating webhook tables (migration missing from Railway)...")
            # Create tables manually
            from sqlalchemy import MetaData, Table, Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text, func, text
            metadata = MetaData()
            
            # webhook_subscriptions
            Table('webhook_subscriptions', metadata,
                Column('id', Integer, primary_key=True),
                Column('name', String(255), nullable=False),
                Column('url', String(500), nullable=False),
                Column('events', JSON, nullable=False),
                Column('secret', String(64), nullable=False),
                Column('active', Boolean, nullable=False, default=True),
                Column('created_by', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
                Column('created_at', DateTime, server_default=func.now(), nullable=False),
                Column('updated_at', DateTime, server_default=func.now(), nullable=False),
            )
            
            # webhook_deliveries
            Table('webhook_deliveries', metadata,
                Column('id', Integer, primary_key=True),
                Column('subscription_id', Integer, ForeignKey('webhook_subscriptions.id', ondelete='CASCADE'), nullable=False),
                Column('url', String(500), nullable=False),
                Column('payload', JSON, nullable=False),
                Column('status', String(20), nullable=False, server_default='pending'),
                Column('http_status_code', Integer, nullable=True),
                Column('retry_count', Integer, nullable=False, default=0),
                Column('last_attempt_at', DateTime, nullable=True),
                Column('error_message', Text, nullable=True),
                Column('created_at', DateTime, server_default=func.now(), nullable=False),
            )
            
            metadata.create_all(db.engine)
            db.session.commit()
            print("Webhook tables created successfully.")
    except Exception as e:
        print(f"Warning: Could not auto-create webhook tables: {e}")

# Run migration check on startup
with app.app_context():
    ensure_webhook_tables()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
