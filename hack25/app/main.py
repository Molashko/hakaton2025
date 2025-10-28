import flet as ft
from typing import Optional, Dict, Any, List, Tuple
import json
import threading
import time
import random
import string
import csv
import webbrowser

from app.db import init_db
from app import models
from app.security import hash_password, verify_password
from app.ui_theme import apply_dark_theme, PRIMARY_ACCENT, CARD, TEXT, SUCCESS, DANGER

STATUSES = ["processed"]

DDOS_THRESHOLD_RPS = 40


def _notify(page: ft.Page, text: str, ok: bool = True):
    page.snack_bar = ft.SnackBar(ft.Text(text), bgcolor=(SUCCESS if ok else DANGER))
    page.snack_bar.open = True
    page.update()


def _current_user_id(page: ft.Page) -> Optional[int]:
    user_id = page.client_storage.get("user_id")
    return int(user_id) if user_id else None


def _set_user(page: ft.Page, user_id: Optional[int]) -> None:
    if user_id is None:
        page.client_storage.remove("user_id")
    else:
        page.client_storage.set("user_id", str(user_id))


# Dialog helpers using page.overlay for compatibility across Flet versions

def _open_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    if dialog not in page.overlay:
        page.overlay.append(dialog)
    dialog.open = True
    page.update()


def _close_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    dialog.open = False
    page.update()


