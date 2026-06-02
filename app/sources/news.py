"""Новости из RSS-лент."""
import feedparser


def get_news(feeds: list, max_items: int) -> dict:
    """Собирает свежие заголовки со всех лент, чередуя источники."""
    per_feed = []
    errors = []
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            source = parsed.feed.get("title", url)
            items = []
            for entry in parsed.entries[:max_items]:
                items.append({
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "source": source,
                })
            per_feed.append(items)
        except Exception as e:
            errors.append(f"{url}: {e}")

    # Чередуем источники (round-robin), чтобы не доминировал один фид
    merged = []
    i = 0
    while len(merged) < max_items and any(i < len(f) for f in per_feed):
        for f in per_feed:
            if i < len(f):
                merged.append(f[i])
                if len(merged) >= max_items:
                    break
        i += 1

    return {"ok": bool(merged), "items": merged, "errors": errors}
