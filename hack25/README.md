# MyCRM (Flet)

Modern CRM built with Python and Flet, featuring:
- Dark, modern UI
- User authentication (register/login/logout)
- Full ticket management with custom fields
- Filters and nicer dashboard charts
- SQLite persistence (file: `crm.db`)

## Requirements
- Python 3.9+
- Windows/macOS/Linux

## Setup
```bash
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
pip install --upgrade pip
pip install flet
```

## Run
```bash
python test_app.py
```
The first start will create `crm.db` automatically.

## Project Structure
- `app/` core modules
  - `main.py` entry point for Flet app
  - `db.py` SQLite connection & schema
  - `models.py` data access for users, tickets, custom fields
  - `security.py` password hashing/verification (PBKDF2)
  - `ui_theme.py` dark theme configuration
- `test_app.py` thin launcher calling `app.main.main`

## Notes
- Use the top-right "Выйти" link to logout.
- Create custom parameters via "Добавить параметр" and they will appear as editable fields in tickets.
