# Деплой на VPS (Ubuntu/Debian) — пошагово

Итог: дашборд по адресу `https://твой-домен` с автоматическим HTTPS,
вход по **QR-коду через Telegram** (только для тебя), сводка в Telegram по утрам.

---

## Что понадобится

- VPS на Ubuntu/Debian с root или sudo
- Домен, указывающий A-записью на IP сервера (напр. `digest.example.com`)
- Telegram-бот (токен от [@BotFather](https://t.me/BotFather)) и твой `CHAT_ID`
- Gmail App Password и, по желанию, LLM-ключ

---

## Шаг 1. Подготовь домен

В DNS-настройках домена добавь **A-запись**, указывающую на IP твоего VPS:

```
digest.example.com.   A   203.0.113.10
```

Проверь, что резолвится (подожди до 10–15 минут после изменения):

```bash
dig +short digest.example.com
```

Должен вернуться IP сервера. Без этого HTTPS не выпустится.

---

## Шаг 2. Установи Docker на сервер

Подключись по SSH и выполни:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Перелогинься (выйди и зайди по SSH снова), чтобы группа docker применилась.
Проверь:

```bash
docker --version
docker compose version
```

---

## Шаг 3. Залей код через Git

Сначала на своём компьютере создай репозиторий (например, приватный на
GitHub/GitLab) и запушь туда папку `daily-digest`. Затем на сервере:

```bash
cd ~
git clone https://github.com/ТВОЙ_АККАУНТ/daily-digest.git
cd daily-digest
```

> Приватный репозиторий: используй SSH-ключ или Personal Access Token при clone.

---

## Шаг 4. Открой порты в фаерволе

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

(Порт 8080 наружу открывать НЕ нужно — к приложению ходит только Caddy.)

---

## Шаг 5. Настрой .env

```bash
cp .env.example .env
nano .env
```

Обязательно заполни:

| Переменная | Значение |
|---|---|
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | Почта и app-password |
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_CHAT_ID` | Твой Telegram ID (он же — единственный, кому разрешён вход) |
| `DIGEST_DOMAIN` | `digest.example.com` — твой домен |
| `AUTH_ENABLED` | `true` (вход по QR) |
| `COOKIE_SECURE` | `true` (т.к. HTTPS) |
| `LLM_PROVIDER` + ключ | По желанию (умный слой) |
| `PROFILE_*` | По желанию (персонализация) |

Как узнать `CHAT_ID`: напиши своему боту любое сообщение, открой
`https://api.telegram.org/bot<ТОКЕН>/getUpdates` и найди `"chat":{"id": ...}`.

---

## Шаг 6. Запусти в продакшн-режиме (с Caddy + HTTPS)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Caddy сам выпустит HTTPS-сертификат Let's Encrypt для твоего домена
(это занимает 10–60 секунд при первом запуске).

Проверь логи:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

Ищи строки: `Auth-бот: @твой_бот` и успешный выпуск сертификата Caddy.

---

## Шаг 7. Зайди на дашборд

Открой `https://digest.example.com` в браузере:

1. Увидишь страницу входа с **QR-кодом**.
2. Отсканируй QR телефоном (камерой или из приложения Telegram).
3. Telegram откроет твоего бота → нажми **Start / Подтвердить**.
4. Бот ответит «Вход подтверждён», а вкладка в браузере **сама откроет
   дашборд** (она опрашивает сервер каждые 2 секунды).

Сессия держится 30 дней. Кнопка «Выйти» — в правом верхнем углу дашборда.
Вход разрешён только с твоего `CHAT_ID` — чужой Telegram бот не пустит.

---

## Шаг 8. Проверь утреннюю отправку

Прямо сейчас, не дожидаясь расписания:

```bash
docker compose -f docker-compose.prod.yml run --rm digest python main.py run
```

Сводка должна прийти тебе в Telegram. Дальше она будет приходить ежедневно
в `DIGEST_TIME` (по умолчанию 08:00 МСК).

---

## Обновление кода

```bash
cd ~/daily-digest
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Остановка / перезапуск

```bash
docker compose -f docker-compose.prod.yml down       # остановить
docker compose -f docker-compose.prod.yml restart    # перезапустить
docker compose -f docker-compose.prod.yml logs -f    # смотреть логи
```

---

## Вариант без домена (доступ только для себя)

Если не хочешь возиться с доменом, есть два пути:

**А. SSH-туннель (дашборд виден только тебе):**
В `.env` поставь `AUTH_ENABLED=false`, `COOKIE_SECURE=false`, запусти обычный
`docker compose up -d --build` (без Caddy), а с локальной машины:

```bash
ssh -L 8080:localhost:8080 user@IP-сервера
```

Открой `http://localhost:8080` — увидишь дашборд. Снаружи он закрыт.

**Б. Только Telegram, без веб-дашборда:**
Веб можно просто не открывать наружу — сводка и так приходит в бот.
Поставь `AUTH_ENABLED=true` и не публикуй порт.

---

## Troubleshooting

- **HTTPS не выпускается** → проверь, что A-запись домена указывает на IP
  сервера (`dig +short твой-домен`) и порты 80/443 открыты.
- **QR не пускает** → убедись, что входишь с того Telegram-аккаунта, чей ID
  стоит в `TELEGRAM_CHAT_ID`. Чужие аккаунты бот отклоняет намеренно.
- **«Бот не настроен» на /login** → проверь `TELEGRAM_BOT_TOKEN`, посмотри
  логи: должна быть строка `Auth-бот: @...`.
- **Сводка не приходит** → запусти ручной прогон (Шаг 8) и читай логи.
