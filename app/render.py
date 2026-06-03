"""Рендеринг сводки в HTML (веб) и в текст для Telegram."""
import html
import re as _re
from datetime import datetime
from urllib.parse import quote as _urlencode

from .config import config

# ---------------------------------------------------------------------------
# Статика: стили и скрипты дашборда. Держим как «сырые» строки (не прогоняем
# через .format), чтобы не экранировать фигурные скобки CSS/JS.
# ---------------------------------------------------------------------------

STYLE = """
  :root{
    --bg:#efece5; --card:#ffffff; --card-2:#f6f3ed;
    --ink:#2b2723; --ink-soft:#6f685f; --dim:#a39c91; --line:#ece7df;
    --accent:#d98a45; --accent-soft:#f4e7d6; --accent-ink:#b5702f;
    --green:#5a9a5e; --red:#c8624a;
    --shadow:0 1px 2px rgba(70,55,40,.04), 0 18px 40px -22px rgba(70,55,40,.22);
    --r:22px; --r2:15px;
  }
  html.dark{
    --bg:#1c1a17; --card:#26231f; --card-2:#2f2b26;
    --ink:#ece7df; --ink-soft:#b3aaa0; --dim:#7d756b; --line:#332f29;
    --accent:#d98a45; --accent-soft:#3a2e21; --accent-ink:#e0a767;
    --green:#73b377; --red:#d57a64;
    --shadow:0 1px 2px rgba(0,0,0,.25), 0 18px 40px -22px rgba(0,0,0,.6);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Inter',-apple-system,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--ink);
    -webkit-font-smoothing:antialiased;padding:34px 30px 60px;letter-spacing:-.01em}
  .shell{max-width:1120px;margin:0 auto;display:flex;gap:22px}

  /* floating pill nav */
  .nav{position:sticky;top:34px;align-self:flex-start;display:flex;flex-direction:column;gap:6px;
    background:var(--card);border-radius:999px;padding:12px 8px;box-shadow:var(--shadow)}
  .nav a,.nav button{width:40px;height:40px;display:grid;place-items:center;border-radius:50%;color:var(--dim);
    text-decoration:none;border:none;background:none;cursor:pointer;font-family:inherit;transition:.15s}
  .nav a:hover,.nav button:hover{background:var(--card-2);color:var(--ink)}
  .nav a.active{background:var(--ink);color:var(--card)}
  .nav svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
  @media(max-width:820px){.nav{display:none}}

  .main{flex:1;min-width:0}
  .head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:26px;padding:0 4px}
  .time{font-size:34px;font-weight:300;letter-spacing:-.02em;line-height:1}
  .hello{font-size:20px;font-weight:300;color:var(--ink-soft);margin-top:10px}
  .hello b{font-weight:600;color:var(--ink)}
  .status{font-size:13px;color:var(--dim);margin-top:6px;display:flex;align-items:center;gap:6px}
  .status .dot{width:7px;height:7px;border-radius:50%;background:var(--green)}
  .date{font-size:13px;color:var(--dim);text-align:right}

  .grid{display:grid;gap:14px;grid-template-columns:repeat(4,1fr)}
  .card{background:var(--card);border-radius:var(--r);padding:22px;box-shadow:var(--shadow);position:relative}
  .card h2{font-size:13px;font-weight:600;color:var(--ink);margin-bottom:16px;display:flex;align-items:center;gap:8px}
  .card h2 .n{font-size:12px;color:var(--dim);font-weight:500}
  .pillbtn{margin-left:auto;font-size:11px;color:var(--ink-soft);background:var(--card-2);border-radius:999px;padding:4px 11px;font-weight:500}
  .seg{margin-left:auto;display:inline-flex;background:var(--card-2);border-radius:999px;padding:2px}
  .seg button{border:none;background:none;font-family:inherit;font-size:12px;font-weight:600;color:var(--dim);padding:3px 11px;border-radius:999px;cursor:pointer;line-height:1.4}
  .seg button.on{background:var(--card);color:var(--ink);box-shadow:0 1px 2px rgba(70,55,40,.12)}
  .ai{font-size:10px;font-weight:600;color:var(--accent-ink);background:var(--accent-soft);padding:3px 9px;border-radius:999px}

  .hero{grid-column:span 4;padding:24px 26px}
  .hero p{font-size:18px;font-weight:300;line-height:1.5;max-width:80ch;color:var(--ink-soft)}
  .hero p b{font-weight:600;color:var(--ink)}
  .weather{grid-column:span 1} .todos{grid-column:span 3}
  .rates{grid-column:span 1} .crypto{grid-column:span 1} .news{grid-column:span 2} .mail{grid-column:span 2} .recs{grid-column:span 2}
  @media(max-width:820px){.grid{grid-template-columns:repeat(2,1fr)}
    .hero,.recs,.todos,.news,.mail{grid-column:span 2}.weather,.rates,.crypto{grid-column:span 1}}
  @media(max-width:480px){.grid{grid-template-columns:1fr}.card{grid-column:span 1!important}}

  /* weather */
  .w-temp{font-size:56px;font-weight:200;line-height:.9;letter-spacing:-.03em}
  .w-temp span{font-size:18px;color:var(--dim);font-weight:400;vertical-align:super}
  .w-desc{font-size:14px;color:var(--ink-soft);margin-top:8px}
  .w-meta{font-size:12px;color:var(--dim);margin-top:4px}
  .bars{display:flex;align-items:flex-end;gap:3px;height:36px;margin-top:16px}
  .bars i{flex:1;background:var(--accent);border-radius:2px;opacity:.85}

  /* todos */
  .tlist{list-style:none;display:flex;flex-direction:column}
  .tlist li{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid var(--line);font-size:14.5px}
  .tlist li:last-child{border-bottom:none}
  .tdot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
  .tdot.high{background:var(--accent)} .tdot.med{background:#c9a45a} .tdot.low{background:var(--line)}
  .tlist .tag{margin-left:auto;font-size:11px;color:var(--dim);white-space:nowrap}
  .tlist .ttext{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

  /* rates */
  .rate{display:flex;justify-content:space-between;align-items:baseline;padding:11px 0;border-bottom:1px solid var(--line)}
  .rate:last-child{border-bottom:none}
  .rate .code{font-size:13px;color:var(--ink-soft);font-weight:500}
  .rate .val{font-size:17px;font-weight:300}
  .delta{font-size:11px;margin-left:7px} .up{color:var(--green)} .down{color:var(--red)}

  /* lists with chevrons */
  .ai-box{background:var(--card-2);border-radius:var(--r2);padding:13px 15px;font-size:13.5px;color:var(--ink-soft);margin-bottom:8px;line-height:1.5}
  .row{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);text-decoration:none;color:inherit}
  .row:last-child{border-bottom:none}
  .row .body{flex:1;min-width:0}
  .row .t{font-size:14px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .row .s{font-size:12px;color:var(--dim);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .row .chev{color:var(--dim);font-size:15px}
  a.row:hover .t{color:var(--accent-ink)}
  .mdot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
  .mdot.high{background:var(--accent)} .mdot.med{background:#c9a45a} .mdot.low{background:var(--line)}

  .chips{display:flex;flex-wrap:wrap;gap:9px}
  .chip{background:var(--card-2);border-radius:999px;padding:9px 15px;font-size:13px;color:var(--ink-soft)}
  .empty{font-size:13px;color:var(--dim)}

  /* todos checklist: кастомный чекбокс */
  .todo-cb{-webkit-appearance:none;appearance:none;width:16px;height:16px;flex-shrink:0;
    border:1.5px solid var(--line);border-radius:4px;cursor:pointer;position:relative;
    transition:.15s;background:var(--card)}
  .todo-cb:hover{border-color:var(--accent)}
  .todo-cb:checked{background:var(--accent);border-color:var(--accent)}
  .todo-cb:checked::after{content:'';position:absolute;left:4px;top:1px;
    width:5px;height:9px;border:2px solid #fff;border-top:0;border-left:0;transform:rotate(45deg)}
  .tlist li.done .ttext{text-decoration:line-through;color:var(--dim)}
  .tlist li.done .tdot{opacity:.4}
"""