def _auth_view(page: ft.Page, on_success):
    email_ref = ft.Ref[ft.TextField]()
    name_ref = ft.Ref[ft.TextField]()
    pass_ref = ft.Ref[ft.TextField]()
    error_ref = ft.Ref[ft.Text]()

    mode_ref = {"mode": "login"}

    def do_login(_):
        err = ""
        email = (email_ref.current.value or "").strip().lower()
        password = pass_ref.current.value or ""
        if not email or not password:
            err = "Введите почту и пароль"
            if error_ref.current: error_ref.current.value = err
            _notify(page, err, ok=False)
            page.update()
            return
        user = models.get_user_by_email(email)
        if not user:
            err = "Аккаунт не найден"
            if error_ref.current: error_ref.current.value = err
            _notify(page, err, ok=False)
            page.update()
            return
        if not verify_password(password, user["password_hash"]):
            err = "Неверный пароль"
            if error_ref.current: error_ref.current.value = err
            _notify(page, err, ok=False)
            page.update()
            return
        if error_ref.current: error_ref.current.value = ""
        _set_user(page, user["id"])
        _notify(page, "Вход выполнен")
        on_success()

    def do_register(_):
        err = ""
        email = (email_ref.current.value or "").strip().lower()
        name = (name_ref.current.value or "").strip()
        password = pass_ref.current.value or ""
        if not email or not name or not password:
            err = "Заполните все поля"
            if error_ref.current: error_ref.current.value = err
            _notify(page, err, ok=False)
            page.update()
            return
        if models.get_user_by_email(email):
            err = "Пользователь уже существует"
            if error_ref.current: error_ref.current.value = err
            _notify(page, err, ok=False)
            page.update()
            return
        uid = models.create_user(email, name, hash_password(password))
        if uid:
            if error_ref.current: error_ref.current.value = ""
            _set_user(page, uid)
            _notify(page, "Регистрация успешна")
            on_success()
        else:
            err = "Ошибка регистрации"
            if error_ref.current: error_ref.current.value = err
            _notify(page, err, ok=False)
            page.update()

    def switch_mode(_):
        mode_ref["mode"] = "register" if mode_ref["mode"] == "login" else "login"
        render()

    def render():
        is_register = mode_ref["mode"] == "register"
        name_field = ft.TextField(ref=name_ref, label="Имя", visible=is_register)
        btn = ft.ElevatedButton(
            "Зарегистрироваться" if is_register else "Войти",
            on_click=do_register if is_register else do_login,
            bgcolor=PRIMARY_ACCENT,
            color=TEXT,
        )
        switch = ft.TextButton(
            "У меня уже есть аккаунт" if is_register else "Создать аккаунт",
            on_click=switch_mode,
        )
        form = ft.Column([
            ft.Text("🚀 MyCRM", size=28, weight=ft.FontWeight.BOLD),
            ft.TextField(ref=email_ref, label="E-mail"),
            name_field,
            ft.TextField(ref=pass_ref, label="Пароль", password=True, can_reveal_password=True),
            ft.Row([btn, switch], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text(ref=error_ref, value="", color=DANGER),
        ], tight=True, spacing=12)
        card = ft.Container(form, bgcolor=CARD, padding=24, border_radius=16)
        page.controls.clear()
        page.add(
            ft.Column([
                ft.Container(height=36),
                ft.Row([card], alignment=ft.MainAxisAlignment.CENTER),
            ], alignment=ft.MainAxisAlignment.START, expand=True)
        )
        page.update()

    render()


def _score_executors_for_subject(subject: str) -> List[Dict[str, Any]]:
    subject_l = (subject or "").lower()
    rows: List[Dict[str, Any]] = []
    for e in models.list_executors():
        try:
            params = json.loads(e.get("parameters") or "{}")
        except Exception:
            params = {}
        keywords = [k.lower() for k in (params.get("keywords") or []) if isinstance(k, str)]
        level_raw = params.get("level", 1)
        try:
            level = int(level_raw)
        except Exception:
            level = 1
        level = max(1, min(5, level))
        daily_limit = int(e.get("daily_limit", 10) or 10)
        assigned = int(e.get("assigned_today", 0) or 0)
        utilization = assigned / daily_limit if daily_limit > 0 else 1.0
        utilization = min(1.0, max(0.0, utilization))
        # keyword score: доля совпавших ключевых слов (если нет ключей — 0)
        if keywords:
            matches = sum(1 for k in keywords if k and k in subject_l)
            kw_score = matches / len(keywords)
        else:
            kw_score = 0.0
        level_score = level / 5.0
        fairness = 1.0 - utilization
        score = 0.5 * fairness + 0.3 * kw_score + 0.2 * level_score
        rows.append({
            "id": e["id"],
            "name": e["name"],
            "fairness": round(fairness, 3),
            "keywords": round(kw_score, 3),
            "level": level,
            "level_score": round(level_score, 3),
            "score": round(score, 3),
            "assigned_today": assigned,
            "daily_limit": daily_limit,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def _auto_assign_executor(subject: str) -> Tuple[str, str]:
    scores = _score_executors_for_subject(subject)
    if not scores:
        return "Не назначен", "Нет исполнителей"
    top = scores[0]
    # update assigned counter
    try:
        models.increment_assigned_today(top["id"])  # type: ignore
    except Exception:
        pass
    details = f"fairness={top['fairness']} kw={top['keywords']} level_score={top['level_score']} => score={top['score']}"
    return top["name"], details


def _score_executors_for_text(text: str) -> List[Dict[str, Any]]:
    text_l = (text or "").lower()
    execs = models.list_executors()
    # вычислим относительную загрузку среди всех
    max_assigned = max((int(e.get("assigned_today", 0) or 0) for e in execs), default=0)
    rows: List[Dict[str, Any]] = []
    for e in execs:
        try:
            params = json.loads(e.get("parameters") or "{}")
        except Exception:
            params = {}
        keywords = [k.lower() for k in (params.get("keywords") or []) if isinstance(k, str)]
        try:
            level = int(params.get("level", 1))
        except Exception:
            level = 1
        level = max(1, min(5, level))
        daily_limit = int(e.get("daily_limit", 10) or 10)
        assigned = int(e.get("assigned_today", 0) or 0)
        # fairness как среднее из двух факторов: по лимиту и по относительной загрузке
        util_limit = assigned / daily_limit if daily_limit > 0 else 1.0
        util_limit = min(1.0, max(0.0, util_limit))
        util_rel = assigned / max(1, max_assigned) if max_assigned > 0 else 0.0
        util_rel = min(1.0, max(0.0, util_rel))
        fairness = 1.0 - (0.5 * util_limit + 0.5 * util_rel)
        fairness = min(1.0, max(0.0, fairness))
        # keyword score: доля совпавших ключевых слов в общем тексте заявки
        if keywords:
            matches = sum(1 for k in keywords if k and k in text_l)
            kw_score = matches / len(keywords)
        else:
            kw_score = 0.0
        level_score = level / 5.0
        score = 0.5 * fairness + 0.3 * kw_score + 0.2 * level_score
        rows.append({
            "id": e["id"],
            "name": e["name"],
            "fairness": round(fairness, 3),
            "keywords": round(kw_score, 3),
            "level": level,
            "level_score": round(level_score, 3),
            "score": round(score, 3),
            "assigned_today": assigned,
            "daily_limit": daily_limit,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def _auto_assign_executor_from_text(text: str) -> Tuple[str, str]:
    # if нет исполнителей — создаём дефолтного, чтобы автоприсвоение всегда срабатывало
    if not models.list_executors():
        try:
            models.create_executor("Автоспециалист", 10, {"keywords": []})
        except Exception:
            pass
    scores = _score_executors_for_text(text)
    if not scores:
        return "Не назначен", "Нет исполнителей"
    top = scores[0]
    try:
        models.increment_assigned_today(top["id"])  # type: ignore
    except Exception:
        pass
    details = f"fairness={top['fairness']} kw={top['keywords']} level_score={top['level_score']} => score={top['score']}"
    return top["name"], details


def _tickets_view(page: ft.Page):
    filter_executor = ft.Ref[ft.Dropdown]()

    page_size_ref = ft.Ref[ft.Dropdown]()
    page_index = {"i": 0}
    total_label = ft.Text("")

    save_dialog = ft.FilePicker()
    page.overlay.append(save_dialog)

    table = ft.DataTable(columns=[
        ft.DataColumn(ft.Text("ID")),
    ])

    selected_id = {"id": None}

    def get_filters():
        return {
            "executor": filter_executor.current.value,
        }

    def refresh():
        table.rows.clear()
        limit = int(page_size_ref.current.value or 50)
        offset = page_index["i"] * limit
        filters = get_filters()
        total = models.count_tickets(filters)
        items = models.list_tickets_paged(filters, limit=limit, offset=offset)
        total_label.value = f"Всего: {total} | Страница: {page_index['i']+1}"
        custom_fields = [f for f in models.list_custom_fields()]
        # columns without status
        vis = get_visible_base_fields()
        cols = [ft.DataColumn(ft.Text("ID"))]
        if vis["client"]: cols.append(ft.DataColumn(ft.Text("Клиент")))
        if vis["subject"]: cols.append(ft.DataColumn(ft.Text("Тема")))
        if vis["executor"]: cols.append(ft.DataColumn(ft.Text("Исполнитель")))
        if vis["amount"]: cols.append(ft.DataColumn(ft.Text("Сумма")))
        table.columns = cols + [ft.DataColumn(ft.Text(f["name"])) for f in custom_fields]
        for o in items:
            def make_handler(oid: int):
                return lambda e: on_select(oid)
            row = [ft.DataCell(ft.Text(str(o["id"]))) ]
            if vis["client"]: row.append(ft.DataCell(ft.Text(o["client"])))
            if vis["subject"]: row.append(ft.DataCell(ft.Text(o["subject"])))
            if vis["executor"]: row.append(ft.DataCell(ft.Text(o["executor"])))
            if vis["amount"]: row.append(ft.DataCell(ft.Text(str(o.get("amount", 0)))))
            row += [ft.DataCell(ft.Text(str(o.get(f["name"], "")))) for f in custom_fields]
            table.rows.append(ft.DataRow(cells=row, data=o, on_select_changed=make_handler(o["id"])) )
        page.update()

    def on_select(oid: int):
        selected_id["id"] = oid
        open_edit_dialog()

    def open_new_dialog(_=None):
        open_edit_dialog(new=True)

    def next_page(_):
        page_index["i"] += 1
        refresh()

    def prev_page(_):
        if page_index["i"] > 0:
            page_index["i"] -= 1
        refresh()

    def apply_my_tickets(_):
        # set executor to current user's name if available
        user = models.get_user(_current_user_id(page)) if _current_user_id(page) else None
        name = user["name"] if user else None
        if filter_executor.current and name:
            filter_executor.current.value = name
            page_index["i"] = 0
            refresh()
        else:
            _notify(page, "Сначала войдите в систему", ok=False)

    def export_csv(_):
        filters = get_filters()
        rows = models.export_tickets(filters)
        headers = list(rows[0].keys()) if rows else ["id","client","subject","executor","amount","status"]
        def on_save_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    with open(e.path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writeheader()
                        for r in rows:
                            writer.writerow({k: r.get(k, "") for k in headers})
                    _notify(page, "Экспорт завершён")
                except Exception:
                    _notify(page, "Ошибка экспорта", ok=False)
        save_dialog.on_result = on_save_result
        save_dialog.save_file(file_name="tickets.csv")

    def export_xlsx(_):
        try:
            import openpyxl  # type: ignore
        except Exception:
            _notify(page, "Установите пакет openpyxl: pip install openpyxl", ok=False)
            return
        filters = get_filters()
        rows = models.export_tickets(filters)
        headers = list(rows[0].keys()) if rows else ["id","client","subject","executor","amount","status"]
        def on_save_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = "Tickets"
                    ws.append(headers)
                    for r in rows:
                        ws.append([r.get(k, "") for k in headers])
                    wb.save(e.path)
                    _notify(page, "Excel экспорт завершён")
                except Exception:
                    _notify(page, "Ошибка сохранения Excel", ok=False)
        save_dialog.on_result = on_save_result
        save_dialog.save_file(file_name="tickets.xlsx")

    def clear_all(_):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтверждение"),
            content=ft.Text("Удалить все заявки безвозвратно?"),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: _close_dialog(page, dlg)),
                ft.ElevatedButton("Удалить", on_click=lambda e: do_clear()),
            ],
        )
        def do_clear():
            models.clear_all_tickets()
            _close_dialog(page, dlg)
            _notify(page, "Все заявки удалены")
            refresh()
        _open_dialog(page, dlg)

    def show_statistics(_=None):
        items = models.list_tickets()
        execs, mae = models.executor_stats()
        counts = {"processed":0, "await":0, "accept":0, "reject":0}
        total_amount = 0.0
        for t in items:
            counts[t["status"]] = counts.get(t["status"], 0) + 1
            total_amount += float(t.get("amount", 0) or 0)
        bars = []
        max_count = max(counts.values()) if counts else 1
        for s in ["processed","await","accept","reject"]:
            height = 220 * (counts.get(s, 0) / max(1, max_count))
            bars.append(ft.Column([
                ft.Container(height=height, width=44, bgcolor=PRIMARY_ACCENT, border_radius=12),
                ft.Text(f"{s}\n{counts.get(s,0)}", size=12, text_align=ft.TextAlign.CENTER),
            ], alignment=ft.MainAxisAlignment.END))
        extra = ft.Text(f"MAE загрузки исполнителей: {round(mae,3) if mae is not None else '—'}")
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Статистика"),
            content=ft.Container(ft.Column([
                ft.Text(f"Всего заявок: {sum(counts.values())}"),
                ft.Text(f"Общая сумма: {int(total_amount)}"),
                extra,
                ft.Container(ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_AROUND), height=280)
            ], spacing=10), width=560),
            actions=[ft.ElevatedButton("Закрыть", on_click=lambda e: _close_dialog(page, dlg))]
        )
        _open_dialog(page, dlg)

    def open_edit_dialog(new: bool = False):
        user_id = _current_user_id(page)
        ticket = {"client": "", "subject": "", "description": "", "status": "processed", "amount": 0, "executor": "Не назначен"}
        custom_fields = models.list_custom_fields()
        custom_values: Dict[int, str] = {}
        if not new and selected_id["id"] is not None:
            existing = models.get_ticket(selected_id["id"]) or {}
            ticket.update({k: existing.get(k, ticket[k]) for k in ticket.keys()})
            for cf in existing.get("custom_fields", []):
                custom_values[cf["field_id"]] = cf.get("value") or ""

        client_ref = ft.Ref[ft.TextField]()
        subject_ref = ft.Ref[ft.TextField]()
        desc_ref = ft.Ref[ft.TextField]()
        amount_ref = ft.Ref[ft.TextField]()
        exec_ref = ft.Ref[ft.TextField]()
        dynamic_refs: Dict[int, ft.Ref] = {}

        def save(_):
            data = {
                "client": client_ref.current.value or "",
                "subject": subject_ref.current.value or "",
                "description": desc_ref.current.value or "",
                "status": "processed",
                "amount": amount_ref.current.value or 0,
                "executor": exec_ref.current.value or "Не назначен",
                "created_by": user_id,
            }
            # required validation
            missing = []
            for cf in custom_fields:
                if int(cf.get("required", 0)) == 1:
                    ref = dynamic_refs.get(cf["id"])  # type: ignore
                    val = ref.current.value if ref and ref.current else ""
                    if val is None or str(val).strip() == "":
                        missing.append(cf["name"])
            if missing:
                _notify(page, "Заполните обязательные поля: " + ", ".join(missing), ok=False)
                return
            values = {fid: (dynamic_refs[fid].current.value if dynamic_refs[fid].current else "") for fid in dynamic_refs}
            if new:
                if not data["executor"] or data["executor"] == "Не назначен":
                    combined_text = f"{data['subject']} {data['description']} {data['client']} " + " ".join(str(v) for v in values.values())
                    # hint if no executors existed
                    had_exec = bool(models.list_executors())
                    chosen, reason = _auto_assign_executor_from_text(combined_text)  # type: ignore
                    if not had_exec:
                        _notify(page, "Исполнитель создан автоматически")
                    data["executor"] = chosen or "Не назначен"
                    _notify(page, f"Назначен исполнитель: {chosen} ({reason})")
                models.create_ticket(data, values)
                _notify(page, "Заявка создана")
            else:
                models.update_ticket(selected_id["id"], data, values)
                _notify(page, "Изменения сохранены")
            _close_dialog(page, dlg)
            refresh()

        def preview_assignment(_):
            combined_text = f"{(subject_ref.current.value or '')} {(desc_ref.current.value or '')} {(client_ref.current.value or '')}"
            rows = _score_executors_for_text(combined_text)
            if not rows:
                _notify(page, "Нет доступных исполнителей", ok=False)
                return
            header = ft.Row([
                ft.Text("Исполнитель", width=160), ft.Text("fairness", width=80), ft.Text("kw", width=60), ft.Text("level", width=60), ft.Text("score", width=80)
            ])
            lines = [header]
            for r in rows[:15]:
                lines.append(ft.Row([
                    ft.Text(r["name"], width=160),
                    ft.Text(str(r["fairness"]), width=80),
                    ft.Text(str(r["keywords"]), width=60),
                    ft.Text(str(r["level"]), width=60),
                    ft.Text(str(r["score"]), width=80),
                ]))
            dlg2 = ft.AlertDialog(title=ft.Text("Прозрачность распределения"), content=ft.Container(ft.Column(lines, spacing=6), width=520), actions=[ft.TextButton("Закрыть", on_click=lambda e: _close_dialog(page, dlg2))])
            _open_dialog(page, dlg2)

        # add preview button to actions
        vis = get_visible_base_fields()
        form_controls = []
        if vis["client"]: form_controls.append(ft.TextField(ref=client_ref, label="Клиент", value=ticket["client"], expand=1))
        if vis["subject"]: form_controls.append(ft.TextField(ref=subject_ref, label="Тема", value=ticket["subject"], expand=1))
        if vis["description"]: form_controls.append(ft.TextField(ref=desc_ref, label="Описание", multiline=True, min_lines=3, value=ticket["description"], expand=1))
        if vis["amount"]: form_controls.append(ft.TextField(ref=amount_ref, label="Сумма", value=str(ticket["amount"]), expand=1))
        if vis["executor"]: form_controls.append(ft.TextField(ref=exec_ref, label="Исполнитель", value=ticket["executor"], expand=1))

        for cf in custom_fields:
            r = ft.Ref[ft.TextField]()
            dynamic_refs[cf["id"]] = r
            form_controls.append(ft.TextField(ref=r, label=cf["name"], value=custom_values.get(cf["id"], ""), expand=1))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Новая заявка" if new else f"Заявка #{selected_id['id']}"),
            content=ft.Container(ft.Column(form_controls, spacing=10, expand=True)),
            actions=[
                ft.TextButton("Предпросмотр назначения", on_click=preview_assignment),
                ft.TextButton("Отмена", on_click=lambda e: _close_dialog(page, dlg)),
                ft.ElevatedButton("Сохранить", on_click=save),
            ],
        )

        _open_dialog(page, dlg)

    def add_field(_):
        name_ref = ft.Ref[ft.TextField]()
        type_ref = ft.Ref[ft.Dropdown]()
        req_ref = ft.Ref[ft.Checkbox]()
        d = ft.AlertDialog(
            modal=True,
            title=ft.Text("Новый параметр"),
            content=ft.Column([
                ft.TextField(ref=name_ref, label="Название параметра", expand=1),
                ft.Dropdown(ref=type_ref, label="Тип", options=[
                    ft.dropdown.Option("text", "Текст"),
                    ft.dropdown.Option("number", "Число"),
                    ft.dropdown.Option("date", "Дата"),
                    ft.dropdown.Option("choice", "Выбор"),
                ], value="text"),
                ft.Checkbox(ref=req_ref, label="Обязательное поле", value=False),
            ], spacing=10, expand=True),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: _close_dialog(page, d)),
                ft.ElevatedButton("Добавить", on_click=lambda e: submit()),
            ],
        )

        def submit():
            name = (name_ref.current.value or "").strip()
            type_ = (type_ref.current.value or "text").strip()
            required = bool(req_ref.current.value) if req_ref.current else False
            if name:
                models.add_custom_field(name, type_, required)
                _notify(page, "Параметр добавлен")
            _close_dialog(page, d)
            refresh()
        _open_dialog(page, d)

    def get_visible_base_fields():
        hidden = set(models.get_hidden_base_fields())
        return {
            "client": "client" not in hidden,
            "subject": "subject" not in hidden,
            "description": "description" not in hidden,
            "status": "status" not in hidden,
            "amount": "amount" not in hidden,
            "executor": "executor" not in hidden,
        }

    def manage_fields(_):
        dlg = ft.AlertDialog(modal=True)

        def render_body():
            elems: list[ft.Control] = []
            # base fields toggles
            vis = get_visible_base_fields()
            base_rows = []
            for key, title in [("client","Клиент"),("subject","Тема"),("description","Описание"),("amount","Сумма"),("executor","Исполнитель")]:
                chk = ft.Checkbox(label=f"Показывать: {title}", value=vis[key])
                def make_toggle_base(k: str, c: ft.Checkbox):
                    def handler(e):
                        models.set_base_field_hidden(k, not bool(c.value))
                        _notify(page, "Отображение обновлено")
                        render_body()
                    return handler
                chk.on_change = make_toggle_base(key, chk)
                del_btn = ft.TextButton("Очистить и скрыть", on_click=lambda e, k=key: do_clear_base(k))
                base_rows.append(ft.Row([chk, del_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            elems.append(ft.Column([ft.Text("Базовые поля", weight=ft.FontWeight.BOLD)] + base_rows, spacing=6))

            # create parameter form
            name_ref = ft.Ref[ft.TextField]()
            type_ref = ft.Ref[ft.Dropdown]()
            req_ref = ft.Ref[ft.Checkbox]()
            create_form = ft.Column([
                ft.Text("Создать параметр", weight=ft.FontWeight.BOLD),
                ft.TextField(ref=name_ref, label="Название параметра"),
                ft.Dropdown(ref=type_ref, label="Тип", value="text", options=[
                    ft.dropdown.Option("text", "Текст"),
                    ft.dropdown.Option("number", "Число"),
                    ft.dropdown.Option("date", "Дата"),
                    ft.dropdown.Option("choice", "Выбор"),
                ]),
                ft.Checkbox(ref=req_ref, label="Обязательное поле", value=False),
                ft.ElevatedButton("Добавить", on_click=lambda e: do_create(name_ref, type_ref, req_ref))
            ], spacing=8)
            elems.append(create_form)

            # dynamic fields list
            rows: list[ft.Control] = []
            for f in models.list_custom_fields():
                fid = f["id"]
                chk = ft.Checkbox(value=bool(f.get("required", 0)))
                def make_toggle(field_id: int, checkbox: ft.Checkbox):
                    def handler(e):
                        models.set_field_required(field_id, bool(checkbox.value))
                        _notify(page, "Обязательность обновлена")
                    return handler
                chk.on_change = make_toggle(fid, chk)
                del_btn = ft.TextButton("Удалить", on_click=lambda e, field_id=fid: do_delete(field_id))
                rows.append(ft.Row([ft.Text(f"{f['name']} ({f['type']})"), ft.Text("обяз.") , chk, del_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            elems.append(ft.Column([ft.Text("Пользовательские поля", weight=ft.FontWeight.BOLD)] + rows, spacing=6))

            dlg.title = ft.Text("Параметры")
            dlg.content = ft.Container(ft.Column(elems, spacing=12), width=560)
            dlg.actions = [ft.TextButton("Закрыть", on_click=lambda e: _close_dialog(page, dlg))]
            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            page.update()

        def do_clear_base(k: str):
            confirm = ft.AlertDialog(
                modal=True,
                title=ft.Text("Подтверждение"),
                content=ft.Text(f"Очистить данные поля '{k}' во всех заявках и скрыть его?"),
                actions=[
                    ft.TextButton("Отмена", on_click=lambda e: _close_dialog(page, confirm)),
                    ft.ElevatedButton("Очистить", on_click=lambda e: apply_clear())
                ]
            )
            def apply_clear():
                models.clear_base_field(k)
                models.set_base_field_hidden(k, True)
                _close_dialog(page, confirm)
                _notify(page, "Поле очищено и скрыто")
                render_body()
            _open_dialog(page, confirm)

        def do_create(name_ref: ft.Ref, type_ref: ft.Ref, req_ref: ft.Ref):
            name = (name_ref.current.value or "").strip() if name_ref.current else ""
            typ = type_ref.current.value if type_ref.current else "text"
            required = bool(req_ref.current.value) if req_ref.current else False
            if not name:
                _notify(page, "Введите название параметра", ok=False)
                return
            models.add_custom_field(name, typ, required)
            _notify(page, "Параметр добавлен")
            render_body()

        def do_delete(field_id: int):
            models.delete_custom_field(field_id)
            _notify(page, "Параметр удалён")
            render_body()

        render_body()

    # controls
    header = ft.Row([
        ft.Text("Заявки", size=20, weight=ft.FontWeight.BOLD),
        ft.Container(expand=True),
        ft.TextButton("Обновить", on_click=lambda e: refresh()),
        ft.TextButton("Параметры", on_click=manage_fields),
        ft.TextButton("Экспорт CSV", on_click=export_csv),
        ft.TextButton("Очистить", on_click=clear_all),
    ])

    # executor options from executors list + "Все"
    exec_names = [e.get("name","") for e in models.list_executors()]
    exec_options = [ft.dropdown.Option("Все")] + [ft.dropdown.Option(n) for n in exec_names]

    filters = ft.Row([
        ft.Dropdown(ref=filter_executor, label="Исполнитель", value="Все", options=exec_options, on_change=lambda e: (page_index.update({"i":0}), refresh())),
        ft.Dropdown(ref=page_size_ref, label="На странице", value="50", options=[ft.dropdown.Option(v) for v in ["25","50","100","200"]], on_change=lambda e: (page_index.update({"i":0}), refresh())),
        total_label,
        ft.TextButton("Мои заявки", on_click=apply_my_tickets),
        ft.TextButton("<", on_click=prev_page),
        ft.TextButton(">", on_click=next_page),
    ], spacing=10)

    content = ft.Container(ft.Column([
        header,
        filters,
        ft.Divider(),
        ft.Container(table, expand=True, padding=10, bgcolor=CARD, border_radius=12),
    ], expand=True), expand=True)

    return content, refresh


def _account_view(page: ft.Page):
    plan = models.get_active_plan() or "starter"
    limits = models.get_plan_limits()
    key_ref = ft.Ref[ft.TextField]()
    
    user = models.get_user(_current_user_id(page)) if _current_user_id(page) else None
    name_ref = ft.Ref[ft.TextField]()
    pass1_ref = ft.Ref[ft.TextField]()
    pass2_ref = ft.Ref[ft.TextField]()
    lic_msg_ref = ft.Ref[ft.Text]()

    def save_profile(_):
        new_name = (name_ref.current.value or (user["name"] if user else "")).strip()
        if user and new_name:
            models.update_user_name(user["id"], new_name)
            _notify(page, "Имя обновлено")

    def change_pass(_):
        p1 = pass1_ref.current.value or ""
        p2 = pass2_ref.current.value or ""
        if not p1 or p1 != p2:
            _notify(page, "Пароли не совпадают", ok=False)
            return
        if user:
            models.update_user_password(user["id"], hash_password(p1))
            _notify(page, "Пароль обновлён")

    def activate(_):
        key = (key_ref.current.value or "").strip()
        if not key:
            if lic_msg_ref.current: lic_msg_ref.current.value = "Введите ключ"
            _notify(page, "Введите ключ", ok=False)
            page.update()
            return
        ok = models.activate_license(key, _current_user_id(page))
        if ok:
            if lic_msg_ref.current: lic_msg_ref.current.value = "Лицензия активирована"
            _notify(page, "Лицензия активирована")
        else:
            if lic_msg_ref.current: lic_msg_ref.current.value = "Неверный ключ"
            _notify(page, "Неверный ключ", ok=False)
        page.update()

    def buy(_):
        try:
            webbrowser.open("http://127.0.0.1:5050/buy")
        except Exception:
            pass

    profile = ft.Container(ft.Column([
        ft.Text("Профиль", size=18, weight=ft.FontWeight.BOLD),
        ft.TextField(ref=name_ref, label="Имя", value=user["name"] if user else "", expand=1),
        ft.Row([ft.ElevatedButton("Сохранить", on_click=save_profile)], alignment=ft.MainAxisAlignment.START),
        ft.Text("Смена пароля", size=18, weight=ft.FontWeight.BOLD),
        ft.TextField(ref=pass1_ref, label="Новый пароль", password=True, can_reveal_password=True),
        ft.TextField(ref=pass2_ref, label="Повтор пароля", password=True, can_reveal_password=True),
        ft.Row([ft.ElevatedButton("Обновить пароль", on_click=change_pass)], alignment=ft.MainAxisAlignment.START),
    ], spacing=10), bgcolor=CARD, padding=18, border_radius=12)

    license_card = ft.Container(ft.Column([
        ft.Text("Подписка", size=18, weight=ft.FontWeight.BOLD),
        ft.Text(f"Текущий план: {plan} (лимит исполнителей: {limits.get('max_executors')})"),
        ft.Row([
            ft.TextField(ref=key_ref, label="Лицензионный ключ", expand=1),
            ft.ElevatedButton("Активировать", on_click=activate),
            ft.TextButton("Купить лицензию", on_click=buy),
        ]),
        ft.Text(ref=lic_msg_ref, value="", color=DANGER),
    ], spacing=10), bgcolor=CARD, padding=18, border_radius=12)

    return ft.Column([ft.Text("Аккаунт", size=20, weight=ft.FontWeight.BOLD), profile, license_card], spacing=12, expand=True)


def _executors_view(page: ft.Page):
    table = ft.DataTable(columns=[
        ft.DataColumn(ft.Text("ID")),
        ft.DataColumn(ft.Text("Имя")),
        ft.DataColumn(ft.Text("Уровень")),
        ft.DataColumn(ft.Text("Лимит/день")),
        ft.DataColumn(ft.Text("Назначено сегодня")),
        ft.DataColumn(ft.Text("Ключевые слова")),
        ft.DataColumn(ft.Text("Активен")),
    ])

    def refresh():
        table.rows.clear()
        for e in models.list_executors():
            try:
                params = json.loads(e.get("parameters") or "{}")
            except Exception:
                params = {}
            keywords = ", ".join(params.get("keywords", []))
            level = str(params.get("level", 1))
            active = "Да" if (e.get("active", 1) in (1, True)) else "Нет"
            row = [
                ft.DataCell(ft.Text(str(e["id"]))),
                ft.DataCell(ft.Text(e["name"])),
                ft.DataCell(ft.Text(level)),
                ft.DataCell(ft.Text(str(e["daily_limit"]))),
                ft.DataCell(ft.Text(str(e.get("assigned_today", 0)))),
                ft.DataCell(ft.Text(keywords)),
                ft.DataCell(ft.Text(active)),
            ]
            table.rows.append(ft.DataRow(cells=row, data=e, on_select_changed=lambda ev, ed=e: on_select(ed)))
        page.update()

    def on_select(executor: Dict[str, Any]):
        name_ref = ft.Ref[ft.TextField]()
        level_ref = ft.Ref[ft.TextField]()
        limit_ref = ft.Ref[ft.TextField]()
        keywords_ref = ft.Ref[ft.TextField]()
        active_ref = ft.Ref[ft.Checkbox]()
        cur_params = {}
        try:
            cur_params = json.loads(executor.get("parameters") or "{}")
        except Exception:
            cur_params = {}
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Исполнитель #{executor['id']}"),
            content=ft.Column([
                ft.TextField(ref=name_ref, label="Имя", value=executor["name"], expand=1),
                ft.TextField(ref=level_ref, label="Уровень (1-5)", value=str(cur_params.get("level", 1)), expand=1),
                ft.TextField(ref=limit_ref, label="Лимит/день", value=str(executor["daily_limit"]), expand=1),
                ft.TextField(ref=keywords_ref, label="Ключевые слова, через запятую", value=", ".join(cur_params.get("keywords", [])), expand=1),
                ft.Checkbox(ref=active_ref, label="Активен", value=(executor.get("active", 1) in (1, True))),
            ], spacing=10, expand=True),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: _close_dialog(page, dlg)),
                ft.ElevatedButton("Сохранить", on_click=lambda e: submit()),
            ],
        )
        def submit():
            name = (name_ref.current.value or executor["name"]).strip()
            try:
                level = max(1, min(5, int(level_ref.current.value or cur_params.get("level", 1))))
            except Exception:
                level = cur_params.get("level", 1)
            try:
                limit = int(limit_ref.current.value or executor["daily_limit"])
            except Exception:
                limit = executor["daily_limit"]
            keywords = [s.strip() for s in (keywords_ref.current.value or "").split(",") if s.strip()]
            params = {"keywords": keywords, "level": level}
            models.update_executor(executor["id"], name, limit, params, active=bool(active_ref.current.value))
            _close_dialog(page, dlg)
            _notify(page, "Исполнитель обновлён")
            refresh()
        _open_dialog(page, dlg)

    def add_executor(_):
        if not models.can_add_executor():
            _notify(page, "Превышен лимит по плану. Активируйте Enterprise.", ok=False)
            return
        name_ref = ft.Ref[ft.TextField]()
        level_ref = ft.Ref[ft.TextField]()
        limit_ref = ft.Ref[ft.TextField]()
        keywords_ref = ft.Ref[ft.TextField]()
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Новый исполнитель"),
            content=ft.Column([
                ft.TextField(ref=name_ref, label="Имя", expand=1),
                ft.TextField(ref=level_ref, label="Уровень (1-5)", value="1", expand=1),
                ft.TextField(ref=limit_ref, label="Лимит/день", value="10", expand=1),
                ft.TextField(ref=keywords_ref, label="Ключевые слова, через запятую", expand=1),
            ], spacing=10, expand=True),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: _close_dialog(page, dlg)),
                ft.ElevatedButton("Добавить", on_click=lambda e: submit()),
            ],
        )
        def submit():
            name = (name_ref.current.value or "").strip()
            try:
                level = max(1, min(5, int(level_ref.current.value or 1)))
            except Exception:
                level = 1
            try:
                limit = int(limit_ref.current.value or 10)
            except Exception:
                limit = 10
            keywords = [s.strip() for s in (keywords_ref.current.value or "").split(",") if s.strip()]
            params = {"keywords": keywords, "level": level}
            if name:
                models.create_executor(name, limit, params)
                _notify(page, "Исполнитель добавлен")
            _close_dialog(page, dlg)
            refresh()
        _open_dialog(page, dlg)

    header = ft.Row([
        ft.Text("Исполнители", size=20, weight=ft.FontWeight.BOLD),
        ft.Container(expand=True),
        ft.ElevatedButton("Новый исполнитель", on_click=add_executor),
        ft.ElevatedButton("Сбросить счётчики", on_click=lambda e: (models.reset_daily_counts(), refresh())),
    ])

    content = ft.Container(ft.Column([
        header,
        ft.Divider(),
        ft.Container(table, expand=True, padding=10, bgcolor=CARD, border_radius=12),
    ], expand=True), expand=True)

    return content, refresh


