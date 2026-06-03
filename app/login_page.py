"""HTML страницы логина с QR-кодом для входа через Telegram."""

# Стили держим «сырой» строкой (без .format), чтобы не экранировать скобки CSS.
_STYLE = """
  :root{
    --bg:#efece5; --card:#ffffff; --card-2:#f6f3ed;
    --ink:#2b2723; --ink-soft:#6f685f; --dim:#a39c91; --line:#ece7df;
    --accent:#d98a45; --accent-ink:#b5702f; --green:#5a9a5e;
    --shadow:0 1px 2px rgba(70,55,40,.04), 0 18px 40px -22px rgba(70,55,40,.22);
  }
  html.dark{
    --bg:#1c1a17; --card:#26231f; --card-2:#2f2b26;
    --ink:#ece7df; --ink-soft:#b3aaa0; --dim:#7d756b; --line:#332f29;
    --accent:#d98a45; --accent-ink:#e0a767; --green:#73b377;
    --shadow:0 1px 2px rgba(0,0,0,.25), 0 18px 40px -22px rgba(0,0,0,.6);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{min-height:100vh;display:flex;align-items:center;justify-content:center;
    background:var(--bg);color:var(--ink);letter-spacing:-.01em;padding:24px;
    font-family:'Inter',-apple-system,'Segoe UI',Roboto,sans-serif;-webkit-font-smoothing:antialiased}
  .box{background:var(--card);border-radius:26px;padding:38px 40px;max-width:380px;
    width:100%;text-align:center;box-shadow:var(--shadow)}
  h1{font-size:22px;font-weight:600;margin-bottom:8px}
  .lead{color:var(--ink-soft);font-size:14px;line-height:1.5;margin-bottom:24px}
  #qr{background:#fff;padding:16px;border-radius:18px;display:inline-block;line-height:0;
    box-shadow:inset 0 0 0 1px var(--line)}
  .status{margin-top:22px;font-size:14px;color:var(--ink-soft);
    display:flex;align-items:center;justify-content:center;gap:8px}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--accent);animation:pulse 1.4s infinite}
  @keyframes pulse{0%,100%{opacity:.3}50%{opacity:1}}
  .ok{color:var(--green);font-weight:500}
  .btn{display:inline-block;margin-top:18px;color:var(--accent-ink);font-size:14px;
    font-weight:500;text-decoration:none;background:var(--card-2);border-radius:999px;padding:9px 18px}
  .btn:hover{filter:brightness(.97)}
  .hint{margin-top:18px;font-size:12px;color:var(--dim);line-height:1.5}
"""

_THEME_INIT = (
    "<script>try{var t=localStorage.getItem('dd-theme');"
    "if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme:dark)').matches))"
    "document.documentElement.classList.add('dark')}catch(e){}</script>"
)

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вход — Утренняя сводка</title>
{theme_init}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>{style}</style>
</head>
<body>
<div class="box">
  <h1>Утренняя сводка</h1>
  <div class="lead">Отсканируй QR телефоном и подтверди вход в Telegram-боте.</div>
  <div id="qr"></div>
  <div class="status" id="status"><span class="dot"></span> Ждём подтверждения…</div>
  <a class="btn" id="tglink" href="{deep_link}" target="_blank">Открыть в Telegram →</a>
  <div class="hint">Ссылка действует 5 минут. Вход доступен только владельцу.</div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>
  var token = "{token}";
  var deepLink = "{deep_link}";
  new QRCode(document.getElementById("qr"), {{
    text: deepLink, width: 220, height: 220,
    colorDark: "#2b2723", colorLight: "#ffffff"
  }});

  function poll() {{
    fetch("/auth/status?token=" + encodeURIComponent(token))
      .then(function(r) {{ return r.json(); }})
      .then(function(d) {{
        if (d.authenticated) {{
          var s = document.getElementById("status");
          s.innerHTML = '<span class="ok">✓ Вход подтверждён, открываю…</span>';
          setTimeout(function() {{ window.location.href = "/"; }}, 600);
        }} else {{
          setTimeout(poll, 2000);
        }}
      }})
      .catch(function() {{ setTimeout(poll, 3000); }});
  }}
  setTimeout(poll, 2000);
</script>
</body>
</html>"""


def render_login(token: str, bot_username: str) -> str:
    deep_link = f"https://t.me/{bot_username}?start={token}"
    return LOGIN_HTML.format(token=token, deep_link=deep_link,
                             style=_STYLE, theme_init=_THEME_INIT)
