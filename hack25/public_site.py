from flask import Flask, render_template_string, request, redirect, abort
from app.db import init_db
from app import models
import json

app = Flask(__name__)
init_db()

INDEX = """
<!doctype html>
<title>CreditOrg - Lead Form</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
  body { font-family: Inter, system-ui, Arial; background:#0b1220; color:#e5e7eb; display:flex; align-items:center; justify-content:center; min-height:100vh; }
  .card { background:#111827; padding:24px; border-radius:16px; width:420px; }
  input, textarea { width:100%; padding:10px; margin:8px 0; border-radius:8px; border:1px solid #374151; background:#0b1220; color:#e5e7eb; }
  button { background:#3b82f6; color:white; border:none; padding:10px 14px; border-radius:10px; cursor:pointer; }
  .muted { opacity:.7; font-size:12px; }
  a { color:#93c5fd; }
  h2 { margin-top:0; }
</style>
<div class="card">
  <h2>Кредитная организация — заявка</h2>
  <form method="post" action="/submit">    
    <input name="client" placeholder="Клиент" required>
    <input name="subject" placeholder="Тема" value="Кредит на развитие" required>
    <textarea name="description" placeholder="Описание" rows="3"></textarea>
    <input name="amount" placeholder="Сумма" type="number" step="0.01">
    <button type="submit">Отправить</button>
  </form>
  <p class="muted">Данные попадут сразу в CRM (SQLite). Поля синхронизируются с CRM автоматически.</p>
  <p><a href="/buy">Купить лицензию</a> · <a href="/landing">О нашей CRM</a></p>
</div>
"""

