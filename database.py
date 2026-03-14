"""
database.py — Centralised JSON-backed data store for Ghost Squad Bot v2
"""

import json
import os
import uuid
import threading
from datetime import datetime, timezone

DATA_DIR  = os.path.join(os.path.dirname(__file__), 'data')
USERS_FILE     = os.path.join(DATA_DIR, 'users.json')
QUESTIONS_FILE = os.path.join(DATA_DIR, 'questions.json')
REMINDERS_FILE = os.path.join(DATA_DIR, 'reminders.json')
SETTINGS_FILE  = os.path.join(DATA_DIR, 'settings.json')
PLACEMENT_FILE = os.path.join(DATA_DIR, 'placement_log.json')

os.makedirs(DATA_DIR, exist_ok=True)

_lock = threading.Lock()


def _load(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


class Database:
    # ── Users ────────────────────────────────────────────────────────────────

    def get_all_users(self):
        with _lock:
            return _load(USERS_FILE)

    def get_user(self, discord_id: str):
        with _lock:
            return _load(USERS_FILE).get(str(discord_id))

    def set_user(self, discord_id: str, data: dict):
        with _lock:
            users = _load(USERS_FILE)
            users[str(discord_id)] = data
            _save(USERS_FILE, users)

    def delete_user(self, discord_id: str):
        with _lock:
            users = _load(USERS_FILE)
            users.pop(str(discord_id), None)
            _save(USERS_FILE, users)

    def update_user_stats(self, discord_id: str, stats: dict):
        with _lock:
            users = _load(USERS_FILE)
            uid = str(discord_id)
            if uid in users:
                users[uid]['total_solved'] = stats.get('total_solved', 0)
                users[uid]['breakdown']    = stats.get('breakdown', [0, 0, 0])
                users[uid]['last_status']  = stats.get('solved_today', False)
                users[uid]['last_synced']  = datetime.now(timezone.utc).isoformat()
                _save(USERS_FILE, users)

    # ── Questions ────────────────────────────────────────────────────────────

    def get_all_questions(self):
        with _lock:
            return _load(QUESTIONS_FILE)

    def add_question(self, asker_id: str, asker_name: str, question: str):
        with _lock:
            questions = _load(QUESTIONS_FILE)
            qid = str(uuid.uuid4())[:8]
            questions[qid] = {
                'id': qid,
                'asker_id': asker_id,
                'asker_name': asker_name,
                'question': question,
                'status': 'open',
                'solver_id': None,
                'solver_name': None,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            _save(QUESTIONS_FILE, questions)
            return qid

    def solve_question(self, qid: str, solver_id: str, solver_name: str):
        with _lock:
            questions = _load(QUESTIONS_FILE)
            if qid in questions:
                questions[qid]['status'] = 'solved'
                questions[qid]['solver_id']   = solver_id
                questions[qid]['solver_name'] = solver_name
                questions[qid]['solved_at']   = datetime.now(timezone.utc).isoformat()
                _save(QUESTIONS_FILE, questions)
                return True
            return False

    # ── Reminders ────────────────────────────────────────────────────────────

    def _reminders(self):
        data = _load(REMINDERS_FILE)
        return data if isinstance(data, list) else []

    def add_reminder(self, user_id: str, message: str, fire_at: datetime):
        with _lock:
            reminders = self._reminders()
            rid = str(uuid.uuid4())[:8]
            reminders.append({
                'id': rid,
                'user_id': str(user_id),
                'message': message,
                'fire_at': fire_at.isoformat(),
                'done': False
            })
            _save(REMINDERS_FILE, reminders)
            return rid

    def get_due_reminders(self):
        with _lock:
            reminders = self._reminders()
        now = datetime.now(timezone.utc)
        due = []
        for r in reminders:
            if not r.get('done'):
                fire_at = datetime.fromisoformat(r['fire_at'])
                if fire_at.tzinfo is None:
                    fire_at = fire_at.replace(tzinfo=timezone.utc)
                if now >= fire_at:
                    due.append(r)
        return due

    def get_user_reminders(self, user_id: str):
        with _lock:
            reminders = self._reminders()
        return [r for r in reminders
                if r['user_id'] == str(user_id) and not r.get('done')]

    def mark_reminder_done(self, rid: str):
        with _lock:
            reminders = self._reminders()
            for r in reminders:
                if r['id'] == rid:
                    r['done'] = True
                    break
            _save(REMINDERS_FILE, reminders)

    def cancel_reminder(self, rid: str, user_id: str):
        with _lock:
            reminders = self._reminders()
            before = len(reminders)
            reminders = [r for r in reminders
                         if not (r['id'] == rid and r['user_id'] == str(user_id))]
            _save(REMINDERS_FILE, reminders)
            return len(reminders) < before

    def get_all_reminders(self):
        with _lock:
            reminders = self._reminders()
        return [r for r in reminders if not r.get('done')]

    # ── Settings ─────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default=None):
        with _lock:
            return _load(SETTINGS_FILE).get(key, default)

    def set_setting(self, key: str, value):
        with _lock:
            settings = _load(SETTINGS_FILE)
            settings[key] = value
            _save(SETTINGS_FILE, settings)

    def get_all_settings(self):
        defaults = {
            'check_time': '21:30',
            'placement_time': '10:00',
            'placement_enabled': True,
            'daily_check_enabled': True,
            'welcome_enabled': True,
        }
        with _lock:
            saved = _load(SETTINGS_FILE)
        return {**defaults, **saved}

    # ── Placement Log ────────────────────────────────────────────────────────

    def log_placement_post(self, content: str):
        with _lock:
            log = _load(PLACEMENT_FILE)
            if not isinstance(log, list):
                log = []
            log.append({
                'content': content,
                'posted_at': datetime.now(timezone.utc).isoformat()
            })
            _save(PLACEMENT_FILE, log)

    def get_placement_log(self, limit=20):
        with _lock:
            log = _load(PLACEMENT_FILE)
        if not isinstance(log, list):
            return []
        return log[-limit:][::-1]