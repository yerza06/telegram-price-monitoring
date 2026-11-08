"""Kaspi.kz: разбор страницы товара и цена конкретного продавца.

Формат проверен 2026-10-27:

- Страница `https://kaspi.kz/shop/p/<slug>-<productId>/` редиректит (301) на актуальный slug.
  В `<script>` есть `BACKEND.components.item = {...}`; в нём `card.id` и `card.title`
  (в title бывают HTML-сущности, например `&#43;`).
- `https://kaspi.kz/shop/p/-<productId>/` (без slug) отдаёт ту же страницу без редиректа.
- Цены продавцов: `POST https://kaspi.kz/yml/offer-view/offers/{productId}` с JSON-телом
  `{"cityId": "750000000", "limit": 10, "page": 0}`, предложения отсортированы по цене. Без браузерного `User-Agent`
  соединение рвётся, без `Referer` на страницу товара — 403.
  `"merchantUID": "<ID продавца>"` в теле оставляет только этого продавца.
- Ответ: `{"offers": [{"merchantId": "234005", "merchantName": "ALPHA", "price": 360054.0, ...}],
  "total": 51, ...}`. Продавца нет — `"offers": []`.
  ID продавца — строка и бывает не числом (`Sulpak`, `Mechta`). `merchantUID` чувствителен
  к регистру, поэтому ID берём только из ответа Kaspi.
"""