LANDING = """
<!doctype html>
<title>MyCRM — Управляйте заявками красиво</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  :root { --bg:#0b1220; --card:#111827; --txt:#e5e7eb; --acc:#3b82f6; --mut:#94a3b8; }
  *{box-sizing:border-box}
  body{font-family:Inter,system-ui,Arial;background:var(--bg);color:var(--txt);margin:0}
  .hero{padding:60px 20px; text-align:center; background:linear-gradient(180deg, rgba(59,130,246,.15), transparent);} 
  .btn{background:var(--acc); color:white; padding:12px 16px; border-radius:12px; display:inline-block; text-decoration:none}
  .container{max-width:980px;margin:0 auto;padding:20px}
  .grid{display:grid; grid-template-columns: repeat(auto-fit,minmax(240px,1fr)); gap:16px}
  .card{background:var(--card); padding:18px; border-radius:14px}
  canvas{background:#0b1220; border-radius:12px}
  select{background:#0b1220; color:#e5e7eb; border:1px solid #374151; padding:8px; border-radius:8px}
  a{color:#93c5fd}
</style>
<section class="hero">
  <h1 id="logo" style="font-weight:800; font-size:36px; margin:0 0 10px; cursor:pointer">MyCRM</h1>
  <p style="opacity:.9">Современная CRM: тёмная тема, авторизация, гибкие параметры, автораспределение, графики</p>
  <p><a class="btn" href="/buy">Купить лицензию</a></p>
</section>
<div class="container">
  <div class="card" style="margin-top:16px">
    <h3>График активности</h3>
    <div style="display:flex; gap:12px; align-items:center;">
      <label>Период <select id="period"><option value="hour">Час</option><option value="day" selected>День</option><option value="week">Неделя</option></select></label>
      <button id="reload" class="btn">Обновить</button>
    </div>
    <canvas id="chart" height="120"></canvas>
  </div>
  <div id="hidden" class="card" style="margin-top:16px; display:none">
    <h3>Тест нагрузки (скрытый)</h3>
    <label>Всего заявок <input id="cnt" type="number" value="100" style="width:100%"></label>
    <label>Заявок в секунду <input id="rps" type="number" value="20" style="width:100%"></label>
    <label>Тема <input id="subj" type="text" value="Тестовая заявка" style="width:100%"></label>
    <label>Описание <input id="desc" type="text" value="Нагрузка" style="width:100%"></label>
    <label>Ключевые слова (через запятую) <input id="kw" type="text" value="сайт, дизайн" style="width:100%"></label>
    <button id="start" class="btn">Старт</button>
    <div id="status" class="muted"></div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  let chart;
  async function loadData(){
    const period = document.getElementById('period').value;
    const resp = await fetch('/metrics?period='+period);
    const data = await resp.json();
    const labels = data.labels;
    const values = data.values;
    const ctx = document.getElementById('chart').getContext('2d');
    if(chart){ chart.destroy(); }
    chart = new Chart(ctx,{type:'line', data:{labels, datasets:[{label:'Заявок', data:values, borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,.2)', tension:.3}]}, options:{plugins:{legend:{labels:{color:'#e5e7eb'}}}, scales:{x:{ticks:{color:'#94a3b8'}}, y:{ticks:{color:'#94a3b8'}}}}});
  }
  loadData();
  document.getElementById('reload').addEventListener('click', loadData);
  // Hidden tester
  let taps = 0; let last = 0;
  const logo = document.getElementById('logo');
  const hidden = document.getElementById('hidden');
  logo.addEventListener('click', ()=>{ const now = Date.now(); if(now-last>2000){taps=0}; taps++; last=now; if(taps>=5){ hidden.style.display='block'; taps=0; }});
  document.getElementById('start').addEventListener('click', async ()=>{
    const cnt = parseInt(document.getElementById('cnt').value||'100');
    const rps = parseInt(document.getElementById('rps').value||'20');
    const subj = document.getElementById('subj').value||'Тестовая заявка';
    const desc = document.getElementById('desc').value||'Нагрузка';
    const kws = (document.getElementById('kw').value||'').split(',').map(s=>s.trim()).filter(Boolean);
    const status = document.getElementById('status');
    let done = 0;
    function once(){
      const form = new URLSearchParams();
      form.append('client','ООО Клиент_'+Math.random().toString(36).slice(2));
      form.append('subject', subj + (kws.length? (' '+kws[Math.floor(Math.random()*kws.length)]) : ''));
      form.append('description', desc);
      form.append('amount', String(Math.floor(Math.random()*100000)));
      fetch('/submit', {method:'POST', body:form}).finally(()=>{ done++; status.textContent = `Готово: ${done}/${cnt}`; });
    }
    const interval = setInterval(()=>{
      const batch = Math.min(rps, cnt-done);
      for(let i=0;i<batch;i++) once();
      if(done>=cnt) clearInterval(interval);
    }, 1000);
  });
</script>
"""

BUY = """
<!doctype html>
<title>Buy License</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style> body { font-family:Inter,system-ui,Arial; background:#0b1220; color:#e5e7eb; display:flex; align-items:center; justify-content:center; min-height:100vh; } .card { background:#111827; padding:24px; border-radius:16px; width:420px; } select,button{ width:100%; padding:10px; margin:8px 0; border-radius:8px; border:1px solid #374151; background:#0b1220; color:#e5e7eb;} button{background:#10b981;border:none}</style>
<div class="card">
  <h2>Покупка лицензии</h2>
  <form method="post" action="/buy">
    <select name="plan">
      <option value="starter">Starter (до 20 исполнителей)</option>
      <option value="enterprise">Enterprise (без ограничений)</option>
    </select>
    <button type="submit">Получить ключ</button>
  </form>
  {% if key %}
    <p>Ваш ключ: <code>{{key}}</code></p>
  {% endif %}
</div>
"""

BLOCK_PAGE = """
<!doctype html><title>Service temporarily unavailable</title>
<style>body{background:#0b1220;color:#e5e7eb;font-family:Inter,system-ui,Arial;display:flex;align-items:center;justify-content:center;height:100vh} .card{background:#111827;padding:24px;border-radius:16px;width:420px;text-align:center}</style>
<div class=card>
  <h2>Сервис временно приостановлен</h2>
  <p>Мы обнаружили аномальный поток заявок. Приём заявок возобновится через минуту.</p>
</div>
"""


