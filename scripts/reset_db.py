import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'streamlit_app', 'ais.db')

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"[OK] БД удалена: {DB_PATH}")
else:
    print("[INFO] БД не существует")

