import sqlite3

conn = sqlite3.connect("crm_local.db")

# Check webhook tables exist
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", sorted(tables))

# Check alembic version
print("Alembic version:", conn.execute("SELECT version_num FROM alembic_version").fetchone())

# Check webhook_subscriptions schema
print("\nwebhook_subscriptions columns:")
for row in conn.execute("PRAGMA table_info(webhook_subscriptions)").fetchall():
    print("  ", row)

print("\nwebhook_deliveries columns:")
for row in conn.execute("PRAGMA table_info(webhook_deliveries)").fetchall():
    print("  ", row)

conn.close()