@app.get("/")
def index():
    fields = models.list_custom_fields()
    return render_template_string(INDEX, fields=fields)


@app.get("/landing")
def landing():
    return render_template_string(LANDING)


@app.get("/metrics")
def metrics():
    period = request.args.get('period','day')
    if period == 'hour':
        rows = models.minute_counts(60)
        labels = [r['m'] for r in rows]
        values = [int(r['c']) for r in rows]
    elif period == 'week':
        rows = models.daily_counts(7)
        labels = [r['d'] for r in rows]
        # sum across statuses
        by = {}
        for r in rows:
            by[r['d']] = by.get(r['d'],0)+int(r['c'])
        labels = sorted(by.keys())
        values = [by[d] for d in labels]
    else:
        rows = models.hourly_counts(24)
        labels = [r['h'] for r in rows]
        values = [int(r['c']) for r in rows]
    return {"labels": labels, "values": values}


@app.post("/submit")
def submit():
    # DDoS block check
    if models.is_blocked_now():
        return BLOCK_PAGE, 503
    # trigger block if >100 rps
    if models.requests_per_second(1) > 100:
        models.set_ddos_block(60)
        return BLOCK_PAGE, 503
    data = {
        "client": request.form.get("client", ""),
        "subject": request.form.get("subject", ""),
        "description": request.form.get("description", ""),
        "status": "processed",
        "amount": request.form.get("amount", 0),
        "executor": "Не назначен",
        "created_by": None,
    }
    # Auto-assign executor if possible
    combined_text = f"{data['subject']} {data['description']} {data['client']}".lower()
    execs = models.list_executors()
    if not execs:
        try:
            models.create_executor("Автоспециалист", 10, {"keywords": []})
            execs = models.list_executors()
        except Exception:
            execs = []
    best = None
    best_score = -1.0
    for e in execs:
        try:
            params = json.loads(e.get("parameters") or "{}")
        except Exception:
            params = {}
        keywords = [k.lower() for k in (params.get("keywords") or []) if isinstance(k, str)]
        lvl = params.get("level", 1)
        try:
            level = max(1, min(5, int(lvl)))
        except Exception:
            level = 1
        daily_limit = int(e.get("daily_limit", 10) or 10)
        assigned = int(e.get("assigned_today", 0) or 0)
        utilization = assigned / daily_limit if daily_limit > 0 else 1.0
        utilization = min(1.0, max(0.0, utilization))
        if keywords:
            matches = sum(1 for k in keywords if k and k in combined_text)
            kw_score = matches / len(keywords)
        else:
            kw_score = 0.0
        level_score = level / 5.0
        fairness = 1.0 - utilization
        score = 0.5 * fairness + 0.3 * kw_score + 0.2 * level_score
        if score > best_score:
            best_score = score
            best = e
    if best:
        try:
            models.increment_assigned_today(best["id"])  # type: ignore
        except Exception:
            pass
        data["executor"] = best["name"]

    # Collect custom field values (fields prefixed as cf_{id})
    custom_values = {}
    for f in models.list_custom_fields():
        key = f"cf_{f['id']}"
        if key in request.form:
            custom_values[f["id"]] = request.form.get(key, "")
    models.create_ticket(data, custom_values)
    return redirect("/")


@app.get("/buy")
def buy_page():
    return render_template_string(BUY)


@app.post("/buy")
def buy_post():
    plan = request.form.get("plan", "starter")
    key = models.generate_license(plan) or ""
    return render_template_string(BUY, key=key)


def run_server(host: str = "127.0.0.1", port: int = 5050) -> None:
    # Run without reloader so it is thread-friendly
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_server()
