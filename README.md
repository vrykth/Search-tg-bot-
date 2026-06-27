# Search TG Bot

> **Прототип** универсального поискового Telegram-бота с AI-анализом.  
> Можно брать в основу для своих проектов. Оптимизирован для Termux и российских сервисов.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Linux%20%7C%20Windows-orange)](https://termux.dev)

---

## 📋 Содержание

- [О проекте](#-о-проекте)
- [Возможности](#-возможности)
- [Установка](#-установка)
- [Настройка](#-настройка)
- [Запуск](#-запуск)
- [Использование](#-использование)
- [Админ-панель](#-админ-панель)
- [Архитектура](#-архитектура)
- [FAQ](#-faq)
- [Лицензия](#-лицензия)

---

## 🧩 О проекте

Этот репозиторий — **прототип** (MVP), демонстрирующий концепцию поискового Telegram-бота с использованием LLM для анализа запросов и генерации ответов.

**Что внутри:**
- Маршрутизация запросов по категориям (музыка, аниме, фильмы, общий поиск)
- Параллельный scraping Яндекса, Кинопоиска, Shikimori, VK, DuckDuckGo
- Интеграция LLM через OpenRouter (без тяжёлой библиотеки `openai` — только `requests`)
- Админ-панель со статистикой, логами, рассылкой и управлением провайдерами
- JSON-файлы как лёгкая замена БД (подходит для прототипов и малой нагрузки)

**Автор:** [Vrykth](https://github.com/vrykth)  
**Статус:** Прототип / Proof of Concept — можно форкать и развивать.

---

## ✨ Возможности

| Категория | Источники |
|-----------|-----------|
| 🎵 Музыка | Яндекс.Музыка, VK Music, Last.fm |
| 🎌 Аниме | Shikimori.one (API + web) |
| 🎬 Фильмы | Кинопоиск (scraping) |
| 🔍 Общий поиск | Яндекс, DuckDuckGo |
| 🤖 AI | OpenRouter (любая модель: Gemma, Claude, GPT и др.) |

**Дополнительно:**
- Автоопределение категории по ключевым словам
- Кэш результатов в памяти (1 час)
- Логирование запросов и статистика пользователей
- Рассылка сообщений от администратора
- Включение/отключение провайдеров через inline-кнопки
- Работа без `openai`, `lxml`, `duckduckgo-search` — минимум зависимостей для Termux

---

## 🚀 Установка

### Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install python -y
pip install pyTelegramBotAPI requests beautifulsoup4

# Скачайте код
git clone https://github.com/vrykth/search-tg-bot.git
cd search-tg-bot
```

### Linux / macOS / Windows

```bash
# Клонирование
git clone https://github.com/vrykth/search-tg-bot.git
cd search-tg-bot

# Виртуальное окружение (рекомендуется)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

pip install pyTelegramBotAPI requests beautifulsoup4
```

---

## ⚙️ Настройка

Откройте `bot.py` и заполните константы в начале файла:

```python
BOT_TOKEN           = "1234567890:ABC...XYZ"      # Токен от @BotFather
ADMIN_ID            = 1234567890                  # Ваш Telegram user_id (число)

OPENROUTER_API_KEY  = "sk-or-v1-..."              # Ключ с openrouter.ai
LLM_MODEL           = "google/gemma-4-26b-a4b-it:free"
LLM_BASE_URL        = "https://openrouter.ai/api/v1"

# Опционально:
VK_ACCESS_TOKEN     = ""   # Для VK API (если есть)
LASTFM_API_KEY      = ""   # Для Last.fm API (если есть)
```

### Где взять ключи

| Сервис | Ссылка | Примечание |
|--------|--------|------------|
| Telegram Bot Token | [@BotFather](https://t.me/BotFather) | Бесплатно |
| OpenRouter API Key | [openrouter.ai/keys](https://openrouter.ai/keys) | Есть бесплатные модели |
| VK Access Token | [vk.com/dev](https://vk.com/dev/access_token) | Опционально |
| Last.fm API Key | [last.fm/api](https://www.last.fm/api/account/create) | Опционально |

> Для работы достаточно **только** `BOT_TOKEN` и `OPENROUTER_API_KEY`.  
> VK и Last.fm — улучшат поиск музыки, но не обязательны.

---

## ▶️ Запуск

```bash
python bot.py
```

При успешном запуске:
```
============================================================
  🤖 SEARCH TG BOT — PROTOTYPE
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

### Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и список возможностей |
| `/help` | Справка |
| `/search <запрос>` | Явный поиск |
| `/admin` | Панель администратора (только для `ADMIN_ID`) |

### Примеры запросов

**Музыка:**
```
трек Монеточка — Каждый раз
альбом Земфира
песня ДДТ Что такое осень
```

**Аниме:**
```
аниме про школу романтика
Наруто серии
топ аниме 2024
```

**Фильмы:**
```
фильм Дюна
сериал Игра престолов
Достучаться до небес
```

**Универсальный поиск:**
```
как приготовить борщ
погода в Москве
новости технологий
```

Бот автоматически определяет категорию, ищет через подходящие провайдеры, анализирует результаты через LLM и отправляет структурированный ответ.

---

## 🔧 Админ-панель

Команда `/admin` доступна только владельцу (`ADMIN_ID`).

| Функция | Описание |
|---------|----------|
| 📢 Рассылка | Отправить сообщение всем пользователям бота |
| 📊 Статистика | Пользователи, запросы, топ-3 по активности |
| 🧠 Промпт | Изменить системный промпт LLM |
| 🔌 Провайдеры | Включить/выключить источники поиска |
| 📋 Логи | Последние 20 запросов с пагинацией |

---

## 🏗 Архитектура

```
Пользователь
    ↓
Telegram Bot API (pyTelegramBotAPI, threaded)
    ↓
Handler → Pipeline (отдельный поток)
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
↓                 ↓                 ↓
LLM.analyze()   SearchAggregator  LLM.verify()
(интент,        (параллельный     (оценка релевантности
запросы)        scraping)         источников)
    └─────────────────┴─────────────────┘
                      ↓
              LLM.generate()
              (структурированный ответ)
                      ↓
              Пользователь
```

**Технические детали:**
- **Потокобезопасность:** все операции с JSON защищены `threading.Lock`
- **Параллелизм:** `ThreadPoolExecutor` для одновременного опроса провайдеров
- **Кэш:** in-memory dict с TTL 3600 секунд
- **Fallback:** при недоступности LLM — вывод сырых результатов поиска
- **Retry:** до 3 попыток при ошибках сети/рейтлимита LLM
- **Без зависимостей:** не требует `openai`, `lxml`, `duckduckgo-search`

---

## ❓ FAQ

### Бот не отвечает
- Проверьте `BOT_TOKEN` (должен быть актуальным)
- Проверьте `OPENROUTER_API_KEY`
- Убедитесь, что устройство онлайн

### DeprecationWarning: datetime.utcnow()
Это предупреждение Python 3.12+. На работу бота не влияет, будет исправлено в следующей версии.

### "Поиск не дал результатов"
- Переформулируйте запрос
- Проверьте, включены ли провайдеры в `/admin`

### Как узнать свой Telegram ID?
Напишите [@userinfobot](https://t.me/userinfobot).

### Можно ли запускать на VPS?
Да. Рекомендуется `systemd` или `screen`:

```bash
# systemd
sudo nano /etc/systemd/system/search-bot.service
```

```ini
[Unit]
Description=Search TG Bot
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/search-tg-bot
ExecStart=/usr/bin/python3 /opt/search-tg-bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable search-bot
sudo systemctl start search-bot
```

### Как сменить модель LLM?
Замените `LLM_MODEL` на любую из [openrouter.ai/docs#models](https://openrouter.ai/docs#models):
- `google/gemma-4-26b-a4b-it:free` — бесплатная
- `anthropic/claude-3.5-sonnet` — мощная
- `openai/gpt-4o-mini` — быстрая и дешевая

---

## 📁 Структура проекта

```
search-tg-bot/
├── bot.py                 # Основной файл
├── users.json             # Пользователи (авто-создание)
├── logs.json              # Логи (авто-создание)
├── prompt_config.json     # Промпт LLM (авто-создание)
├── providers_config.json  # Провайдеры (авто-создание)
├── README.md
└── LICENSE
```

> **Примечание:** JSON-файлы используются как упрощённая БД для прототипа.  
> Для продакшена рекомендуется заменить на SQLite/PostgreSQL.

---

## 🛣 Дорожная карта (идеи для развития)

- [ ] Заменить JSON на SQLite
- [ ] Добавить кэш Redis
- [ ] Webhook-режим (для VPS)
- [ ] Поддержка изображений (постеры аниме/фильмов)
- [ ] Inline-режим (@botname запрос)
- [ ] Подписка на обновления аниме
- [ ] Docker-контейнер
- [ ] CI/CD через GitHub Actions

---

## 🤝 Контрибьютинг

Это open-source прототип. Pull requests приветствуются:
- Новые провайдеры поиска
- Улучшение парсеров (Яндекс, Кинопоиск часто меняют вёрстку)
- Оптимизация под Termux
- Переводы документации

---

## 📜 Лицензия

MIT License — 2026

```
Copyright (c) 2026 Vrykth

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

> **Прототип создан как база для развития.**  
> Форкайте, улучшайте, адаптируйте под свои задачи.  
> Автор: [github.com/vrykth](https://github.com/vrykth)
