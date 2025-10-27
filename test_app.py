import flet as ft

ACCENT = ft.Colors.ORANGE


def main(page: ft.Page):
    page.title = "CRM — Система обработки заявок"
    page.theme_mode = "light"
    page.padding = 20
    page.bgcolor = "white"

    #Пример данных
    requests = [
        {"id": 1, "name": "Иван Иванов", "subject": "Проблема с заказом", "status": "новая", "priority": 3},
        {"id": 2, "name": "Мария Петрова", "subject": "Вопрос по доставке", "status": "в работе", "priority": 2},
        {"id": 3, "name": "Олег Сидоров", "subject": "Оплата не прошла", "status": "закрыта", "priority": 1},
    ]

    selected = ft.Ref[ft.Text]()
    reply_input = ft.Ref[ft.TextField]()

    #Статистика
    total = len(requests)
    new_count = sum(r["status"] == "новая" for r in requests)
    in_progress = sum(r["status"] == "в работе" for r in requests)
    closed = sum(r["status"] == "закрыта" for r in requests)

    #Обработчики
    def on_select(e):
        req = e.control.data
        selected.current.value = f"Заявка #{req['id']}: {req['subject']}"
        page.update()

    def refresh_data(e):
        page.snack_bar = ft.SnackBar(ft.Text("Список заявок обновлён!"), bgcolor=ACCENT)
        page.snack_bar.open = True
        page.update()

    #Шапка с логотипом
    header = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SUPPORT_AGENT_ROUNDED, color="white", size=30),
                        ft.Text("CRM Заявки", size=22, weight=ft.FontWeight.BOLD, color="white"),
                    ],
                    spacing=10,
                ),
                ft.ElevatedButton(
                    "Обновить",
                    icon=ft.Icons.REFRESH,
                    bgcolor="white",
                    color=ACCENT,
                    on_click=refresh_data,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=15,
        bgcolor=ACCENT,
        border_radius=10,
    )

    #Панель статистики
    stat_card = lambda title, value, color: ft.Container(
        content=ft.Column(
            [
                ft.Text(title, size=14, color="gray"),
                ft.Text(str(value), size=20, weight=ft.FontWeight.BOLD, color=color),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=15,
        bgcolor="white",
        border_radius=8,
        shadow=ft.BoxShadow(blur_radius=8, color="rgba(0,0,0,0.1)"),
        expand=True,
    )

    stats_row = ft.Row(
        [
            stat_card("Всего заявок", total, ACCENT),
            stat_card("Новые", new_count, "green"),
            stat_card("В работе", in_progress, "orange"),
            stat_card("Закрытые", closed, "gray"),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    #Таблица заявок
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Имя")),
            ft.DataColumn(ft.Text("Тема")),
            ft.DataColumn(ft.Text("Статус")),
            ft.DataColumn(ft.Text("Приоритет")),
        ],
        rows=[
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(r["id"]))),
                    ft.DataCell(ft.Text(r["name"])),
                    ft.DataCell(ft.Text(r["subject"])),
                    ft.DataCell(ft.Text(r["status"])),
                    ft.DataCell(ft.Text(str(r["priority"]))),
                ],
                data=r,
                on_select_changed=on_select,
            )
            for r in requests
        ],
    )

    #Правая панель
    reply_section = ft.Column(
        [
            ft.Text("Детали заявки", size=18, weight=ft.FontWeight.BOLD, color=ACCENT),
            ft.Text(ref=selected, size=16, color="gray"),
            ft.TextField(ref=reply_input, label="Ваш ответ", multiline=True, min_lines=3),
            ft.ElevatedButton(
                "Отправить ответ",
                style=ft.ButtonStyle(
                    bgcolor=ACCENT,
                    color="white",
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=lambda _: page.snack_bar.open(),
            ),
        ],
        spacing=10,
    )

    #Основная раскладка
    layout = ft.Column(
        [
            header,
            ft.Container(content=stats_row, margin=ft.margin.only(top=15, bottom=10)),
            ft.Row(
                [
                    ft.Container(table, expand=2, padding=10),
                    ft.VerticalDivider(),
                    ft.Container(reply_section, expand=1, padding=10),
                ],
                expand=True,
            ),
        ],
        expand=True,
    )

    page.add(layout)


ft.app(target=main)