# SVG-иконки для навбара (inline, без icon-библиотек)
_IC_HOME = '<svg viewBox="0 0 24 24"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/></svg>'
_IC_THEME = '<svg viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>'
_IC_LOGOUT = '<svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>'

SCRIPT = """
function lsGet(k){try{return localStorage.getItem(k)}catch(e){return null}}
function lsSet(k,v){try{localStorage.setItem(k,v)}catch(e){}}

// --- переключатель валюты крипты ₽/$ (по умолчанию ₽) ---
const seg=document.getElementById('ccyseg');
if(seg){
  function setCcy(c){
    document.querySelectorAll('.crypto .num').forEach(n=>{if(n.dataset[c])n.textContent=n.dataset[c]});
    seg.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.ccy===c));
    lsSet('dd-ccy',c);
  }
  seg.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>setCcy(b.dataset.ccy)));
  setCcy(lsGet('dd-ccy')||'rub');
}

// --- тема light/dark ---
const themeBtn=document.getElementById('themebtn');
if(themeBtn)themeBtn.addEventListener('click',()=>{
  const dark=document.documentElement.classList.toggle('dark');
  lsSet('dd-theme',dark?'dark':'light');
});

// --- todos checklist: сохраняем выполненные в localStorage ---
(function(){
  var today=new Date().toISOString().slice(0,10);
  var LS_KEY='dd-todos-'+today;
  var done={};
  try{done=JSON.parse(localStorage.getItem(LS_KEY)||'{}')}catch(e){}
  document.querySelectorAll('.todo-cb').forEach(function(cb){
    var k=cb.dataset.key;
    if(done[k]){cb.checked=true;cb.closest('li').classList.add('done');}
    cb.addEventListener('change',function(){
      cb.closest('li').classList.toggle('done',cb.checked);
      if(cb.checked)done[k]=1;else delete done[k];
      try{localStorage.setItem(LS_KEY,JSON.stringify(done));}catch(e){}
    });
  });
})();
"""

