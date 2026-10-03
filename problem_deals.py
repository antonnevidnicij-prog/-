import os
import time
import requests

# Токен и поддомен из окружения. Access-токен amoCRM живёт 24 ч, в проде нужен refresh
BASE = f"https://{os.environ['AMO_SUBDOMAIN']}.amocrm.ru/api/v4"
SESSION = requests.Session()
SESSION.headers["Authorization"] = f"Bearer {os.environ['AMO_TOKEN']}"
CLOSED = (142, 143)  # системные статусы: успех / провал, одинаковы во всех воронках


def fetch_all(path, key, params=None):
    items, page, retries = [], 1, 0
    while True:
        try:
            r = SESSION.get(f"{BASE}/{path}", timeout=30,
                            params={**(params or {}), "page": page, "limit": 250})
        except requests.exceptions.RequestException:
            if retries >= 5:
                raise
            retries += 1
            time.sleep(2 ** retries)  # сетевой сбой: тоже ретраим с backoff
            continue
        if r.status_code == 429 and retries < 5:  # лимит запросов: ждём и повторяем
            retries += 1
            time.sleep(2 ** retries)
            continue
        if r.status_code == 204:  # данных нет
            break
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("_embedded", {}).get(key, []))
        if "next" not in data.get("_links", {}):
            break
        page += 1
        retries = 0
        time.sleep(0.15)  # лимит ~7 запросов/сек
    return items


def problem_deals():
    now = int(time.time())
    # фильтр по датам не нужен: ищем ПРОБЛЕМНЫЕ сделки среди всех открытых сейчас,
    # а не те, что созданы за 30 дней — старая зависшая сделка это тоже проблема
    leads = [l for l in fetch_all("leads", "leads")
             if l["status_id"] not in CLOSED]
    tasks = fetch_all("tasks", "tasks", {
        "filter[entity_type]": "leads",
        "filter[is_completed]": 0,  # только незавершённые задачи
    })
    by_lead = {}
    for t in tasks:
        by_lead.setdefault(t["entity_id"], []).append(t)

    no_active_tasks, overdue = [], []
    for lead in leads:
        lead_tasks = by_lead.get(lead["id"], [])
        if not lead_tasks:
            no_active_tasks.append(lead)
        elif any(t.get("complete_till", now) < now for t in lead_tasks):
            overdue.append(lead)  # complete_till нет: не считаем просроченной
    return no_active_tasks, overdue
