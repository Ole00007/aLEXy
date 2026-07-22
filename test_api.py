#!/usr/bin/env python3
"""Test all deployed API endpoints."""
import json, os, sys, urllib.request, urllib.error

with open("/tmp/alexy_token.txt") as f:
    token = f.read().strip()

print(f"Token length: {len(token)}")

def req(method, path, data=None):
    url = f"https://web-production-b2e68.up.railway.app{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)

# Test each endpoint
for label, method, path, body in [
    ("CONTACTS GET", "GET", "/api/contacts", None),
    ("CONTACTS POST", "POST", "/api/contacts", {"full_name": "John Doe", "email": "john@example.com"}),
    ("CASES GET", "GET", "/api/cases", None),
    ("TASKS GET", "GET", "/api/tasks/", None),
    ("TASKS STATS", "GET", "/api/tasks/stats", None),
    ("CHATBOT HEALTH", "GET", "/chatbot/health", None),
    ("EMAIL SETTINGS", "GET", "/api/email/settings", None),
    ("WEBHOOKS", "GET", "/api/webhooks/subscriptions", None),
    ("CALENDAR", "GET", "/api/calendar/events", None),
    ("NOTIFICATIONS", "GET", "/api/notifications/unread-count", None),
]:
    status, body = req(method, path, body)
    print(f"{label}: {status}")
    print(f"  {str(body)[:200]}")
    print()