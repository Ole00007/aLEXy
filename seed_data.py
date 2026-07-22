#!/usr/bin/env python3
"""Seed demo data via API and test PATCH endpoint for drag-drop."""
import json, urllib.request, urllib.error

with open("/tmp/alexy_token.txt") as f:
    token = f.read().strip()

BASE = "https://web-production-b2e68.up.railway.app"

def req(method, path, data=None, raw=False):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    # Contacts endpoint doesn't require auth
    if not path.startswith("/api/contacts"):
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            result = resp.read().decode()
            return resp.status, json.loads(result)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except:
            return e.code, body[:200]
    except Exception as e:
        return 0, str(e)

# 1. Test contacts with trailing slash
print("=== Contact with trailing slash ===")
status, body = req("GET", "/api/contacts/")
print(f"  {status}: {str(body)[:200]}")

# 2. Create contacts
contacts = [
    {"full_name": "Sarah Mitchell", "email": "sarah@example.com", "phone": "+1 (555) 123-4567", "company": "Mitchell & Co"},
    {"full_name": "James Rodriguez", "email": "james@example.com", "phone": "+1 (555) 234-5678", "company": "Rodriguez Holdings"},
    {"full_name": "Emily Chen", "email": "emily@example.com", "phone": "+1 (555) 345-6789", "company": "Chen Industries"},
    {"full_name": "Marcus Webb", "email": "marcus@example.com", "phone": "+1 (555) 456-7890", "company": "Webb Legal"},
]

contact_ids = []
print("\n=== Create Contacts ===")
for c in contacts:
    status, body = req("POST", "/api/contacts/", c)
    if status == 201:
        cid = body.get("id") if isinstance(body, dict) else None
        contact_ids.append(cid)
        print(f"  Created contact {cid}: {c['full_name']}")
    else:
        print(f"  FAILED {c['full_name']}: {status} {str(body)[:100]}")

# 3. Create cases
cases_data = [
    {"title": "Employment Dispute v. Acme Corp", "contactid": contact_ids[0], "casetype": "Employment", "priority": "high", "status": "Review"},
    {"title": "Commercial Lease Review", "contactid": contact_ids[1], "casetype": "Real Estate", "priority": "medium", "status": "Intake"},
    {"title": "Debt Collection - Smith Account", "contactid": contact_ids[2], "casetype": "Debt Collection", "priority": "urgent", "status": "Review"},
    {"title": "Family Trust Establishment", "contactid": contact_ids[3], "casetype": "Family", "priority": "low", "status": "Intake"},
]

case_ids = []
print("\n=== Create Cases ===")
for c in cases_data:
    status, body = req("POST", "/api/cases", c)
    if status == 201:
        cid = body.get("id") if isinstance(body, dict) else None
        case_ids.append(cid)
        print(f"  Created case {cid}: {c['title']}")
    else:
        print(f"  FAILED {c['title']}: {status} {str(body)[:100]}")

# 4. Create tasks for each case
tasks_data = [
    {"title": "Review client employment contract", "caseid": case_ids[0], "priority": "high", "status": "in_progress", "description": "Analyze termination clause and non-compete agreement"},
    {"title": "Draft demand letter to Acme Corp", "caseid": case_ids[0], "priority": "urgent", "status": "pending", "description": "Formal demand for severance payment"},
    {"title": "Order property valuation report", "caseid": case_ids[1], "priority": "medium", "status": "pending", "description": "Get independent valuation of commercial property"},
    {"title": "Review lease terms section 4-7", "caseid": case_ids[1], "priority": "medium", "status": "in_progress", "description": "Focus on rent escalation and maintenance clauses"},
    {"title": "File court summons", "caseid": case_ids[2], "priority": "urgent", "status": "completed", "description": "Statute of limitations approaching"},
    {"title": "Draft trust deed", "caseid": case_ids[3], "priority": "low", "status": "pending", "description": "Standard family trust with asset protection clauses"},
]

task_ids = []
print("\n=== Create Tasks ===")
for t in tasks_data:
    status, body = req("POST", "/api/tasks/", t)
    if status == 200:
        tid = body.get("id") if isinstance(body, dict) else None
        task_ids.append(tid)
        print(f"  Created task {tid}: {t['title']} ({t['status']})")
    else:
        print(f"  FAILED {t['title']}: {status} {str(body)[:100]}")

# 5. Verify counts
print("\n=== Verification ===")
status, body = req("GET", "/api/contacts/")
print(f"  Contacts: {len(body) if isinstance(body, list) else str(body)[:80]}")

status, body = req("GET", "/api/cases")
print(f"  Cases: {body.get('total', '?')}")

status, body = req("GET", "/api/tasks/")
print(f"  Tasks: {body.get('total', '?')}")

# 6. Test PATCH endpoint (drag-drop)
if task_ids:
    print(f"\n=== Test PATCH (drag-drop) task {task_ids[0]} ===")
    status, body = req("PATCH", f"/api/tasks/{task_ids[0]}", {"status": "completed"})
    print(f"  PATCH: {status} {str(body)[:200]}")

# 7. Test task completion endpoint
if task_ids:
    print(f"\n=== Test complete task {task_ids[1]} ===")
    status, body = req("PATCH", f"/api/tasks/{task_ids[1]}/complete", {"actual_duration_minutes": 45})
    print(f"  COMPLETE: {status} {str(body)[:200]}")

print("\nDone!")