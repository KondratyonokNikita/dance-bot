# dance-bot

Агрегатор анонсов социальных танцев (bachata, kizomba, zouk) из Telegram-каналов Минска. Бот собирает посты из студий и сообществ, извлекает даты и места через LLM и публикует события в общий Google Calendar **«Танцы Минск»**.

**Источники:** студии и каналы вроде [Kredo](https://t.me/kredo_dance), [Plyas Dance](https://t.me/plyas_dance), [Dance Forever](https://t.me/danceforever_minsk), [ESTA RICO](https://t.me/estarico_dance) и другие.

**Что попадает в календарь:** вечеринки, open-air, протанцовки, классы — с указанием времени, места, цены и ссылкой на оригинальный пост.

---

## Добавить календарь к себе

Календарь публичный. Подписка бесплатная, аккаунт Google нужен только для просмотра и синхронизации на телефон.

### Быстрый способ — по ссылке

Откройте ссылку в браузере, где вы залогинены в Google:

**[Танцы Минск — добавить календарь](https://calendar.google.com/calendar/u/0?cid=M2I3NWE2NjhiOTdjZjAxZjgxZmE1Mjc5N2UyZGFkOTEzZTgxMDkxNDMzNzU0OGY4OTQ1ZWVmMGVhNjVmYzAwN0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t)**

1. Перейдите по ссылке.
2. Откроется Google Calendar с предложением добавить календарь **«Танцы Минск»**.
3. Нажмите **«+ Добавить»** (или **Add**).
4. Календарь появится в списке слева — включите галочку, чтобы видеть события.

### Через настройки Google Calendar (веб)

1. Откройте [calendar.google.com](https://calendar.google.com).
2. Справа от **«Другие календари»** нажмите **«+»** → **«Подписаться на календарь»**.
3. Вставьте ссылку:

   ```
   https://calendar.google.com/calendar/u/0?cid=M2I3NWE2NjhiOTdjZjAxZjgxZmE1Mjc5N2UyZGFkOTEzZTgxMDkxNDMzNzU0OGY4OTQ1ZWVmMGVhNjVmYzAwN0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t
   ```

4. Нажмите **«Добавить календарь»**.

### На телефоне (Android / iPhone)

**Android (приложение Google Calendar):**

1. Откройте ссылку на календарь в Chrome — должно предложить добавить календарь.
2. Либо: приложение Google Calendar → **≡** → **Настройки** → **Добавить аккаунт** (если ещё нет Google) → затем в браузере добавьте календарь по ссылке выше — он синхронизируется автоматически.

**iPhone (приложение Google Calendar):**

1. Установите [Google Calendar](https://apps.apple.com/app/google-calendar/id909319292) и войдите в тот же Google-аккаунт.
2. Откройте ссылку на календарь в Safari → **Добавить**.
3. События появятся в приложении Google Calendar.

> **Примечание:** в стандартном приложении «Календарь» на iOS подписка на Google Calendar работает только через синхронизацию аккаунта Google в настройках iPhone (**Настройки → Календарь → Учётные записи → Google**). Проще использовать приложение Google Calendar.

### Как читать события

| Поле | Пример |
|------|--------|
| Название | `Bachata / Kizomba — Party` |
| Место | `Bali, Кирова, 13` |
| Описание | тип, танцы, цена, текст поста, ссылка на Telegram |
| Цвет | красный — party, зелёный — open-air, бирюзовый — протанцовка, синий — класс |

---

## Для разработчиков

Техническая документация — в папке [dev_docs/](dev_docs/):

- [Установка и запуск](dev_docs/setup.md)
- [Архитектура](dev_docs/architecture.md)
- [TODO](dev_docs/TODO.md)
