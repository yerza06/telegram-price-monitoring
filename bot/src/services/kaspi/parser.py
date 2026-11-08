import html
import json
import re

from selectolax.lexbor import LexborHTMLParser

from services.kaspi.exceptions import KaspiError

PRODUCT_URL_RE = re.compile(r"https?://(?:www\.)?kaspi\.kz/shop/p/(?:[^/?#]*-)?(\d+)/?(?:[?#].*)?")


def parse_product_id(url: str) -> str | None:
    match = PRODUCT_URL_RE.fullmatch(url.strip())
    return match[1] if match else None


def parse_component(page: str, name: str) -> object:
    """JSON из `BACKEND.components.<name> = {...}` в `<script>` страницы Kaspi."""
    marker = f"BACKEND.components.{name} = "
    for script in LexborHTMLParser(page).css("script"):
        text = script.text()
        start = text.find(marker)
        if start == -1:
            continue
        try:
            return json.JSONDecoder().raw_decode(text, start + len(marker))[0]
        except ValueError as e:
            raise KaspiError(f"не удалось разобрать {name}: {e!r}") from e
    raise KaspiError(f"на странице нет {name}")


def parse_product(page: str) -> tuple[str, str]:
    """Возвращает (ID товара, название) из HTML страницы товара."""
    try:
        card = parse_component(page, "item")["card"]
        return str(card["id"]), html.unescape(card["title"])
    except (KeyError, TypeError) as e:
        raise KaspiError(f"не удалось разобрать карточку товара: {e!r}") from e
