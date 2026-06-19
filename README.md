# dance-bot

Знаете, что бесит? Чтобы понять, где сегодня open или вечеринка, надо лазить по куче Telegram-чатов и искать нужный анонс среди занятий и прочего.

**dance-bot** собирает такие анонсы в одном месте: бот читает посты из студий и сообществ, извлекает даты и места через LLM и публикует события в Google Calendar — **отдельный календарь на каждый танец** (bachata, kizomba, zouk).

- **[Github Pages](https://kondratyonoknikita.github.io/dance-bot/)**

  Веб-страница с тремя календарями сразу — можно смотреть в браузере без Google-аккаунта.

- **Google Calendar — подписка по танцам**

  - [Бачата](https://calendar.google.com/calendar/u/0?cid=M2I3NWE2NjhiOTdjZjAxZjgxZmE1Mjc5N2UyZGFkOTEzZTgxMDkxNDMzNzU0OGY4OTQ1ZWVmMGVhNjVmYzAwN0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
  - [Кизомба](https://calendar.google.com/calendar/u/0?cid=MjFjZDAxYjBjMzA1ZjNiOTQ0NGJkYjFkZTlkOWI2ZDhiMTZmMzEzNDhkYzRhMzAwOWM2YTlhZjY4ZWRmOThjN0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
  - [Зук](https://calendar.google.com/calendar/u/0?cid=NDFmZGU5M2EwNjAyODM2MmUxNjY0MWE2Zjk2ZmNiZDYwN2Y1OTRiMmRlMWM0MmRjNzRmZjdmN2JiYzlhNjhiZEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t)

**Источники:** студии и каналы вроде:
 - [Kredo](https://t.me/kredo_dance)
 - [Plyas Dance](https://t.me/plyas_dance)
 - [Dance Forever](https://t.me/danceforever_minsk)
 - [ESTA RICO](https://t.me/estarico_dance)
 - и другие

**Что попадает в календарь:** вечеринки, open-air, протанцовки, классы — с указанием времени, места, цены и ссылкой на оригинальный пост. Событие с несколькими танцами попадает в несколько календарей.

## Как читать события

| Поле | Пример |
|------|--------|
| Название | `Bachata / Kizomba — Party` |
| Место | `Bali, Кирова, 13` |
| Описание | тип, танцы, цена, текст поста, ссылка на Telegram |
| Цвет | задаётся календарём (бачата / кизомба / зук) |

## Фидбэк

Нашли ошибку в расписании, пропущенное событие или есть идея — создайте [issue на GitHub](https://github.com/KondratyonokNikita/dance-bot/issues).

---

## Для разработчиков

Техническая документация — в папке [dev_docs/](dev_docs/):

- [Установка и запуск](dev_docs/setup.md)
- [Архитектура](dev_docs/architecture.md)
- [TODO](dev_docs/TODO.md)
