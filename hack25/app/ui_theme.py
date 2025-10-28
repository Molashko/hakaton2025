import flet as ft

PRIMARY = "#1f2937"  # slate-800
PRIMARY_ACCENT = "#3b82f6"  # blue-500
BG = "#0b1220"  # deep dark
CARD = "#111827"  # slate-900
TEXT = "#e5e7eb"  # gray-200
MUTED = "#94a3b8"  # slate-400
SUCCESS = "#10b981"
DANGER = "#ef4444"
WARNING = "#f59e0b"


def apply_dark_theme(page: ft.Page) -> None:
    page.theme_mode = "dark"
    page.bgcolor = BG
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARY_ACCENT,
    )
