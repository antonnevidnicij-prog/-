import os
import time
import requests

BASE = f"https://{os.environ['AMO_SUBDOMAIN']}.amocrm.ru/api/v4"
SESSION = requests.Session()
SESSION.headers["Authorization"] = f"Bearer {os.environ['AMO_TOKEN']}"
CLOSED = (142, 143)  # статусы успех/провал, одинаковы во всех воронках

def fetch_all(path, key, params=None):
    items, page, retries = [], 1, 0
    while True:
        try:
            r = SESSION.get(f"{BASE}/{path}", timeout=30,
                             params={**(params or {}), "page": page, "limit": 250})
        except requests.exceptions.RequestException:
            retries += 1
            if retries > 5: raise
            time.sleep(2 ** retries); continue
        if r.status_code == 429 and retries < 5:
            retries += 1
            time.sleep(2 ** retries); continue
        if r.status_code == 204: break
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("_embedded", {}).get(key, []))
        if "next" not in data.get("_links", {}):
            break
        page += 1
        retries = 0
        time.sleep(0.15)
    return items

def problem_deals():
    now = int(time.time())
    leads = [l for l in fetch_all("leads", "leads") if l["status_id"] not in CLOSED]
    tasks = fetch_all("tasks", "tasks", {
        "filter[entity_type]": "leads", "filter[is_completed]": 0,
    })
    by_lead = {}
    for t in tasks:
        by_lead.setdefault(t["entity_id"], []).append(t)
    no_active, overdue = [], []
    for lead in leads:
        lt = by_lead.get(lead["id"], [])
        if not lt:
            no_active.append(lead)
        elif any(t.get("complete_till", now) < now for t in lt):
            overdue.append(lead)
    return no_active, overdue
