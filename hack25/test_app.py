import threading
import flet as ft
from app.main import main
from public_site import run_server


def start_public_site():
    t = threading.Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": 5050}, daemon=True)
    t.start()


if __name__ == "__main__":
    start_public_site()
ft.app(target=main)