# Скрипт в <head>: применяет сохранённую тему до отрисовки (без мигания).
THEME_INIT = (
    "<script>try{var t=localStorage.getItem('dd-theme');"
    "if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme:dark)').matches))"
    "document.documentElement.classList.add('dark')}catch(e){}</script>"
)

_MONTHS_GEN = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
               "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def _esc(s):
    return html.escape(str(s or ""))


def _safe_url(url: str) -> str:
    """Пропускаем только http/https-ссылки, иначе пустую строку."""
    u = str(url or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else ""


def _gmail_url(sender: str, subject: str = "") -> str:
    """Gmail search URL для отправителя письма.

    Пытается извлечь email-адрес из поля «От»; при неудаче ищет по теме.
    Всегда возвращает валидную https-ссылку или пустую строку.
    """
    s = str(sender or "").strip()
    # Формат «Имя <email@host>»
    m = _re.search(r'<([^>]+@[^>]+)>', s)
    if m:
        term = "from:" + m.group(1).strip()
    elif "@" in s:
        # Голый «email@host» или «имя email@host» — берём токен с @
        addr = next((tok for tok in s.split() if "@" in tok), s)
        term = "from:" + addr.strip()
    elif subject:
        # Только отображаемое имя (напр. «ВТБ») → ищем по теме
        term = "subject:" + subject[:60]
    else:
        return ""
    return "https://mail.google.com/mail/u/0/#search/" + _urlencode(term)


def _dot_class(p: str) -> str:
    """Приоритет -> класс цветной точки (high/med/low)."""
    return {"high": "high", "medium": "med", "low": "low"}.get(
        (p or "").lower(), "low")


def _plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _fmt_num(value, comma=False) -> str:
    """Число с разделителем тысяч пробелом; comma=True → дробная часть."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    if comma:
        s = f"{v:,.2f}"
    else:
        s = f"{v:,.0f}"
    # Разряды — неразрывным пробелом (U+00A0), чтобы число не переносилось;
    # десятичная точка → запятая (русская типографика).
    return s.replace(",", "\u00a0").replace(".", ",")


def _fmt_money(value, currency: str) -> str:
    """USD/RUB с группировкой. Малые числа (<100) — с копейками."""
    if value is None:
        return "—"
    try:
        small = abs(float(value)) < 100
    except (TypeError, ValueError):
        return "—"
    body = _fmt_num(value, comma=small)
    return f"${body}" if currency == "usd" else f"{body} ₽"


def _delta_html(value, suffix="") -> str:
    """Стрелка + значение изменения. value>=0 → рост (зелёный)."""
    if value is None:
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    arrow = "▲" if v >= 0 else "▼"
    cls = "up" if v >= 0 else "down"
    num = f"{abs(v):.1f}".replace(".", ",") if suffix == "%" else _fmt_num(abs(v), comma=True)
    return f"<span class='delta {cls}'>{arrow}{num}{suffix}</span>"


def _parse_when(generated_at: str):
    """'%d.%m.%Y %H:%M' → (time_str, day, month_idx). При ошибке — (gen, '', 0)."""
    try:
        dt = datetime.strptime(generated_at, "%d.%m.%Y %H:%M")
        return dt.strftime("%H:%M"), dt.day, dt.month
    except (ValueError, TypeError):
        return generated_at, "", 0


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Утренняя сводка — {generated_at}</title>
{theme_init}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap" rel="stylesheet">
<style>{style}</style>
</head>
<body>
<div class="shell">
  <nav class="nav">
    <a class="active" href="/" title="Главная">{ic_home}</a>
    <button id="themebtn" title="Светлая / тёмная тема" type="button">{ic_theme}</button>
    <a href="/logout" title="Выйти">{ic_logout}</a>
  </nav>

  <div class="main">
    <div class="head">
      <div>
        <div class="time">{time_str}</div>
        <div class="hello">{hello}</div>
        <div class="status"><span class="dot" style="background:{dot_color}"></span>{status_text}</div>
      </div>
      <div class="date">{weekday}<br>{date_label}</div>
    </div>

    <div class="grid" id="grid">
      {hero_html}
      {weather_html}
      {todos_html}
      {rates_html}
      {crypto_html}
      {news_html}
      {mail_html}
      {recs_html}
    </div>
  </div>
</div>
<script>{script}</script>
</body>
</html>"""


def _card(data_id: str, extra_class: str, inner: str) -> str:
    return f'<div class="card {extra_class}" data-id="{data_id}">{inner}</div>'


def render_html(d: dict) -> str:
    ai = d.get("ai", {}) or {}
    todos = d.get("todos") or []
    ranked = ai.get("todos_ranked")
    effective_todos = ranked or todos

    # --- шапка ---
    time_str, day, month = _parse_when(d.get("generated_at", ""))
    date_label = f"{day} {_MONTHS_GEN[month]}" if month else _esc(d.get("generated_at", ""))
    name = config.PROFILE_NAME
    hello = f"Доброе утро, <b>{_esc(name)}</b>" if name else "Доброе утро"

    # важные письма: из AI-разбора (priority=high) или из actionable
    inbox = ai.get("inbox")
    mail = d.get("mail", {}) or {}
    if inbox:
        important = sum(1 for e in inbox if (e.get("priority") or "").lower() == "high")
    else:
        important = sum(1 for e in mail.get("emails", []) if e.get("actionable"))
    todo_count = len(effective_todos)

    parts = [f"{todo_count} " + _plural(todo_count, "дело", "дела", "дел")]
    if important:
        parts.append(f"{important} " + _plural(
            important, "важное письмо", "важных письма", "важных писем"))
    lead = "Всё спокойно" if important == 0 else "Есть важное"
    status_text = lead + " · " + " · ".join(parts)
    dot_color = "var(--green)" if important == 0 else "var(--accent)"

    # --- hero (обращение) ---
    if ai.get("greeting"):
        hero_inner = (f'<h2>Доброе утро <span class="ai">AI</span></h2>'
                      f'<p>{_esc(ai["greeting"])}</p>')
    else:
        hero_inner = ('<h2>Доброе утро</h2>'
                      '<p>Хорошего и продуктивного дня! Ниже — всё важное на сегодня.</p>')
    hero_html = _card("hero", "hero", hero_inner)

    # --- погода ---
    w = d.get("weather", {}) or {}
    if w.get("ok"):
        bars = ""
        hourly = w.get("hourly") or []
        if hourly:
            lo, hi = min(hourly), max(hourly)
            rng = (hi - lo) or 1
            bars = '<div class="bars">' + "".join(
                f'<i style="height:{30 + round((t - lo) / rng * 70)}%"></i>'
                for t in hourly[:12]) + "</div>"
        weather_inner = (
            f'<h2>Погода · {_esc(w.get("city"))}</h2>'
            f'<div class="w-temp">{w.get("temp")}<span>°C</span></div>'
            f'<div class="w-desc">{_esc(w.get("description"))}</div>'
            f'<div class="w-meta">Ощущается {w.get("feels_like")}° · '
            f'ветер {w.get("wind")} км/ч</div>{bars}')
    else:
        weather_inner = (f'<h2>Погода</h2>'
                         f'<div class="empty">Не удалось получить: {_esc(w.get("error"))}</div>')
    weather_html = _card("weather", "weather", weather_inner)

    # --- дела ---
    if effective_todos:
        rows = ""
        for t in effective_todos:
            dot = _dot_class(t.get("priority"))
            tag = t.get("why") or t.get("meta") or ""
            tag_html = f'<span class="tag">{_esc(tag)}</span>' if tag else ""
            # ключ для localStorage: нормализованный текст, до 50 символов
            cb_key = _esc((t.get("text") or "").lower().strip()[:50])
            rows += (f'<li>'
                     f'<input type="checkbox" class="todo-cb" data-key="{cb_key}">'
                     f'<span class="tdot {dot}"></span>'
                     f'<span class="ttext">{_esc(t.get("text"))}</span>{tag_html}</li>')
        todos_badge = ' <span class="ai">AI приоритеты</span>' if ranked else ""
        todos_inner = (f'<h2>Дела на сегодня{todos_badge}</h2>'
                       f'<ul class="tlist">{rows}</ul>')
    else:
        todos_inner = '<h2>Дела на сегодня</h2><div class="empty">Срочных задач нет 🎉</div>'
    todos_html = _card("todos", "todos", todos_inner)

    # --- курсы ЦБ ---
    r = d.get("rates", {}) or {}
    if r.get("ok") and r.get("rates"):
        rows = ""
        for x in r["rates"]:
            rows += (f'<div class="rate"><span class="code">{_esc(x["code"])}</span>'
                     f'<span class="val">{_fmt_num(x["value"], comma=True)}'
                     f'{_delta_html(x.get("delta"))}</span></div>')
        rates_inner = f'<h2>Курсы ЦБ РФ</h2>{rows}'
    else:
        rates_inner = '<h2>Курсы ЦБ РФ</h2><div class="empty">Нет данных</div>'
    rates_html = _card("rates", "rates", rates_inner)

    # --- крипто ---
    cr = d.get("crypto", {}) or {}
    if cr.get("ok") and cr.get("items"):
        rows = ""
        for it in cr["items"]:
            usd = _fmt_money(it.get("usd"), "usd")
            rub = _fmt_money(it.get("rub"), "rub")
            rows += (f'<div class="rate"><span class="code">{_esc(it["code"])}</span>'
                     f'<span class="val"><span class="num" data-usd="{_esc(usd)}" '
                     f'data-rub="{_esc(rub)}">{_esc(rub)}</span>'
                     f'{_delta_html(it.get("change24h"), "%")}</span></div>')
        crypto_inner = ('<h2>Крипто <span class="seg" id="ccyseg">'
                        '<button data-ccy="usd" type="button">$</button>'
                        '<button data-ccy="rub" type="button">₽</button></span></h2>'
                        f'{rows}')
        crypto_html = _card("crypto", "crypto", crypto_inner)
    else:
        # источник выключен/упал — карточку показываем только если настроен
        if config.CRYPTO_COINS:
            crypto_html = _card("crypto", "crypto",
                                '<h2>Крипто</h2><div class="empty">Нет данных</div>')
        else:
            crypto_html = ""

    # --- новости ---
    n = d.get("news", {}) or {}
    if n.get("items"):
        box = ""
        if ai.get("news_summary"):
            box = f'<div class="ai-box">{_esc(ai["news_summary"])}</div>'
        rows = ""
        for i in n["items"]:
            url = _safe_url(i.get("link"))
            inner = (f'<div class="body"><div class="t">{_esc(i.get("title"))}</div>'
                     f'<div class="s">{_esc(i.get("source"))}</div></div>'
                     f'<span class="chev">›</span>')
            if url:
                rows += f'<a class="row" href="{_esc(url)}" target="_blank" rel="noopener">{inner}</a>'
            else:
                rows += f'<div class="row">{inner}</div>'
        ai_badge = ' <span class="ai">AI выжимка</span>' if box else ""
        news_inner = f'<h2>Новости{ai_badge}</h2>{box}{rows}'
    else:
        news_inner = '<h2>Новости</h2><div class="empty">Нет данных</div>'
    news_html = _card("news", "news", news_inner)

    # --- почта ---
    if mail.get("ok"):
        if inbox:
            order = {"high": 0, "medium": 1, "low": 2}
            inbox_sorted = sorted(
                inbox, key=lambda x: order.get((x.get("priority") or "low").lower(), 3))
            rows = ""
            for e in inbox_sorted:
                dot = _dot_class(e.get("priority"))
                sub = e.get("action") or e.get("from") or ""
                url = _gmail_url(e.get("from", ""), e.get("subject", ""))
                inner = (f'<span class="mdot {dot}"></span>'
                         f'<div class="body"><div class="t">{_esc(e.get("subject"))}</div>'
                         f'<div class="s">{_esc(sub)}</div></div>'
                         f'<span class="chev">›</span>')
                if url:
                    rows += (f'<a class="row" href="{_esc(url)}" '
                             f'target="_blank" rel="noopener">{inner}</a>')
                else:
                    rows += f'<div class="row">{inner}</div>'
            mail_inner = f'<h2>Почта <span class="ai">AI разбор</span></h2>{rows}'
        elif mail.get("emails"):
            rows = ""
            for e in mail["emails"]:
                dot = "high" if e.get("actionable") else "low"
                url = _gmail_url(e.get("from", ""), e.get("subject", ""))
                inner = (f'<span class="mdot {dot}"></span>'
                         f'<div class="body"><div class="t">{_esc(e.get("subject"))}</div>'
                         f'<div class="s">{_esc(e.get("from"))}</div></div>'
                         f'<span class="chev">›</span>')
                if url:
                    rows += (f'<a class="row" href="{_esc(url)}" '
                             f'target="_blank" rel="noopener">{inner}</a>')
                else:
                    rows += f'<div class="row">{inner}</div>'
            mail_inner = f'<h2>Почта</h2>{rows}'
        else:
            mail_inner = '<h2>Почта</h2><div class="empty">Новых писем нет 🎉</div>'
    else:
        mail_inner = f'<h2>Почта</h2><div class="empty">{_esc(mail.get("error"))}</div>'
    mail_html = _card("mail", "mail", mail_inner)

    # --- рекомендации ---
    recs = d.get("recommendations") or []
    if recs:
        chips = "".join(f'<div class="chip">{_esc(x)}</div>' for x in recs)
        recs_html = _card("recs", "recs", f'<h2>Рекомендации</h2><div class="chips">{chips}</div>')
    else:
        recs_html = ""

    return HTML_TEMPLATE.format(
        generated_at=_esc(d.get("generated_at")),
        theme_init=THEME_INIT, style=STYLE, script=SCRIPT,
        ic_home=_IC_HOME, ic_theme=_IC_THEME, ic_logout=_IC_LOGOUT,
        time_str=_esc(time_str), hello=hello,
        dot_color=dot_color, status_text=_esc(status_text),
        weekday=_esc(d.get("weekday")), date_label=_esc(date_label),
        hero_html=hero_html, weather_html=weather_html, todos_html=todos_html,
        rates_html=rates_html, crypto_html=crypto_html, news_html=news_html,
        mail_html=mail_html, recs_html=recs_html,
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