def _kpi_tile(title: str, value: str, delta: str | None = None, positive: bool | None = None):
    delta_text = ft.Text(delta or "", size=12, color=(SUCCESS if positive else DANGER) if delta else None)
    return ft.Container(
        ft.Column([
            ft.Text(title, size=12, color="#94a3b8"),
            ft.Text(value, size=28, weight=ft.FontWeight.BOLD),
            delta_text,
        ], spacing=4),
        bgcolor=CARD, padding=18, border_radius=12
    )


def _sparkline(values: list[float], width: int = 220, height: int = 60, color: str = PRIMARY_ACCENT):
    if not values:
        return ft.Container(width=width, height=height)
    maxv = max(values) or 1
    bars = []
    for v in values:
        h = max(2, int((v / maxv) * (height - 4)))
        bars.append(ft.Container(width=6, height=h, bgcolor=color, border_radius=4))
    row = ft.Row(bars, spacing=2, vertical_alignment=ft.CrossAxisAlignment.END)
    return ft.Container(row, width=width, height=height)


def _dashboard_view(page: ft.Page):
    total = models.total_tickets_count()
    today = models.tickets_count_today()
    yesterday = models.tickets_count_yesterday()
    week = models.tickets_count_last_days(7)
    prev_week = models.tickets_count_between_days(14, 7)
    last_60m = models.tickets_count_last_minutes(60)
    online = models.online_executors_count(10)
    execs, mae = models.executor_stats()

    def fmt_delta(current: int, prev: int) -> tuple[str, bool]:
        diff = current - prev
        if prev == 0:
            pct = 100 if current > 0 else 0
        else:
            pct = int((diff / prev) * 100)
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff} ({pct}%)", diff >= 0

    today_delta, today_pos = fmt_delta(today, yesterday)
    week_delta, week_pos = fmt_delta(week, prev_week)

    # inline charts state and content ref
    chart_state = {"show": False, "key": ""}
    content_ref = ft.Ref[ft.Column]()

    # data for sparklines
    dc = models.daily_counts(14)
    by_day_total = {}
    for r in dc:
        by_day_total[r['d']] = by_day_total.get(r['d'], 0) + int(r['c'])
    labels = sorted(by_day_total.keys())
    vals_total = [by_day_total[d] for d in labels]

    up = models.uptime_stats(60)
    stability = 100 if up["heartbeats"]>0 else 0

    # precompute series
    hours24 = models.hourly_counts(24)
    mins60 = models.minute_counts(60)
    execs_list = models.online_executors_list(10)

    def series_from(rows, key):
        lbls = [r[key] for r in rows]
        vals = [int(r['c']) for r in rows]
        return lbls, vals

    labels_h, vals_h = series_from(hours24, 'h') if hours24 else ([], [])
    labels_m, vals_m = series_from(mins60, 'm') if mins60 else ([], [])

    def tile(title: str, value: str, delta: str | None, positive: bool | None, key: str):
        parts = [ft.Text(title, size=12, color="#94a3b8"), ft.Text(value, size=28, weight=ft.FontWeight.BOLD)]
        if delta is not None:
            parts.append(ft.Text(delta, size=12, color=(SUCCESS if positive else DANGER)))
        inner = ft.Container(ft.Column(parts, spacing=4), bgcolor=CARD, padding=18, border_radius=12)
        if key == 'total':
            return inner  # без графика
        card = ft.GestureDetector(content=inner, on_tap=lambda e, k=key: toggle_chart(k))
        if chart_state["show"] and chart_state["key"] == key:
            detail: ft.Control
            if key == 'today':
                detail = _sparkline(vals_h)
            elif key == 'week':
                detail = _sparkline(vals_total[-7:] if len(vals_total)>=7 else vals_total)
            elif key == '60m':
                detail = _sparkline(vals_m)
            elif key == 'online':
                names = ", ".join([e.get('name','') for e in execs_list]) or '—'
                detail = ft.Text(f"Онлайн: {names}")
            else:
                detail = _sparkline(vals_total)
            return ft.Column([card, detail], spacing=6)
        return card

    def render():
        # KPIs
        kpis = ft.ResponsiveRow([
            ft.Container(tile("Стабильность (60м)", f"{stability}%", None, None, "stability"), col={'xs':12,'sm':6,'md':3}),
            ft.Container(tile("Всего заявок", str(total), None, None, "total"), col={'xs':12,'sm':6,'md':3}),
            ft.Container(tile("Сегодня", str(today), today_delta, today_pos, "today"), col={'xs':12,'sm':6,'md':3}),
            ft.Container(tile("За 7 дней", str(week), week_delta, week_pos, "week"), col={'xs':12,'sm':6,'md':3}),
            ft.Container(tile("За 60 мин", str(last_60m), None, None, "60m"), col={'xs':12,'sm':6,'md':3}),
            ft.Container(tile("Онлайн исполнителей", str(online), None, None, "online"), col={'xs':12,'sm':6,'md':3}),
        ], columns=12, spacing=12, run_spacing=12)
        # recent
        recent = models.list_tickets({})[:8]
        recent_items = [ft.Row([ft.Text(f"#{t['id']} {t['client']} — {t['subject']}", weight=ft.FontWeight.W_500), ft.Container(expand=True), ft.Text(t["status"]), ft.Text(str(int(t.get("amount",0) or 0)))]) for t in recent]
        recent_card = ft.Container(ft.Column([ft.Text("Последние заявки", weight=ft.FontWeight.BOLD)] + recent_items, spacing=8), bgcolor=CARD, padding=18, border_radius=12)
        content_ref.current.controls = [ft.Text("Дашборд", size=20, weight=ft.FontWeight.BOLD), kpis, recent_card]
        page.update()

    def toggle_chart(key: str):
        chart_state["show"] = not (chart_state["show"] and chart_state["key"] == key)
        chart_state["key"] = key
        render()

    # initial content
    content = ft.Column(ref=content_ref, expand=True)
    render()
    return content


