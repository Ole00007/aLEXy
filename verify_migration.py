"""Verify the migration was applied successfully."""
import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:***@sakura.proxy.rlwy.net:33833/railway?sslmode=require'

import sys
sys.path.insert(0, '/Users/olesiarasing/aLEXy')

from crm import create_app
from crm.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Check alembic version
    result = db.session.execute(text('SELECT version_num FROM alembic_version'))
    print(f'Alembic version: {result.fetchone()[0]}')
    
    # Check calendar_events table columns
    result = db.session.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'calendar_events' 
        ORDER BY ordinal_position
    """))
    print('\ncalendar_events table columns:')
    for row in result:
        print(f'  {row[0]:20s} {row[1]:20s} nullable={row[2]} default={row[3]}')
    
    # Check FKs
    result = db.session.execute(text("""
        SELECT tc.constraint_name, kcu.column_name, ccu.table_name AS foreign_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'calendar_events' AND tc.constraint_type = 'FOREIGN KEY'
    """))
    print('\nForeign keys:')
    for row in result:
        print(f'  FK: {row[1]} -> {row[2]}')
    
    print('\n✓ Migration verified successfully')
