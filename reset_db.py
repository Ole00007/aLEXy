import sqlite3

conn = sqlite3.connect("crm_local.db")

# Check current state
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)
print("Alembic version:", conn.execute("SELECT version_num FROM alembic_version").fetchone())

# Create cases table manually (from the migration)
conn.execute("""
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER NOT NULL,
    contactid INTEGER NOT NULL,
    ownerid INTEGER,
    title VARCHAR(255) NOT NULL,
    casetype VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'Intake',
    priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
    openedat DATE NOT NULL,
    duedate DATE,
    assignedto INTEGER,
    createdat DATETIME NOT NULL,
    updatedat DATETIME NOT NULL,
    PRIMARY KEY (id)
)
""")

# Add FK from cases.contactid to contacts.id
conn.execute("""
CREATE TABLE cases_new (
    id INTEGER NOT NULL,
    contactid INTEGER NOT NULL REFERENCES contacts(id),
    ownerid INTEGER,
    title VARCHAR(255) NOT NULL,
    casetype VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'Intake',
    priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
    openedat DATE NOT NULL,
    duedate DATE,
    assignedto INTEGER REFERENCES users(id),
    createdat DATETIME NOT NULL,
    updatedat DATETIME NOT NULL,
    PRIMARY KEY (id)
)
""")

# Copy data
conn.execute("INSERT INTO cases_new SELECT * FROM cases")
conn.execute("DROP TABLE cases")
conn.execute("ALTER TABLE cases_new RENAME TO cases")

# Add FK from tasks.caseid to cases.id
conn.execute("""
CREATE TABLE tasks_new (
    id INTEGER NOT NULL,
    caseid INTEGER NOT NULL REFERENCES cases(id),
    userid INTEGER REFERENCES users(id),
    assigned_to INTEGER REFERENCES users(id),
    eventid INTEGER REFERENCES events(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    duedate DATE,
    duration_minutes INTEGER,
    actual_duration_minutes INTEGER,
    completed_at DATETIME,
    parent_task_id INTEGER REFERENCES tasks(id),
    depends_on JSON,
    createdat DATETIME NOT NULL,
    updatedat DATETIME NOT NULL,
    PRIMARY KEY (id)
)
""")

conn.execute("INSERT INTO tasks_new SELECT * FROM tasks")
conn.execute("DROP TABLE tasks")
conn.execute("ALTER TABLE tasks_new RENAME TO tasks")

conn.commit()

tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("\nAfter fix, tables:", tables)
conn.close()
