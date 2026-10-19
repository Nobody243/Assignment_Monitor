import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple

from config import DB_PATH, META_PATH
from deadlines import is_open_pending

log = logging.getLogger("bahria.tracker")


def load_stored_assignments() -> Dict[str, dict]:
    """Loads previously saved assignments from the local JSON database."""
    if not DB_PATH.exists():
        return {}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Could not read the assignment database: %s", e)
        return {}


def save_assignments(assignments: Dict[str, dict]) -> None:
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(assignments, f, indent=2, default=str)
    except Exception as e:
        log.error("Could not save the assignment database: %s", e)


def clear_stored_assignments() -> None:
    for path in (DB_PATH, META_PATH):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def compare_assignments(current_list: List[dict]) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Merges a fresh scrape into the database.
    Returns (pending, extended, new_items) where:
      pending  - open assignments with no submission yet
      extended - unsubmitted assignments whose deadline moved since the last sync
                 (or that arrived already extended)
      new_items - assignments seen for the first time
    """
    stored = load_stored_assignments()
    now_iso = datetime.now().isoformat(timespec="seconds")
    pending, extended, new_items = [], [], []
    updated_store: Dict[str, dict] = {}

    for item in current_list:
        key = item.get("id") or f"{item.get('course')}_{item.get('title')}"
        item["last_checked"] = now_iso
        old_item = stored.get(key)

        if old_item is None:
            item["first_seen"] = now_iso
            new_items.append(item)
            deadline_changed = bool(item.get("is_extended"))
        else:
            item["first_seen"] = old_item.get("first_seen", now_iso)
            old_due = old_item.get("due_date", "")
            new_due = item.get("due_date", "")
            deadline_changed = (bool(old_due) and bool(new_due) and old_due != new_due) or \
                               (item.get("is_extended") and not old_item.get("is_extended"))
            if deadline_changed:
                item["previous_due_date"] = old_due or item.get("original_due_date", "")
            elif old_item.get("previous_due_date"):
                item["previous_due_date"] = old_item["previous_due_date"]

        if deadline_changed and not item.get("is_submitted"):
            extended.append(item)
        if is_open_pending(item):
            pending.append(item)
        updated_store[key] = item

    # Assignments that vanished from the portal (e.g. semester rolled over) are dropped
    # only when the scrape returned something; an empty scrape keeps the old data.
    if not current_list:
        updated_store = stored
    save_assignments(updated_store)
    return pending, extended, new_items
