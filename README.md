# 🤖 Universal Search Bot — Russia Edition

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Linux%20%7C%20Windows-orange)](https://termux.dev)
[![AI](https://img.shields.io/badge/AI-OpenRouter%20%7C%20Gemma-purple)](https://openrouter.ai)

> Универсальный поисковый Telegram-бот с AI-анализом, оптимизированный для пользователей из России.
> Ищет музыку, аниме, фильмы, книги и любую другую информацию через популярные российские и мировые сервисы.

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Демо](#-демо)
- [Установка](#-установка)
  - [Termux (Android)](#termux-android)
  - [Linux / Windows](#linux--windows)
- [Настройка](#-настройка)
- [Запуск](#-запуск)
- [Использование](#-использование)
  - [Поиск музыки](#поиск-музыки)
  - [Поиск аниме](#поиск-аниме)
  - [Поиск фильмов](#поиск-фильмов)
  - [Универсальный поиск](#универсальный-поиск)
- [Админ-панель](#-админ-панель)
- [Провайдеры](#-провайдеры)
- [Архитектура](#-архитектура)
- [FAQ / Troubleshooting](#-faq--troubleshooting)
- [Лицензия](#-лицензия)

---

## ✨ Возможности

| Категория | Провайдеры | Описание |
|-----------|-----------|----------|
| 🎵 **Музыка** | Яндекс.Музыка, VK Music, Last.fm | Поиск треков, альбомов, исполнителей |
| 🎌 **Аниме** | Shikimori.one | Русскоязычная база аниме с рейтингами, жанрами, сериями |
| 🎬 **Фильмы** | Кинопоиск | Поиск фильмов и сериалов с рейтингами |
| 🔍 **Универсальный** | Яндекс, DuckDuckGo | Веб-поиск с AI-анализом результатов |
| 🤖 **AI-анализ** | OpenRouter (Gemma, Claude, GPT и др.) | Автоматический анализ запроса, ранжирование источников, генерация красивого ответа |

**Дополнительно:**
- 🧠 Автоопределение категории запроса
- 💾 Кэширование результатов (1 час)
- 📊 Статистика пользователей и логи
- 📢 Рассылка сообщений администратором
- 🔌 Включение/отключение провайдеров на лету
- 🛡️ Работа без `openai` и `lxml` — только `requests` + `BeautifulSoup`

---

## 🖼 Демо

```
Пользователь: аниме про школу романтика

Бот:
🎌 Результат поиска
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Что найдено:
• «Хоримия» (Horimiya) — 13 эп., ★8.2
  Школьная романтика, повседневность
  Статус: вышел | Ссылка: shikimori.one/animes/42822

• «Торадора!» (Toradora!) — 25 эп., ★8.4
  Романтика, комедия, драма
  Статус: вышел

⚠️ Нюансы:
Некоторые тайтлы доступны только на стриминговых платформах (VK Видео, Crunchyroll)

🔗 Источники:
1. [Shikimori — Хоримия](...) — описание, рейтинг
2. [Shikimori — Торадора](...) — описание, рейтинг

💡 Совет:
Если хотите что-то посвежее — посмотрите «Учитель маскированной девицы» (2026)
```

---

## 🚀 Установка

### Termux (Android)

```bash
# 1. Обновляем пакеты
pkg update && pkg upgrade -y

# 2. Устанавливаем Python и зависимости
pkg install python -y
pip install pyTelegramBotAPI requests beautifulsoup4

# 3. Клонируем репозиторий (или скачиваем файл)
git clone https://github.com/ваш-ник/universal-search-bot.git
cd universal-search-bot

# 4. Настраиваем конфиг (см. раздел Настройка)
nano bot.py

# 5. Запускаем
python bot.py
```

### Linux / Windows

```bash
# Клонируем репозиторий
git clone https://github.com/ваш-ник/universal-search-bot.git
cd universal-search-bot

# Создаём виртуальное окружение (опционально)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# Устанавливаем зависимости
pip install pyTelegramBotAPI requests beautifulsoup4

# Запуск
python bot.py
```

---

## ⚙️ Настройка

Откройте `bot.py` и заполните переменные в начале файла:

```python
BOT_TOKEN           = "1234567890:ABC...XYZ"      # Токен от @BotFather
ADMIN_ID            = 1234567890                  # Ваш Telegram ID (число, не строка!)

OPENROUTER_API_KEY  = "sk-or-v1-..."              # Ключ с openrouter.ai
LLM_MODEL           = "google/gemma-4-26b-a4b-it:free"  # или другая модель
LLM_BASE_URL        = "https://openrouter.ai/api/v1"

# Опционально:
VK_ACCESS_TOKEN     = ""   # Для поиска музыки через VK API
LASTFM_API_KEY      = ""   # Для расширенного поиска музыки
```

### Где взять ключи?

| Сервис | Ссылка | Стоимость |
|--------|--------|-----------|
| **Telegram Bot Token** | [@BotFather](https://t.me/BotFather) | Бесплатно |
| **OpenRouter API** | [openrouter.ai/keys](https://openrouter.ai/keys) | Бесплатные модели есть |
| **VK Access Token** | [vk.com/dev/access_token](https://vk.com/dev/access_token) | Бесплатно (требует приложение) |
| **Last.fm API** | [last.fm/api/account/create](https://www.last.fm/api/account/create) | Бесплатно |

> 💡 **Совет:** Для начала достаточно только `BOT_TOKEN` и `OPENROUTER_API_KEY`. Остальное — по желанию.

---

## ▶️ Запуск

```bash
python bot.py
```

При успешном старте вы увидите:
```
============================================================
  🤖 UNIVERSAL SEARCH BOT — RUSSIA EDITION (Termux)
============================================================
  LLM: google/gemma-4-26b-a4b-it:free
  VK API: ❌ не настроен (веб-поиск)
  Last.fm: ❌ не настроен (опционально)
  Admin ID: 1234567890
============================================================
  Бот запущен! Жду сообщений...
============================================================
```

---

## 📖 Использование

### Базовые команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню, приветствие |
| `/help` | Справка по использованию |
| `/search <запрос>` | Явный поиск по запросу |
| `/admin` | **(только админ)** Панель управления |

### Поиск музыки 🎵

Просто напишите боту:
- `трек Монеточка — Каждый раз`
- `альбом Земфира`
- `песня ДДТ Что такое осень`
- `новинки русской музыки 2026`

Бот определит категорию и найдёт треки на **Яндекс.Музыке**, **VK Music** и **Last.fm**.

### Поиск аниме 🎌

- `аниме про школу романтика`
- `Наруто`
- `топ аниме 2026`
- `манга Берсерк`

Результаты с **Shikimori.one**: рейтинг, количество серий, статус, описание.

### Поиск фильмов 🎬

- `фильм Дюна`
- `сериал Игра престолов`
- `Достучаться до небес смотреть`

Источник: **Кинопоиск** — год, режиссёр, рейтинг, описание.

### Универсальный поиск 🔍

Пишите что угодно — бот сам определит категорию:
- `как приготовить борщ`
- `погода в Москве`
- `новости технологий`

Используется **Яндекс** + **DuckDuckGo** + AI-анализ.

---

## 🔧 Админ-панель

Команда `/admin` доступна только пользователю с `ADMIN_ID`.

| Функция | Описание |
|---------|----------|
| 📢 **Рассылка** | Массовая отправка сообщения всем пользователям |
| 📊 **Статистика** | Количество пользователей, запросов, топ-3 активных |
| 🧠 **Промпт** | Изменение системного промпта AI на лету |
| 🔌 **Провайдеры** | Включение/выключение источников поиска |
| 📋 **Логи** | История последних 20 запросов |

---

## 🔌 Провайдеры

Все провайдеры можно включать/выключать через `/admin` → **Провайдеры**:

| Провайдер | Иконка | Тип поиска | Требует API-ключ |
|-----------|--------|-----------|------------------|
| Яндекс | 🟡 | Веб | Нет |
| DuckDuckGo | 🦆 | Веб | Нет |
| VK Music | 🔵 | Музыка | Опционально |
| Shikimori | 🎌 | Аниме | Нет |
| Last.fm | 🎸 | Музыка | Опционально |
| Кинопоиск | 🎬 | Фильмы | Нет |
| Яндекс.Музыка | 🎶 | Музыка | Нет |

---

## 🏗 Архитектура

```
Пользователь → Telegram → Bot Handler
                    ↓
            Pipeline (поток)
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
  LLM.analyze()  SearchAggregator  LLM.verify()
  (понимание     (параллельный     (оценка
   запроса)       поиск)            релевантности)
    ↓               ↓               ↓
  search_queries  all_results     best_sources
    └───────────────┴───────────────┘
                    ↓
            LLM.generate()
            (красивый ответ)
                    ↓
            Пользователь ✅
```

**Ключевые особенности:**
- **Потокобезопасность:** JSON-файлы защищены `threading.Lock`
- **Параллельный поиск:** `ThreadPoolExecutor` для одновременного опроса провайдеров
- **Кэш:** Результаты кэшируются на 1 час (`CACHE_TTL = 3600`)
- **Fallback:** Если LLM недоступен — показываются сырые результаты поиска
- **Retry:** LLM делает до 3 попыток при ошибках 429/500/502/503

---

## ❓ FAQ / Troubleshooting

### Бот не отвечает / пишет "Что-то пошло не так"

1. Проверьте `BOT_TOKEN` — должен быть актуальным.
2. Проверьте `OPENROUTER_API_KEY` — ключ должен быть рабочим.
3. Посмотрите логи в консоли Termux/терминала.

### DeprecationWarning: datetime.datetime.utcnow()

Это предупреждение, не ошибка. Бот работает нормально. В будущих версиях будет исправлено.

### "Поиск не дал результатов"

- Попробуйте переформулировать запрос
- Проверьте, включены ли провайдеры в `/admin`
- Убедитесь, что устройство имеет доступ в интернет

### Как узнать свой Telegram ID?

Напишите боту [@userinfobot](https://t.me/userinfobot) — он пришлёт ваш ID.

### Можно ли запустить на VPS / хостинге?

Да! Установите Python 3.9+, поставьте зависимости и запустите. Рекомендуется использовать `screen` или `systemd`:

```bash
# screen
screen -S bot
python bot.py
# Ctrl+A, D — отключиться

# systemd (создайте /etc/systemd/system/bot.service)
[Unit]
Description=Universal Search Bot
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/bot
ExecStart=/usr/bin/python3 /opt/bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Как сменить модель AI?

Замените `LLM_MODEL` на любую из списка [openrouter.ai/docs#models](https://openrouter.ai/docs#models). Примеры:
- `google/gemma-4-26b-a4b-it:free` — бесплатная
- `anthropic/claude-3.5-sonnet` — мощная
- `openai/gpt-4o-mini` — быстрая

---

## 📁 Структура проекта

```
universal-search-bot/
├── bot.py              # Основной файл бота
├── users.json          # База пользователей (авто-создание)
├── logs.json           # Логи запросов (авто-создание)
├── prompt_config.json  # Системный промпт (авто-создание)
├── providers_config.json # Настройки провайдеров (авто-создание)
├── README.md           # Этот файл
└── LICENSE             # Лицензия MIT
```

---

## 🤝 Контрибьютинг

Pull requests приветствуются! Особенно ценятся:
- Новые провайдеры поиска
- Улучшение парсеров
- Оптимизация для Termux
- Перевод README на другие языки

---

## 📜 Лицензия

Распространяется под лицензией **MIT**.

```
Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 🙏 Благодарности

- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) — обёртка для Telegram Bot API
- [OpenRouter](https://openrouter.ai) — унифицированный доступ к LLM
- [Shikimori](https://shikimori.one) — лучшая русскоязычная база аниме
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) — парсинг HTML

---

> **Made with ❤️ for Russian-speaking users.**
> 
> Если бот помог вам — поставьте ⭐ на GitHub!
