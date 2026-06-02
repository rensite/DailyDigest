"""HTML страницы логина с QR-кодом для входа через Telegram."""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вход — Утренняя сводка</title>
<style>
  :root {{ --bg:#0f1419; --card:#1a2027; --accent:#4f9dff;
    --text:#e6edf3; --muted:#8b949e; --line:#2d333b; --green:#3fb950; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; min-height:100vh; display:flex; align-items:center;
    justify-content:center; background:var(--bg); color:var(--text);
    font-family:-apple-system,'Segoe UI',Roboto,sans-serif; }}
  .box {{ background:var(--card); border:1px solid var(--line);
    border-radius:18px; padding:36px 40px; max-width:380px; text-align:center; }}
  h1 {{ font-size:22px; margin:0 0 6px; }}
  p {{ color:var(--muted); font-size:14px; line-height:1.5; margin:0 0 22px; }}
  #qr {{ background:#fff; padding:16px; border-radius:14px; display:inline-block;
    line-height:0; }}
  .status {{ margin-top:20px; font-size:14px; color:var(--muted);
    display:flex; align-items:center; justify-content:center; gap:8px; }}
  .dot {{ width:8px; height:8px; border-radius:50%; background:var(--accent);
    animation:pulse 1.4s infinite; }}
  @keyframes pulse {{ 0%,100%{{opacity:.3}} 50%{{opacity:1}} }}
  .ok {{ color:var(--green); }}
  .btn {{ display:inline-block; margin-top:18px; color:var(--accent);
    font-size:14px; text-decoration:none; }}
  .hint {{ margin-top:18px; font-size:12px; color:var(--muted); }}
</style>
</head>
<body>
<div class="box">
  <h1>Утренняя сводка</h1>
  <p>Отсканируй QR телефоном и подтверди вход в Telegram-боте.</p>
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
    colorDark: "#0f1419", colorLight: "#ffffff"
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
    return LOGIN_HTML.format(token=token, deep_link=deep_link)
