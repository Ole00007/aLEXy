#!/usr/bin/env python
"""Quick verification script."""
import sys
sys.path.insert(0, '/Users/olesiarasing/aLEXy')

# 1. Model import
from crm.models.calendar import CalendarEvent
print(f"1. Model OK: {CalendarEvent.__tablename__}")

# 2. App creation with blueprints
from crm import create_app
app = create_app()
bp_names = [b.name for b in app.blueprints.values()]
print(f"2. App OK. Blueprints: {bp_names}")
assert 'calendar' in bp_names, "calendar blueprint NOT registered!"
print("   'calendar' blueprint IS registered ✓")

# 3. Service import
from crm.services.calendar import get_events, create_event, update_event, delete_event, get_upcoming
print("3. Service imports OK")

# 4. Route import
from crm.routes.calendar import calendar_bp
print(f"4. Route blueprint OK: url_prefix={calendar_bp.url_prefix}")

print("\nAll checks passed ✓")
