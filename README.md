# dance-bot

Агрегатор анонсов социальных танцев (bachata, kizomba, zouk) из Telegram-каналов Минска. Бот собирает посты из студий и сообществ, извлекает даты и места через LLM и публикует события в общий Google Calendar **«Танцы Минск»**.

- **[Github Pages](https://kondratyonoknikita.github.io/dance-bot/)**

  Веб-страница с календарём — можно смотреть в браузере без Google-аккаунта. На странице также есть ссылки для подписки через Google Calendar и iCal (Apple Calendar, Outlook и др.).

- **[Google calendar](https://calendar.google.com/calendar/u/0?cid=M2I3NWE2NjhiOTdjZjAxZjgxZmE1Mjc5N2UyZGFkOTEzZTgxMDkxNDMzNzU0OGY4OTQ1ZWVmMGVhNjVmYzAwN0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t)**

  Текстом для удобного копирования для подписки
  ```
  https://calendar.google.com/calendar/u/0?cid=M2I3NWE2NjhiOTdjZjAxZjgxZmE1Mjc5N2UyZGFkOTEzZTgxMDkxNDMzNzU0OGY4OTQ1ZWVmMGVhNjVmYzAwN0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t
  ```

**Источники:** студии и каналы вроде:
 - [Kredo](https://t.me/kredo_dance)
 - [Plyas Dance](https://t.me/plyas_dance)
 - [Dance Forever](https://t.me/danceforever_minsk)
 - [ESTA RICO](https://t.me/estarico_dance)
 - и другие

**Что попадает в календарь:** вечеринки, open-air, протанцовки, классы — с указанием времени, места, цены и ссылкой на оригинальный пост.

## Как читать события

| Поле | Пример |
|------|--------|
| Название | `Bachata / Kizomba — Party` |
| Место | `Bali, Кирова, 13` |
| Описание | тип, танцы, цена, текст поста, ссылка на Telegram |
| Цвет | красный — party, зелёный — open-air, бирюзовый — протанцовка, синий — класс |

## Фидбэк

Нашли ошибку в расписании, пропущенное событие или есть идея — создайте [issue на GitHub](https://github.com/KondratyonokNikita/dance-bot/issues).

---

## Для разработчиков

Техническая документация — в папке [dev_docs/](dev_docs/):

- [Установка и запуск](dev_docs/setup.md)
- [Архитектура](dev_docs/architecture.md)
- [TODO](dev_docs/TODO.md)
