import time
import random
import string
import threading
import statistics
import requests

SITE_URL = "http://127.0.0.1:5050/submit"
THREADS = 20
REQUESTS_PER_THREAD = 50


def random_name(prefix: str) -> str:
    return prefix + "_" + "".join(random.choices(string.ascii_letters + string.digits, k=6))


def worker(results: list[float]):
    session = requests.Session()
    for _ in range(REQUESTS_PER_THREAD):
        payload = {
            "client": random_name("ООО Клиент"),
            "subject": random.choice(["Кредит на развитие", "Рефинансирование", "Овердрафт", "Обслуживание сайта"]),
            "description": random_name("Описание"),
            "amount": str(random.randint(10_000, 1_000_000)),
        }
        t0 = time.perf_counter()
        try:
            resp = session.post(SITE_URL, data=payload, timeout=10)
            resp.raise_for_status()
        except Exception:
            continue
        dt = time.perf_counter() - t0
        results.append(dt)


def main():
    print(f"Starting load test: {THREADS} threads x {REQUESTS_PER_THREAD} requests")
    threads = []
    results: list[float] = []
    t_start = time.perf_counter()
    for _ in range(THREADS):
        t = threading.Thread(target=worker, args=(results,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t_start
    total = len(results)
    rps = total / elapsed if elapsed > 0 else 0
    p50 = statistics.median(results) if results else 0
    p95 = statistics.quantiles(results, n=20)[18] if len(results) >= 20 else (max(results) if results else 0)

    print(f"Completed: {total} requests in {elapsed:.2f}s => {rps:.1f} RPS")
    print(f"Latency p50={p50:.3f}s p95={p95:.3f}s")


if __name__ == "__main__":
    main()