def _random_string(prefix: str, k: int = 6) -> str:
    return prefix + "_" + "".join(random.choices(string.ascii_letters + string.digits, k=k))


def _open_load_generator(page: ft.Page, user_id: Optional[int], after_create_callback=None):
    total_ref = ft.Ref[ft.TextField]()
    rps_ref = ft.Ref[ft.TextField]()
    subjects_ref = ft.Ref[ft.TextField]()
    running = {"stop": False}
    status_txt = ft.Text("")
    progress = ft.ProgressBar(width=400)

    def run_bg(total: int, rps: int, subjects: list[str]):
        made = 0
        last_tick = time.perf_counter()
        per_interval = max(1, rps)
        while made < total and not running["stop"]:
            start_batch = time.perf_counter()
            for _ in range(min(per_interval, total - made)):
                subject = random.choice(subjects) if subjects else random.choice([
                    "Кредит на развитие", "Рефинансирование", "Овердрафт", "Сайт", "Маркетинг"
                ])
                data = {
                    "client": _random_string("ООО Клиент"),
                    "subject": subject,
                    "description": _random_string("Описание"),
                    "status": "processed",
                    "amount": random.randint(5_000, 2_000_000),
                    "executor": "Не назначен",
                    "created_by": user_id,
                }
                # auto-assign similar to new ticket dialog
                if not data["executor"] or data["executor"] == "Не назначен":
                    combined_text = f"{data['subject']} {data['description']} {data['client']} " + " ".join(str(v) for v in data.values())
                    # hint if no executors existed
                    had_exec = bool(models.list_executors())
                    chosen, reason = _auto_assign_executor_from_text(combined_text)  # type: ignore
                    if not had_exec:
                        _notify(page, "Исполнитель создан автоматически")
                    data["executor"] = chosen or "Не назначен"
                    _notify(page, f"Назначен исполнитель: {chosen} ({reason})")
                try:
                    models.create_ticket(data, {})
                except Exception:
                    pass
                made += 1
                progress.value = made / total
                status_txt.value = f"Создано: {made}/{total}"
                page.update()
                if after_create_callback:
                    try:
                        after_create_callback()
                    except Exception:
                        pass
            # throttle to target rps
            elapsed = time.perf_counter() - start_batch
            sleep_time = max(0.0, 1.0 - elapsed)
            time.sleep(sleep_time)
        status_txt.value = "Готово" if not running["stop"] else "Остановлено"
        page.update()

    def start(_):
        try:
            total = int(total_ref.current.value or 100)
        except Exception:
            total = 100
        try:
            rps = int(rps_ref.current.value or 10)
        except Exception:
            rps = 10
        subjects = [s.strip() for s in (subjects_ref.current.value or "").split(",") if s.strip()]
        running["stop"] = False
        threading.Thread(target=run_bg, args=(total, rps, subjects), daemon=True).start()

    def stop(_):
        running["stop"] = True

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Генератор нагрузки"),
        content=ft.Column([
            ft.Text("Скрытая функция админ-панели"),
            ft.TextField(ref=total_ref, label="Всего заявок", value="200"),
            ft.TextField(ref=rps_ref, label="Заявок в секунду", value="20"),
            ft.TextField(ref=subjects_ref, label="Темы (через запятую)", value="Кредит на развитие, Рефинансирование, Сайт"),
            progress,
            status_txt,
        ], spacing=10, expand=True),
        actions=[
            ft.TextButton("Стоп", on_click=stop),
            ft.ElevatedButton("Старт", on_click=start),
            ft.TextButton("Закрыть", on_click=lambda e: _close_dialog(page, dlg)),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    _open_dialog(page, dlg)


def main(page: ft.Page):
    page.title = "🚀 MyCRM"
    apply_dark_theme(page)
    page.padding = 12
    try:
        page.scroll = ft.ScrollMode.ADAPTIVE
    except Exception:
        pass
    init_db()

    auto = {"run": False}

    # start global heartbeat thread once per app
    hb = {"running": False}
    def start_heartbeat():
        if hb["running"]:
            return
        hb["running"] = True
        def loop():
            while hb["running"]:
                try:
                    models.record_heartbeat()
                except Exception as ex:
                    try:
                        models.record_error(str(ex))
                    except Exception:
                        pass
                time.sleep(15)
        threading.Thread(target=loop, daemon=True).start()
    start_heartbeat()

    def go_app():
        page.controls.clear()
        # App shell
        user_id = _current_user_id(page)
        user = models.get_user(user_id) if user_id else None
        if user_id and not user:
            # invalid stored user id; reset to auth
            _set_user(page, None)
            _auth_view(page, on_success=go_app)
            return
        if user:
            eid = models.ensure_executor_for_user(user["name"])  # create if missing
            models.set_executor_active(eid, True)
            models.ping_executor(eid)

        # Hidden tap counter on logo to open load generator
        tap = {"n": 0, "last": 0.0}
        def on_logo_click(e):
            now = time.perf_counter()
            if now - tap["last"] > 2.0:
                tap["n"] = 0
            tap["n"] += 1
            tap["last"] = now
            if tap["n"] >= 5:
                tap["n"] = 0
                _open_load_generator(page, _current_user_id(page), after_create_callback=lambda: None)

        # DDoS banner
        ddos_banner = ft.Container(ft.Text("Высокая нагрузка: приём заявок приостановлен на 1 минуту", color="white"), bgcolor="#b91c1c", padding=10, border_radius=8, visible=False)

        topbar = ft.Container(
            ft.Row([
                ft.TextButton("🚀 MyCRM", on_click=on_logo_click),
                ft.TextButton("О нас", on_click=lambda e: webbrowser.open("http://127.0.0.1:5050/landing")),
                ft.Container(expand=True),
                ft.Text(user["name"] if user else "", color=TEXT),
                ft.TextButton("Выйти", on_click=lambda e: logout()),
            ]),
            padding=12
        )

        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Дашборд"),
                ft.Tab(text="Заявки"),
                ft.Tab(text="Исполнители"),
                ft.Tab(text="Аккаунт"),
            ],
            expand=1,
        )

        tickets, refresh_tickets = _tickets_view(page)
        executors, refresh_exec = _executors_view(page)
        account = _account_view(page)

        def on_change(_):
            # keep online heartbeat
            if user:
                eid = models.ensure_executor_for_user(user["name"])
                models.ping_executor(eid)
            body.controls.clear()
            if tabs.selected_index == 0:
                body.controls.append(_dashboard_view(page))
            elif tabs.selected_index == 1:
                body.controls.append(tickets)
                refresh_tickets()
            elif tabs.selected_index == 2:
                body.controls.append(executors)
                refresh_exec()
            else:
                # Account
                body.controls.append(_account_view(page))
            page.update()

        tabs.on_change = on_change
        body = ft.Column(expand=True)
        layout = ft.Column([topbar, ddos_banner, tabs, body], expand=True)
        page.add(layout)
        on_change(None)
        page.update()

        # start auto refresh thread for dashboard
        auto["run"] = True
        def auto_refresh_loop():
            while auto["run"]:
                try:
                    # DDoS banner poll
                    ddos_banner.visible = models.is_blocked_now()
                    # local trigger: if many tickets in last second
                    if not ddos_banner.visible and models.requests_per_second(1) > DDOS_THRESHOLD_RPS:
                        models.set_ddos_block(60)
                        ddos_banner.visible = True
                    if tabs.selected_index == 0:
                        body.controls.clear()
                        body.controls.append(_dashboard_view(page))
                        page.update()
                except Exception as ex:
                    models.record_error(str(ex))
                time.sleep(3)
        threading.Thread(target=auto_refresh_loop, daemon=True).start()

    def logout():
        auto["run"] = False
        _set_user(page, None)
        _auth_view(page, on_success=go_app)

    if _current_user_id(page):
        go_app()
    else:
        _auth_view(page, on_success=go_app)
