"""Рендеринг сводки в HTML (веб) и в текст для Telegram."""
import html

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Утренняя сводка — {generated_at}</title>
<style>
  :root {{
    --bg:#0f1419; --card:#1a2027; --accent:#4f9dff; --text:#e6edf3;
    --muted:#8b949e; --green:#3fb950; --red:#f85149; --line:#2d333b;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,'Segoe UI',Roboto,sans-serif;
    background:var(--bg); color:var(--text); line-height:1.5; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:24px 16px 64px; }}
  header h1 {{ margin:0 0 4px; font-size:26px; }}
  header .sub {{ color:var(--muted); font-size:14px; }}
  .card {{ background:var(--card); border:1px solid var(--line);
    border-radius:14px; padding:18px 20px; margin-top:18px; }}
  .card h2 {{ margin:0 0 12px; font-size:15px; text-transform:uppercase;
    letter-spacing:.06em; color:var(--accent); }}
  .row {{ display:flex; gap:16px; flex-wrap:wrap; }}
  .weather-temp {{ font-size:42px; font-weight:700; }}
  .weather-meta {{ color:var(--muted); font-size:14px; }}
  .rate {{ display:flex; justify-content:space-between; padding:6px 0;
    border-bottom:1px solid var(--line); }}
  .rate:last-child {{ border-bottom:none; }}
  .up {{ color:var(--red); }} .down {{ color:var(--green); }}
  ul {{ margin:0; padding-left:0; list-style:none; }}
  li {{ padding:8px 0; border-bottom:1px solid var(--line); }}
  li:last-child {{ border-bottom:none; }}
  .todo-high {{ border-left:3px solid var(--red); padding-left:10px; }}
  .news a {{ color:var(--text); text-decoration:none; }}
  .news a:hover {{ color:var(--accent); }}
  .src {{ color:var(--muted); font-size:12px; }}
  .rec {{ background:rgba(79,157,255,.08); border-radius:8px;
    padding:8px 12px; margin-bottom:8px; }}
  .err {{ color:var(--red); font-size:13px; }}
  .greeting {{ background:linear-gradient(135deg,#1d2a44,#1a2027);
    border:1px solid #2b3a55; border-radius:14px; padding:20px 22px;
    margin-top:18px; font-size:16px; line-height:1.6; }}
  .greeting .label {{ font-size:12px; text-transform:uppercase;
    letter-spacing:.06em; color:var(--accent); margin-bottom:8px; }}
  .ai-summary {{ font-size:15px; line-height:1.6; color:#cdd6e0; }}
  .pri {{ display:inline-block; font-size:11px; font-weight:600;
    padding:2px 8px; border-radius:6px; margin-right:8px;
    text-transform:uppercase; letter-spacing:.04em; vertical-align:middle; }}
  .pri-high {{ background:rgba(248,81,73,.16); color:#ff8b85; }}
  .pri-medium {{ background:rgba(240,159,39,.16); color:#f0b96b; }}
  .pri-low {{ background:rgba(139,148,158,.16); color:#a9b2bc; }}
  .action {{ color:var(--accent); font-size:13px; }}
  .why {{ color:var(--muted); font-size:12px; font-style:italic; }}
  .badge-ai {{ font-size:10px; background:rgba(79,157,255,.15);
    color:var(--accent); padding:2px 7px; border-radius:6px;
    margin-left:8px; vertical-align:middle; letter-spacing:.03em; }}
</style>
</head>
<body>
<div class="wrap">
  <header style="display:flex; justify-content:space-between; align-items:flex-start;">
    <div>
      <h1>Утренняя сводка</h1>
      <div class="sub">{weekday}, {generated_at}</div>
    </div>
    <a href="/logout" style="color:var(--muted); font-size:13px; text-decoration:none; margin-top:6px;">Выйти</a>
  </header>
  {greeting_html}
  {weather_html}
  {rates_html}
  {todos_html}
  {recs_html}
  {news_html}
  {mail_html}
</div>
</body>
</html>"""


def _esc(s):
    return html.escape(str(s or ""))


def _pri_class(p: str) -> str:
    return {"high": "pri-high", "medium": "pri-medium",
            "low": "pri-low"}.get((p or "").lower(), "pri-low")


def render_html(d: dict) -> str:
    ai = d.get("ai", {}) or {}

    # Утреннее обращение
    if ai.get("greeting"):
        greeting_html = (f"""<div class="greeting">
        <div class="label">Доброе утро<span class="badge-ai">AI</span></div>
        {_esc(ai['greeting'])}</div>""")
    else:
        greeting_html = ""

    w = d["weather"]
    if w.get("ok"):
        weather_html = f"""<div class="card"><h2>Погода — {_esc(w['city'])}</h2>
        <div class="row" style="align-items:center">
          <div class="weather-temp">{w['temp']}°</div>
          <div class="weather-meta">{_esc(w['description'])}<br>
          ощущается как {w['feels_like']}° · ветер {w['wind']} км/ч<br>
          день: {w['t_min']}…{w['t_max']}° · осадки {w['precip_prob']}%</div>
        </div></div>"""
    else:
        weather_html = f"""<div class="card"><h2>Погода</h2>
        <div class="err">Не удалось получить: {_esc(w.get('error'))}</div></div>"""

    r = d["rates"]
    if r.get("ok") and r.get("rates"):
        rows = ""
        for x in r["rates"]:
            arrow = "▲" if x["up"] else "▼"
            cls = "up" if x["up"] else "down"
            rows += (f"<div class='rate'><span>{_esc(x['code'])} "
                     f"({_esc(x['name'])})</span>"
                     f"<span>{x['value']} ₽ "
                     f"<span class='{cls}'>{arrow} {abs(x['delta'])}</span></span></div>")
        rates_html = f"""<div class="card"><h2>Курсы ЦБ РФ · {_esc(r.get('date','')[:10])}</h2>{rows}</div>"""
    else:
        rates_html = """<div class="card"><h2>Курсы валют</h2>
        <div class="err">Нет данных</div></div>"""

    todos = d["todos"]
    ranked = ai.get("todos_ranked")
    if ranked:
        items = "".join(
            f"<li><span class='pri {_pri_class(t.get('priority'))}'>"
            f"{_esc(t.get('priority','—'))}</span>{_esc(t.get('text'))}"
            + (f"<br><span class='why'>{_esc(t['why'])}</span>" if t.get('why') else "")
            + "</li>"
            for t in ranked
        )
        todos_html = (f"""<div class="card"><h2>Дела на сегодня"""
                      f"""<span class="badge-ai">AI приоритеты</span></h2>"""
                      f"""<ul>{items}</ul></div>""")
    elif todos:
        items = "".join(
            f"<li class='todo-high'>{_esc(t['text'])}<br>"
            f"<span class='src'>{_esc(t['meta'])}</span></li>"
            for t in todos
        )
        todos_html = f"""<div class="card"><h2>Дела на сегодня</h2><ul>{items}</ul></div>"""
    else:
        todos_html = """<div class="card"><h2>Дела на сегодня</h2>
        <ul><li>Срочных задач из почты нет.</li></ul></div>"""

    recs = "".join(f"<div class='rec'>{_esc(x)}</div>" for x in d["recommendations"])
    recs_html = f"""<div class="card"><h2>Рекомендации</h2>{recs}</div>"""

    n = d["news"]
    if n.get("items"):
        summary = ""
        if ai.get("news_summary"):
            summary = (f"<div class='ai-summary' style='margin-bottom:14px'>"
                       f"{_esc(ai['news_summary'])}</div>")
        items = "".join(
            f"<li class='news'><a href='{_esc(i['link'])}' target='_blank'>{_esc(i['title'])}</a>"
            f"<br><span class='src'>{_esc(i['source'])}</span></li>"
            for i in n["items"]
        )
        ai_badge = '<span class="badge-ai">AI выжимка</span>' if summary else ''
        news_html = (f"""<div class="card"><h2>Новости{ai_badge}</h2>"""
                     f"""{summary}<ul>{items}</ul></div>""")
    else:
        news_html = """<div class="card"><h2>Новости</h2>
        <div class="err">Нет данных</div></div>"""

    m = d["mail"]
    inbox = ai.get("inbox")
    if m.get("ok"):
        if inbox:
            # AI-разбор: приоритет + конкретное действие
            order = {"high": 0, "medium": 1, "low": 2}
            inbox_sorted = sorted(
                inbox, key=lambda x: order.get((x.get("priority") or "low").lower(), 3))
            items = "".join(
                f"<li><span class='pri {_pri_class(e.get('priority'))}'>"
                f"{_esc(e.get('priority','—'))}</span>{_esc(e.get('subject'))}"
                + (f"<br><span class='action'>→ {_esc(e['action'])}</span>" if e.get('action') else "")
                + (f" <span class='src'>· {_esc(e['from'])}</span>" if e.get('from') else "")
                + "</li>"
                for e in inbox_sorted
            )
            mail_html = (f"""<div class="card"><h2>Почта"""
                         f"""<span class="badge-ai">AI разбор</span></h2>"""
                         f"""<ul>{items}</ul></div>""")
        elif m.get("emails"):
            items = "".join(
                f"<li>{'🔴 ' if e.get('actionable') else ''}{_esc(e['subject'])}"
                f"<br><span class='src'>{_esc(e['from'])}</span></li>"
                for e in m["emails"]
            )
            label = "непрочитанные" if m.get("unread_only") else "последние"
            mail_html = f"""<div class="card"><h2>Почта ({label})</h2><ul>{items}</ul></div>"""
        else:
            mail_html = """<div class="card"><h2>Почта</h2>
            <ul><li>Новых писем нет 🎉</li></ul></div>"""
    else:
        mail_html = f"""<div class="card"><h2>Почта</h2>
        <div class="err">{_esc(m.get('error'))}</div></div>"""

    return HTML_TEMPLATE.format(
        generated_at=_esc(d["generated_at"]),
        weekday=_esc(d["weekday"]),
        greeting_html=greeting_html,
        weather_html=weather_html, rates_html=rates_html,
        todos_html=todos_html, recs_html=recs_html,
        news_html=news_html, mail_html=mail_html,
    )


def render_telegram(d: dict) -> str:
    """Markdown-текст для Telegram (parse_mode=Markdown)."""
    ai = d.get("ai", {}) or {}
    lines = [f"*🌅 Утренняя сводка*\n_{d['weekday']}, {d['generated_at']}_\n"]

    if ai.get("greeting"):
        lines.append(f"{ai['greeting']}\n")

    w = d["weather"]
    if w.get("ok"):
        lines.append(
            f"*Погода — {w['city']}*\n"
            f"{w['temp']}° ({w['description']}), ощущается {w['feels_like']}°\n"
            f"День: {w['t_min']}…{w['t_max']}°, осадки {w['precip_prob']}%\n"
        )

    r = d["rates"]
    if r.get("ok") and r.get("rates"):
        parts = []
        for x in r["rates"]:
            arrow = "▲" if x["up"] else "▼"
            parts.append(f"{x['code']} {x['value']}₽ {arrow}{abs(x['delta'])}")
        lines.append("*Курсы ЦБ:* " + " · ".join(parts) + "\n")

    pri_emoji = {"high": "🔴", "medium": "🟡", "low": "⚪"}
    ranked = ai.get("todos_ranked")
    if ranked:
        lines.append("*📌 Дела на сегодня* (по приоритету):")
        for t in ranked:
            em = pri_emoji.get((t.get("priority") or "low").lower(), "•")
            why = f" — _{t['why']}_" if t.get("why") else ""
            lines.append(f"{em} {t.get('text','')}{why}")
        lines.append("")
    elif d["todos"]:
        lines.append("*📌 Дела на сегодня:*")
        for t in d["todos"]:
            lines.append(f"• {t['text']}")
        lines.append("")

    lines.append("*💡 Рекомендации:*")
    for x in d["recommendations"]:
        lines.append(f"• {x}")
    lines.append("")

    n = d["news"]
    if n.get("items"):
        if ai.get("news_summary"):
            lines.append(f"*📰 Главное за утро:*\n{ai['news_summary']}\n")
        lines.append("*Новости:*")
        for i in n["items"][:6]:
            title = i["title"].replace("[", "(").replace("]", ")")
            lines.append(f"• [{title}]({i['link']})")
        lines.append("")

    m = d["mail"]
    inbox = ai.get("inbox")
    if inbox:
        order = {"high": 0, "medium": 1, "low": 2}
        inbox_sorted = sorted(
            inbox, key=lambda x: order.get((x.get("priority") or "low").lower(), 3))
        lines.append("*✉️ Разбор почты:*")
        for e in inbox_sorted[:8]:
            em = pri_emoji.get((e.get("priority") or "low").lower(), "•")
            act = f" → _{e['action']}_" if e.get("action") else ""
            lines.append(f"{em} {e.get('subject','')}{act}")
    elif m.get("ok") and m.get("emails"):
        action = [e for e in m["emails"] if e.get("actionable")]
        lines.append(f"*✉️ Почта:* {len(m['emails'])} писем, "
                     f"{len(action)} требуют внимания")

    return "\n".join(lines)
