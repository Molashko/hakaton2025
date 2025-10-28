from typing import Optional, Dict, Any, List, Tuple
import json
import secrets
import time
from .db import get_connection


# Users

def create_user(email: str, name: str, password_hash: str) -> Optional[int]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
            (email, name, password_hash),
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_name(user_id: int, name: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    conn.commit()
    conn.close()


def update_user_password(user_id: int, password_hash: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    conn.close()


# Custom fields

def list_custom_fields() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, type, COALESCE(required,0) as required FROM custom_fields ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_custom_field(name: str, type_: str, required: bool = False) -> Optional[int]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO custom_fields (name, type, required) VALUES (?, ?, ?)", (name, type_, 1 if required else 0)
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        return None
    finally:
        conn.close()


def set_field_required(field_id: int, required: bool) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE custom_fields SET required = ? WHERE id = ?", (1 if required else 0, field_id))
    conn.commit()
    conn.close()


def delete_custom_field(field_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ticket_fields WHERE field_id = ?", (field_id,))
    cur.execute("DELETE FROM custom_fields WHERE id = ?", (field_id,))
    conn.commit()
    conn.close()


# Executors

def list_executors() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM executors ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_executor_by_name(name: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM executors WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_executor(name: str, daily_limit: int = 10, parameters: Dict[str, Any] | None = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO executors (name, daily_limit, assigned_today, parameters, active) VALUES (?, ?, 0, ?, 1)",
        (name, int(daily_limit), json.dumps(parameters or {})),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def ensure_executor_for_user(name: str) -> int:
    ex = get_executor_by_name(name)
    if ex:
        return ex["id"]
    return create_executor(name, daily_limit=10, parameters={"keywords": []})


def get_executor(eid: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM executors WHERE id = ?", (eid,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_executor(eid: int, name: str, daily_limit: int, parameters: Dict[str, Any], active: bool | None = None) -> None:
    conn = get_connection()
    cur = conn.cursor()
    if active is None:
        cur.execute(
            "UPDATE executors SET name = ?, daily_limit = ?, parameters = ? WHERE id = ?",
            (name, int(daily_limit), json.dumps(parameters or {}), eid),
        )
    else:
        cur.execute(
            "UPDATE executors SET name = ?, daily_limit = ?, parameters = ?, active = ? WHERE id = ?",
            (name, int(daily_limit), json.dumps(parameters or {}), 1 if active else 0, eid),
        )
    conn.commit()
    conn.close()


def reset_daily_counts() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE executors SET assigned_today = 0")
    conn.commit()
    conn.close()


def increment_assigned_today(eid: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE executors SET assigned_today = assigned_today + 1 WHERE id = ?", (eid,))
    conn.commit()
    conn.close()


def set_executor_active(eid: int, active: bool) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE executors SET active = ? WHERE id = ?", (1 if active else 0, eid))
    conn.commit()
    conn.close()


def ping_executor(eid: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE executors SET last_ping = CURRENT_TIMESTAMP WHERE id = ?", (eid,))
    conn.commit()
    conn.close()


def online_executors_count(minutes: int = 10) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as c FROM executors WHERE active = 1 AND (last_ping IS NULL OR last_ping >= datetime('now', ?))",
        (f"-{int(minutes)} minutes",),
    )
    row = cur.fetchone()
    conn.close()
    return int(row["c"] if row else 0)


# Rules

def get_active_rule_set() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rule_sets WHERE active = 1 ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    try:
        data["rules"] = json.loads(data.get("rules") or "{}")
    except Exception:
        data["rules"] = {}
    return data


def save_rule_set(name: str, rules: Dict[str, Any], active: int = 1) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rule_sets (name, rules, active) VALUES (?, ?, ?)",
        (name, json.dumps(rules or {}), int(active)),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


# Tickets

def create_ticket(data: Dict[str, Any], custom_values: Dict[int, str]) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tickets (client, subject, description, status, amount, executor, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("client", ""),
            data.get("subject", ""),
            data.get("description", ""),
            data.get("status", "processed"),
            float(data.get("amount", 0) or 0),
            data.get("executor", "Не назначен"),
            data.get("created_by"),
        ),
    )
    ticket_id = cur.lastrowid
    for field_id, value in custom_values.items():
        cur.execute(
            "INSERT OR REPLACE INTO ticket_fields (ticket_id, field_id, value) VALUES (?, ?, ?)",
            (ticket_id, field_id, str(value)),
        )
    conn.commit()
    conn.close()
    return ticket_id


def update_ticket(ticket_id: int, data: Dict[str, Any], custom_values: Dict[int, str]) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE tickets
        SET client = ?, subject = ?, description = ?, status = ?, amount = ?, executor = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            data.get("client", ""),
            data.get("subject", ""),
            data.get("description", ""),
            data.get("status", "processed"),
            float(data.get("amount", 0) or 0),
            data.get("executor", "Не назначен"),
            ticket_id,
        ),
    )
    for field_id, value in custom_values.items():
        cur.execute(
            "INSERT OR REPLACE INTO ticket_fields (ticket_id, field_id, value) VALUES (?, ?, ?)",
            (ticket_id, field_id, str(value)),
        )
    conn.commit()
    conn.close()


def delete_ticket(ticket_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ticket_fields WHERE ticket_id = ?", (ticket_id,))
    cur.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()


def list_tickets(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    filters = filters or {}
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM tickets WHERE 1=1"
    params: List[Any] = []

    status = filters.get("status")
    if status and status != "Все":
        query += " AND status = ?"
        params.append(status)

    executor = filters.get("executor")
    if executor and executor != "Все":
        query += " AND executor = ?"
        params.append(executor)

    min_sum = filters.get("min_sum")
    if min_sum is not None and str(min_sum) != "":
        query += " AND amount >= ?"
        params.append(float(min_sum))

    max_sum = filters.get("max_sum")
    if max_sum is not None and str(max_sum) != "":
        query += " AND amount <= ?"
        params.append(float(max_sum))

    query += " ORDER BY id DESC"

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]

    # Attach custom field values per ticket
    if rows:
        ids = [r["id"] for r in rows]
        placeholders = ",".join(["?"] * len(ids))
        cur.execute(
            f"""
            SELECT tf.ticket_id, cf.name, tf.value
            FROM ticket_fields tf
            JOIN custom_fields cf ON cf.id = tf.field_id
            WHERE tf.ticket_id IN ({placeholders})
            """,
            ids,
        )
        by_ticket: Dict[int, Dict[str, str]] = {}
        for r in cur.fetchall():
            t_id = r["ticket_id"]
            by_ticket.setdefault(t_id, {})[r["name"]] = r["value"]
        for row in rows:
            row.update(by_ticket.get(row["id"], {}))

    conn.close()
    return rows


def get_ticket(ticket_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    ticket = dict(row)
    cur.execute(
        """
        SELECT cf.id as field_id, cf.name, cf.type, tf.value
        FROM custom_fields cf
        LEFT JOIN ticket_fields tf ON tf.field_id = cf.id AND tf.ticket_id = ?
        ORDER BY cf.id
        """,
        (ticket_id,),
    )
    ticket["custom_fields"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return ticket


# Metrics helpers

def executor_stats() -> Tuple[List[Dict[str, Any]], float | None]:
    execs = list_executors()
    if not execs:
        return [], None
    utilizations = []
    for e in execs:
        dl = max(1, int(e.get("daily_limit", 1) or 1))
        util = (int(e.get("assigned_today", 0) or 0)) / dl
        utilizations.append(util)
    avg = sum(utilizations) / len(utilizations) if utilizations else 0
    mae = sum(abs(u - avg) for u in utilizations) / len(utilizations) if utilizations else None
    return execs, mae


def total_tickets_count() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tickets")
    row = cur.fetchone()
    conn.close()
    return int(row["c"] if row else 0)


def tickets_count_today() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tickets WHERE DATE(created_at) = DATE('now')")
    row = cur.fetchone()
    conn.close()
    return int(row["c"] if row else 0)


def tickets_count_yesterday() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tickets WHERE DATE(created_at) = DATE('now','-1 day')")
    row = cur.fetchone()
    conn.close()
    return int(row["c"] if row else 0)


def tickets_count_last_days(days: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tickets WHERE created_at >= datetime('now', ?)", (f"-{int(days)} days",))
    row = cur.fetchone()
    conn.close()
    return int(row["c"] if row else 0)


def tickets_count_between_days(start_days_ago: int, end_days_ago: int) -> int:
    # start_days_ago > end_days_ago; e.g., (14, 7) gives previous 7-day window
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) as c FROM tickets
        WHERE created_at >= datetime('now', ?) AND created_at < datetime('now', ?)
        """,
        (f"-{int(start_days_ago)} days", f"-{int(end_days_ago)} days"),
    )
    row = cur.fetchone()
    conn.close()
    return int(row["c"] if row else 0)


def tickets_count_last_minutes(minutes: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tickets WHERE created_at >= datetime('now', ?)", (f"-{int(minutes)} minutes",))
    row = cur.fetchone()
    conn.close()
    return int(row["c"] if row else 0)


def amount_sum_last_days(days: int) -> float:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) as s FROM tickets WHERE created_at >= datetime('now', ?)", (f"-{int(days)} days",))
    row = cur.fetchone()
    conn.close()
    try:
        return float(row["s"]) if row else 0.0
    except Exception:
        return 0.0


def daily_counts(days: int = 14) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DATE(created_at) as d, status, COUNT(*) as c
        FROM tickets
        WHERE created_at >= datetime('now', ?)
        GROUP BY DATE(created_at), status
        ORDER BY d ASC
        """,
        (f"-{int(days)} days",),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def hourly_counts(hours: int = 24) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT strftime('%Y-%m-%d %H:00:00', created_at) as h, COUNT(*) as c
        FROM tickets
        WHERE created_at >= datetime('now', ?)
        GROUP BY h
        ORDER BY h ASC
        """,
        (f"-{int(hours)} hours",),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def minute_counts(minutes: int = 60) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT strftime('%Y-%m-%d %H:%M:00', created_at) as m, COUNT(*) as c
        FROM tickets
        WHERE created_at >= datetime('now', ?)
        GROUP BY m
        ORDER BY m ASC
        """,
        (f"-{int(minutes)} minutes",),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def online_executors_list(minutes: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM executors WHERE active = 1 AND (last_ping IS NULL OR last_ping >= datetime('now', ?)) ORDER BY name",
        (f"-{int(minutes)} minutes",),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _build_ticket_filters(filters: Optional[Dict[str, Any]]):
    filters = filters or {}
    query = "WHERE 1=1"
    params: List[Any] = []
    status = filters.get("status")
    if status and status != "Все":
        query += " AND status = ?"
        params.append(status)
    executor = filters.get("executor")
    if executor and executor != "Все":
        query += " AND executor = ?"
        params.append(executor)
    min_sum = filters.get("min_sum")
    if min_sum is not None and str(min_sum) != "":
        query += " AND amount >= ?"
        params.append(float(min_sum))
    max_sum = filters.get("max_sum")
    if max_sum is not None and str(max_sum) != "":
        query += " AND amount <= ?"
        params.append(float(max_sum))
    return query, params


def count_tickets(filters: Optional[Dict[str, Any]] = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    where_sql, params = _build_ticket_filters(filters)
    cur.execute(f"SELECT COUNT(*) as c FROM tickets {where_sql}", params)
    row = cur.fetchone()
    conn.close()
    return int(row["c"] if row else 0)


def list_tickets_paged(filters: Optional[Dict[str, Any]], limit: int, offset: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    where_sql, params = _build_ticket_filters(filters)
    cur.execute(
        f"SELECT * FROM tickets {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [int(limit), int(offset)],
    )
    rows = [dict(r) for r in cur.fetchall()]

    # Attach custom field values per ticket
    if rows:
        ids = [r["id"] for r in rows]
        placeholders = ",".join(["?"] * len(ids))
        cur.execute(
            f"""
            SELECT tf.ticket_id, cf.name, tf.value
            FROM ticket_fields tf
            JOIN custom_fields cf ON cf.id = tf.field_id
            WHERE tf.ticket_id IN ({placeholders})
            """,
            ids,
        )
        by_ticket: Dict[int, Dict[str, str]] = {}
        for r in cur.fetchall():
            t_id = r["ticket_id"]
            by_ticket.setdefault(t_id, {})[r["name"]] = r["value"]
        for row in rows:
            row.update(by_ticket.get(row["id"], {}))

    conn.close()
    return rows


def clear_all_tickets() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ticket_fields")
    cur.execute("DELETE FROM tickets")
    conn.commit()
    conn.close()


def export_tickets(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    # Export uses unpaged query
    return list_tickets(filters or {})


# Licenses & Settings

PLANS = {
    "starter": {"max_executors": 20},
    "enterprise": {"max_executors": 10000},
}


def generate_license(plan: str) -> Optional[str]:
    if plan not in PLANS:
        return None
    key = secrets.token_urlsafe(24)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO licenses (license_key, plan) VALUES (?, ?)", (key, plan))
    conn.commit()
    conn.close()
    return key


def activate_license(license_key: str, user_id: Optional[int]) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM licenses WHERE license_key = ?", (license_key,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    plan = row["plan"]
    cur.execute("UPDATE settings SET active_plan = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (plan,))
    cur.execute(
        "UPDATE licenses SET activated_by = ?, activated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (user_id, row["id"]),
    )
    conn.commit()
    conn.close()
    return True


def get_active_plan() -> Optional[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT active_plan FROM settings WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return row["active_plan"] if row and row["active_plan"] else None


def get_plan_limits() -> Dict[str, Any]:
    plan = get_active_plan() or "starter"
    return PLANS.get(plan, PLANS["starter"])


def can_add_executor() -> bool:
    limits = get_plan_limits()
    max_exec = limits.get("max_executors", 20)
    return len(list_executors()) < max_exec

# Base fields visibility

BASE_FIELDS = ["client", "subject", "description", "status", "amount", "executor"]


def get_hidden_base_fields() -> List[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT hidden_base_fields FROM settings WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    try:
        return json.loads(row[0]) if row and row[0] else []
    except Exception:
        return []


def set_base_field_hidden(field_name: str, hidden: bool) -> None:
    hidden_list = get_hidden_base_fields()
    if hidden and field_name not in hidden_list:
        hidden_list.append(field_name)
    if not hidden and field_name in hidden_list:
        hidden_list.remove(field_name)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE settings SET hidden_base_fields = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (json.dumps(hidden_list),))
    conn.commit()
    conn.close()


def clear_base_field(field_name: str) -> None:
    if field_name not in BASE_FIELDS:
        return
    conn = get_connection()
    cur = conn.cursor()
    # choose default value by field
    if field_name in ("amount",):
        cur.execute(f"UPDATE tickets SET {field_name} = 0")
    else:
        cur.execute(f"UPDATE tickets SET {field_name} = ''")
    conn.commit()
    conn.close()


# Service status helpers

def record_heartbeat() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO service_status (kind, message) VALUES ('heartbeat', NULL)")
    conn.commit()
    conn.close()


def record_error(message: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO service_status (kind, message) VALUES ('error', ?)", (message,))
    conn.commit()
    conn.close()


def uptime_stats(minutes: int = 60) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as h FROM service_status WHERE kind='heartbeat' AND created_at >= datetime('now', ?)", (f"-{int(minutes)} minutes",))
    hb = cur.fetchone()["h"] if cur.fetchone is not None else 0
    cur.execute("SELECT COUNT(*) as e FROM service_status WHERE kind='error' AND created_at >= datetime('now', ?)", (f"-{int(minutes)} minutes",))
    er = cur.fetchone()["e"] if cur.fetchone is not None else 0
    conn.close()
    return {"heartbeats": int(hb or 0), "errors": int(er or 0)}


# DDoS protection helpers

def set_ddos_block(seconds: int) -> None:
    until = int(time.time()) + max(0, seconds)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE settings SET ddos_block_until = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (until,))
    conn.commit()
    conn.close()


def get_ddos_block_until() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT ddos_block_until FROM settings WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return int(row[0] or 0) if row and row[0] is not None else 0


def is_blocked_now() -> bool:
    return int(time.time()) < get_ddos_block_until()


def requests_per_second(window_seconds: int = 1) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tickets WHERE created_at >= datetime('now', ?)", (f"-{int(window_seconds)} seconds",))
    cnt = cur.fetchone()[0]
    conn.close()
    return int(cnt or 0)
