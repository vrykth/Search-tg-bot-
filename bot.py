BOT_TOKEN           = "Вставьте ваш токен бота"
ADMIN_ID            = 0000000000 # замените на ваш id

OPENROUTER_API_KEY  = "Ключ от провайдера"
LLM_MODEL           = "google/gemma-4-26b-a4b-it:free"
LLM_BASE_URL        = "https://openrouter.ai/api/v1"

VK_ACCESS_TOKEN     = "" #Можно оставить пустым
LASTFM_API_KEY      = "" #Можно оставить пустым

# =============================================================================
#  ИМПОРТЫ
# =============================================================================

import telebot
import threading
import time
import json
import os
import re
import logging
import hashlib
import urllib.parse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# =============================================================================
#  КОНСТАНТЫ
# =============================================================================

CACHE_TTL           = 3600
MAX_SEARCH_RESULTS  = 30
MAX_PARSE_PAGES     = 10
RELEVANCE_THRESHOLD = 6
MAX_SEARCH_ITERS    = 3

USERS_FILE          = "users.json"
LOGS_FILE           = "logs.json"
PROMPT_FILE         = "prompt_config.json"
PROVIDERS_FILE      = "providers_config.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

YANDEX_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://yandex.ru/",
}

DEFAULT_SYSTEM_PROMPT = (
    "Ты — универсальный русскоязычный поисковый ассистент. "
    "Ты помогаешь искать музыку, аниме, треки, фильмы, книги и любую другую информацию. "
    "Работаешь в России, знаешь российские сервисы (Яндекс, VK, Кинопоиск, Shikimori). "
    "Отвечаешь только на русском языке. Структурируй ответы красиво с эмодзи."
)

CATEGORIES = {
    "music":     "🎵",
    "anime":     "🎌",
    "movie":     "🎬",
    "book":      "📚",
    "news":      "📰",
    "person":    "👤",
    "game":      "🎮",
    "general":   "🔍",
}

CATEGORY_KEYWORDS = {
    "music":  ["музыка", "трек", "песня", "исполнитель", "альбом", "слушать", "song", "music", "track", "playlist", "плейлист"],
    "anime":  ["аниме", "манга", "anime", "manga", "сезон", "серия", "опенинг", "эндинг", "shikimori", "мангака"],
    "movie":  ["фильм", "сериал", "кино", "смотреть", "movie", "film", "series", "кинопоиск", "режиссёр"],
    "book":   ["книга", "автор", "читать", "роман", "повесть", "book", "author", "литература"],
    "game":   ["игра", "game", "геймплей", "стим", "steam", "playstation", "xbox", "nintendo"],
    "news":   ["новости", "news", "событие", "сегодня", "вчера", "произошло"],
}

admin_states: Dict[int, str] = {}

# =============================================================================
#  УТИЛИТЫ
# =============================================================================

def escape_md(text: str) -> str:
    if not text:
        return ""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


def detect_category(query: str) -> str:
    q_lower = query.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in q_lower for kw in keywords):
            return cat
    return "general"


def truncate(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    return text[:max_len] + ("..." if len(text) > max_len else "")


# =============================================================================
#  КЭШИРОВАНИЕ
# =============================================================================

_cache: Dict[str, Dict] = {}
_cache_lock = threading.Lock()


def cache_key(query: str, category: str) -> str:
    return hashlib.md5(f"{category}:{query}".encode()).hexdigest()


def cache_get(key: str) -> Optional[List]:
    with _cache_lock:
        e = _cache.get(key)
        if e and time.time() - e["ts"] < CACHE_TTL:
            return e["data"]
    return None


def cache_set(key: str, data: List):
    with _cache_lock:
        _cache[key] = {"ts": time.time(), "data": data}


# =============================================================================
#  БАЗА ДАННЫХ (JSON)
# =============================================================================

class DB:
    _lock = threading.Lock()

    @staticmethod
    def read(path: str, default):
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    @classmethod
    def write(cls, path: str, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def upsert_user(cls, uid: int, username: str, first_name: str):
        with cls._lock:
            users = cls.read(USERS_FILE, {})
            key = str(uid)
            now = datetime.utcnow().isoformat()
            if key not in users:
                users[key] = {
                    "user_id": uid, "username": username or "",
                    "first_name": first_name or "", "join_date": now,
                    "requests_count": 0, "last_activity": now,
                    "favorite_category": "general",
                }
            else:
                users[key].update({
                    "username": username or users[key]["username"],
                    "first_name": first_name or users[key]["first_name"],
                    "last_activity": now,
                })
            cls.write(USERS_FILE, users)

    @classmethod
    def inc_requests(cls, uid: int, category: str = "general"):
        with cls._lock:
            users = cls.read(USERS_FILE, {})
            key = str(uid)
            if key in users:
                users[key]["requests_count"] = users[key].get("requests_count", 0) + 1
                users[key]["last_activity"] = datetime.utcnow().isoformat()
                users[key]["favorite_category"] = category
                cls.write(USERS_FILE, users)

    @classmethod
    def get_users(cls) -> dict:
        return cls.read(USERS_FILE, {})

    @classmethod
    def add_log(cls, uid: int, query: str, category: str, sources: int, status: str):
        with cls._lock:
            logs = cls.read(LOGS_FILE, [])
            logs.append({
                "ts": datetime.utcnow().isoformat(),
                "uid": uid, "query": query[:150],
                "category": category, "sources": sources, "status": status,
            })
            logs = logs[-100:]
            cls.write(LOGS_FILE, logs)

    @classmethod
    def get_logs(cls, limit: int = 20) -> list:
        return cls.read(LOGS_FILE, [])[-limit:]

    @classmethod
    def get_system_prompt(cls) -> str:
        cfg = cls.read(PROMPT_FILE, {})
        return cfg.get("prompt", DEFAULT_SYSTEM_PROMPT)

    @classmethod
    def set_system_prompt(cls, text: str):
        with cls._lock:
            cls.write(PROMPT_FILE, {"prompt": text})

    @classmethod
    def get_providers(cls) -> dict:
        default = {
            "yandex": True, "duckduckgo": True,
            "vk": True, "shikimori": True, "lastfm": True,
        }
        return cls.read(PROVIDERS_FILE, default)

    @classmethod
    def toggle_provider(cls, name: str) -> bool:
        with cls._lock:
            cfg = cls.get_providers()
            cfg[name] = not cfg.get(name, True)
            cls.write(PROVIDERS_FILE, cfg)
            return cfg[name]

    @classmethod
    def stats(cls) -> dict:
        users = cls.get_users()
        day_ago = (datetime.utcnow() - timedelta(days=1)).isoformat()
        total_req = sum(u.get("requests_count", 0) for u in users.values())
        active_today = sum(1 for u in users.values() if u.get("last_activity", "") >= day_ago)
        top3 = sorted(users.values(), key=lambda u: u.get("requests_count", 0), reverse=True)[:3]
        return {
            "total_users": len(users),
            "total_requests": total_req,
            "active_today": active_today,
            "top3": top3,
        }


# =============================================================================
#  ПОИСКОВЫЕ ПРОВАЙДЕРЫ
# =============================================================================

class YandexSearch:
    @staticmethod
    def search(query: str, max_results: int = 15) -> List[Dict]:
        results = []
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://yandex.ru/search/?text={encoded}&lr=213"
            resp = requests.get(url, headers=YANDEX_HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            items = soup.select("li.serp-item, div.OrganicResult, div[data-cid]")
            for item in items[:max_results]:
                title_el = item.select_one("h2 a, .OrganicTitle-LinkText, a[class*='Title']")
                snippet_el = item.select_one(".OrganicText, .TextContainer, span[class*='green']")
                link_el = item.select_one("a[href^='http']")

                title = title_el.get_text(strip=True) if title_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                href = link_el.get("href", "") if link_el else ""

                if href and "yandex.ru/clck" not in href and title:
                    results.append({
                        "title": title, "url": href,
                        "snippet": snippet, "source": "yandex"
                    })
            time.sleep(0.5)
        except Exception as e:
            logger.warning("Yandex search error: %s", e)
        return results


class DDGSearch:
    """DuckDuckGo через HTML-версию (без сторонних библиотек)."""

    @staticmethod
    def search(query: str, max_results: int = 15) -> List[Dict]:
        results = []
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            items = soup.select(".result__body")
            for item in items[:max_results]:
                title_el = item.select_one(".result__a")
                snippet_el = item.select_one(".result__snippet")
                if title_el:
                    href = title_el.get("href", "")
                    # DDG иногда даёт редирект-ссылки
                    if href.startswith("//"):
                        href = "https:" + href
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "url": href,
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        "source": "duckduckgo",
                    })
            time.sleep(0.3)
        except Exception as e:
            logger.warning("DDG error: %s", e)
        return results


class ShikimoriSearch:
    BASE = "https://shikimori.one"

    @classmethod
    def search(cls, query: str, max_results: int = 10) -> List[Dict]:
        results = []
        try:
            encoded = urllib.parse.quote(query)
            # Сразу пробуем API — надёжнее
            api_url = f"{cls.BASE}/api/animes?search={encoded}&limit={max_results}&order=popularity"
            api_resp = requests.get(api_url, headers=HEADERS, timeout=15)
            if api_resp.status_code == 200:
                data = api_resp.json()
                for item in data:
                    name = item.get("russian") or item.get("name", "")
                    anime_id = item.get("id", "")
                    kind = item.get("kind", "")
                    score = item.get("score", "?")
                    episodes = item.get("episodes", "?")
                    status = item.get("status", "")
                    results.append({
                        "title": f"{name} ({kind.upper()}, {episodes} эп., ★{score})",
                        "url": f"{cls.BASE}/animes/{anime_id}",
                        "snippet": f"Статус: {status} | Рейтинг: {score}/10",
                        "source": "shikimori",
                        "extra": {
                            "name": name, "kind": kind, "score": score,
                            "episodes": episodes, "status": status,
                            "image": cls.BASE + (item.get("image", {}).get("preview") or ""),
                        }
                    })
            time.sleep(0.3)
        except Exception as e:
            logger.warning("Shikimori error: %s", e)
        return results


class VKMusicSearch:
    @staticmethod
    def search(query: str, max_results: int = 10) -> List[Dict]:
        results = []
        if VK_ACCESS_TOKEN:
            try:
                url = "https://api.vk.com/method/audio.search"
                params = {
                    "q": query, "count": max_results,
                    "access_token": VK_ACCESS_TOKEN, "v": "5.131"
                }
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                data = resp.json()
                items = data.get("response", {}).get("items", [])
                for item in items:
                    artist = item.get("artist", "")
                    title = item.get("title", "")
                    duration = item.get("duration", 0)
                    dur_str = f"{duration // 60}:{duration % 60:02d}"
                    results.append({
                        "title": f"{artist} — {title} [{dur_str}]",
                        "url": f"https://vk.com/search?c[q]={urllib.parse.quote(artist+' '+title)}&c[section]=audio",
                        "snippet": f"Длительность: {dur_str}",
                        "source": "vk_music",
                        "extra": {"artist": artist, "track": title, "duration": dur_str}
                    })
                time.sleep(0.3)
                return results
            except Exception as e:
                logger.warning("VK API error: %s", e)

        # Fallback — веб
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://vk.com/search?c%5Bq%5D={encoded}&c%5Bsection%5D=audio"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("div.audio_item, .AudioRow")
            for item in items[:max_results]:
                title_el = item.select_one(".audio_title, .AudioRow__title")
                artist_el = item.select_one(".audio_artist, .AudioRow__artist")
                title = title_el.get_text(strip=True) if title_el else ""
                artist = artist_el.get_text(strip=True) if artist_el else ""
                if title:
                    results.append({
                        "title": f"{artist} — {title}" if artist else title,
                        "url": url,
                        "snippet": "VK Music",
                        "source": "vk_music",
                    })
            time.sleep(0.5)
        except Exception as e:
            logger.warning("VK scraping error: %s", e)
        return results


class YandexMusicSearch:
    @staticmethod
    def search(query: str, max_results: int = 10) -> List[Dict]:
        results = []
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://music.yandex.ru/search?text={encoded}"
            resp = requests.get(url, headers=YANDEX_HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            items = soup.select("div.d-track, .Track, article[class*='track']")
            for item in items[:max_results]:
                title_el = item.select_one(".d-track__name, .Track__title, [class*='name']")
                artist_el = item.select_one(".d-track__artists, .Track__artist, [class*='artist']")
                title = title_el.get_text(strip=True) if title_el else ""
                artist = artist_el.get_text(strip=True) if artist_el else ""
                if title:
                    search_url = f"https://music.yandex.ru/search?text={encoded}"
                    results.append({
                        "title": f"🎵 {artist} — {title}" if artist else f"🎵 {title}",
                        "url": search_url,
                        "snippet": "Найдено на Яндекс.Музыке",
                        "source": "yandex_music",
                        "extra": {"artist": artist, "track": title}
                    })

            if not results:
                results.append({
                    "title": f"🎵 Поиск '{query}' на Яндекс.Музыке",
                    "url": f"https://music.yandex.ru/search?text={encoded}",
                    "snippet": "Нажмите для прослушивания на Яндекс.Музыке",
                    "source": "yandex_music",
                })
            time.sleep(0.3)
        except Exception as e:
            logger.warning("Yandex Music error: %s", e)
        return results


class LastFmSearch:
    @staticmethod
    def search(query: str, max_results: int = 10) -> List[Dict]:
        if not LASTFM_API_KEY:
            return []
        results = []
        try:
            url = "https://ws.audioscrobbler.com/2.0/"
            params = {
                "method": "track.search", "track": query,
                "api_key": LASTFM_API_KEY, "format": "json", "limit": max_results,
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            data = resp.json()
            tracks = data.get("results", {}).get("trackmatches", {}).get("track", [])
            for t in tracks:
                artist = t.get("artist", "")
                name = t.get("name", "")
                listeners = t.get("listeners", "")
                lastfm_url = t.get("url", "")
                results.append({
                    "title": f"🎵 {artist} — {name}",
                    "url": lastfm_url,
                    "snippet": f"Слушателей: {listeners}",
                    "source": "lastfm",
                    "extra": {"artist": artist, "track": name}
                })
            time.sleep(0.3)
        except Exception as e:
            logger.warning("Last.fm error: %s", e)
        return results


class KinopoiskSearch:
    @staticmethod
    def search(query: str, max_results: int = 10) -> List[Dict]:
        results = []
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://www.kinopoisk.ru/index.php?kp_query={encoded}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            items = soup.select("div.element, .film-item, .search_results .name")
            for item in items[:max_results]:
                name_el = item.select_one(".name a, p.name a, a.name")
                year_el = item.select_one(".year, .info .year")
                rating_el = item.select_one(".rating, .kp-rating")
                desc_el = item.select_one(".info, .desc")

                if not name_el:
                    continue
                title = name_el.get_text(strip=True)
                href = name_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.kinopoisk.ru" + href
                year = year_el.get_text(strip=True) if year_el else ""
                rating = rating_el.get_text(strip=True) if rating_el else ""
                desc = desc_el.get_text(strip=True)[:150] if desc_el else ""

                results.append({
                    "title": f"🎬 {title} ({year}) ★{rating}",
                    "url": href,
                    "snippet": desc,
                    "source": "kinopoisk",
                })
            time.sleep(0.5)
        except Exception as e:
            logger.warning("Kinopoisk error: %s", e)
        return results


class PageParser:
    @staticmethod
    def parse(url: str) -> Dict:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            h1 = soup.find("h1")
            h1_text = h1.get_text(strip=True) if h1 else ""

            meta = soup.find("meta", attrs={"name": "description"})
            meta_desc = meta.get("content", "") if meta else ""

            paras = [
                p.get_text(strip=True)
                for p in soup.find_all("p")
                if len(p.get_text(strip=True)) > 50
            ]
            para_text = " ".join(paras[:3])[:600]

            return {"h1": h1_text, "meta": meta_desc, "text": para_text}
        except Exception:
            return {}


# =============================================================================
#  АГРЕГАТОР ПОИСКА
# =============================================================================

class SearchAggregator:
    def __init__(self):
        self.providers = DB.get_providers()

    def refresh(self):
        self.providers = DB.get_providers()

    def _dedup(self, results: List[Dict]) -> List[Dict]:
        seen = set()
        out = []
        for r in results:
            url = r.get("url", "").strip().rstrip("/")
            if url and url not in seen:
                seen.add(url)
                out.append(r)
        return out

    def _score(self, r: Dict, query: str) -> float:
        text = (r.get("title", "") + " " + r.get("snippet", "")).lower()
        words = [w for w in query.lower().split() if len(w) > 2]
        return sum(1.0 for w in words if w in text)

    def search(self, query: str, category: str = "general") -> List[Dict]:
        self.refresh()
        key = cache_key(query, category)
        cached = cache_get(key)
        if cached:
            logger.info("Cache hit: %s / %s", category, query[:30])
            return cached

        all_results = []
        tasks = []

        with ThreadPoolExecutor(max_workers=8) as pool:
            if category == "anime":
                if self.providers.get("shikimori", True):
                    tasks.append(pool.submit(ShikimoriSearch.search, query, 15))
                if self.providers.get("yandex", True):
                    tasks.append(pool.submit(YandexSearch.search, f"{query} аниме", 10))

            elif category == "music":
                if self.providers.get("vk", True):
                    tasks.append(pool.submit(VKMusicSearch.search, query, 10))
                tasks.append(pool.submit(YandexMusicSearch.search, query, 10))
                if self.providers.get("lastfm", True) and LASTFM_API_KEY:
                    tasks.append(pool.submit(LastFmSearch.search, query, 10))
                if self.providers.get("yandex", True):
                    tasks.append(pool.submit(YandexSearch.search, f"{query} слушать онлайн", 8))

            elif category == "movie":
                tasks.append(pool.submit(KinopoiskSearch.search, query, 10))
                if self.providers.get("yandex", True):
                    tasks.append(pool.submit(YandexSearch.search, f"{query} фильм смотреть", 10))

            else:
                if self.providers.get("yandex", True):
                    tasks.append(pool.submit(YandexSearch.search, query, 20))
                if self.providers.get("duckduckgo", True):
                    tasks.append(pool.submit(DDGSearch.search, query, 15))

            if category not in ("anime", "music", "movie") and self.providers.get("yandex", True):
                tasks.append(pool.submit(YandexSearch.search, query, 15))

            for future in as_completed(tasks):
                try:
                    all_results.extend(future.result())
                except Exception as e:
                    logger.warning("Search task failed: %s", e)

        if not all_results:
            logger.info("All providers failed, DDG fallback")
            all_results = DDGSearch.search(query, 20)

        unique = self._dedup(all_results)
        scored = sorted(unique, key=lambda r: self._score(r, query), reverse=True)
        top = scored[:MAX_SEARCH_RESULTS]

        if category not in ("music",) and len(top) > 0:
            parse_targets = [r for r in top[:MAX_PARSE_PAGES] if "shikimori" not in r.get("source", "")]
            with ThreadPoolExecutor(max_workers=5) as pool:
                pfutures = {pool.submit(PageParser.parse, r["url"]): i for i, r in enumerate(parse_targets)}
                for pf in as_completed(pfutures):
                    idx = pfutures[pf]
                    try:
                        parse_targets[idx]["page_content"] = pf.result()
                    except Exception:
                        parse_targets[idx]["page_content"] = {}

        cache_set(key, top)
        return top


# =============================================================================
#  LLM КЛИЕНТ (через requests, без openai)
# =============================================================================

class LLM:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/",
            "X-Title": "UniversalSearchBot",
        }

    def _call(self, messages: List[Dict], max_tokens: int = 1500) -> Optional[str]:
        delays = [1, 2, 4]
        for i, delay in enumerate(delays):
            try:
                resp = requests.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": LLM_MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                    },
                    timeout=60,
                )
                if resp.status_code != 200:
                    err = resp.text[:200]
                    if any(code in err for code in ["429", "500", "502", "503"]):
                        logger.warning("LLM rate limit attempt %d: %s", i + 1, err)
                        if i < len(delays) - 1:
                            time.sleep(delay)
                            continue
                    logger.error("LLM HTTP error %s: %s", resp.status_code, err)
                    return None
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.error("LLM error: %s", e)
                return None
        return None

    def analyze(self, query: str, category: str) -> Optional[Dict]:
        sys_prompt = DB.get_system_prompt()
        cat_icon = CATEGORIES.get(category, "🔍")
        prompt = f"""Пользователь из России написал запрос в категории {cat_icon} {category}:
"{query}"

Задача:
1. Пойми истинную потребность пользователя.
2. Создай 3-5 поисковых запросов для максимального охвата.
3. Кратко опиши что ищет пользователь.

Ответ СТРОГО в JSON (без markdown):
{{"intent": "описание потребности", "queries": ["запрос1", "запрос2", "запрос3"], "category_hint": "{category}"}}"""

        raw = self._call([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ], max_tokens=500)
        if not raw:
            return None
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(clean)
        except Exception:
            return {"intent": query, "queries": [query], "category_hint": category}

    def verify(self, query: str, sources: List[Dict], category: str) -> Optional[Dict]:
        sys_prompt = DB.get_system_prompt()
        cat_icon = CATEGORIES.get(category, "🔍")
        src_text = "\n".join(
            f"[{i+1}] {s.get('title','')} | {s.get('snippet','')[:120]}"
            for i, s in enumerate(sources[:25])
        )
        prompt = f"""Запрос пользователя (категория {cat_icon} {category}): "{query}"

Источники:
{src_text}

Оцени релевантность каждого источника от 1 до 10.
Учитывай: российские источники предпочтительны.

Ответ в JSON (без markdown):
{{"scores": [8, 5, 9], "avg": 7.5, "note": "комментарий"}}"""

        raw = self._call([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ], max_tokens=600)
        if not raw:
            return None
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(clean)
        except Exception:
            return {"scores": [], "avg": 5.0, "note": raw[:150]}

    def generate(self, query: str, sources: List[Dict], category: str) -> Optional[str]:
        sys_prompt = DB.get_system_prompt()
        cat_icon = CATEGORIES.get(category, "🔍")

        src_text = "\n".join(
            f"[{i+1}] {s.get('title','')} ({s.get('url','')})\n"
            f"    {s.get('snippet','')[:180]}\n"
            f"    {s.get('page_content', {}).get('text', '')[:200]}"
            for i, s in enumerate(sources[:12])
        )

        category_instructions = {
            "music": "Укажи: исполнителя, название трека/альбома, где слушать в России. Если трек — покажи длительность.",
            "anime": "Укажи: название (рус/яп), жанр, количество серий, рейтинг на Shikimori, краткое описание. Дай ссылку на Shikimori.",
            "movie": "Укажи: год выхода, режиссёра, рейтинг Кинопоиска/IMDb, краткое описание. Дай ссылку на Кинопоиск.",
            "general": "Дай максимально полный и структурированный ответ.",
        }
        extra_instruction = category_instructions.get(category, category_instructions["general"])

        prompt = f"""Запрос: "{query}" (категория: {cat_icon} {category})

Найденные источники:
{src_text}

Создай красивый структурированный ответ на русском языке.
{extra_instruction}

Формат ответа (используй Markdown):
**{cat_icon} [Краткий заголовок]**

✅ **Что найдено:**
[основные факты, прямые ответы на запрос]

⚠️ **Нюансы / что учесть:**
[важные детали, ограничения, альтернативы]

🔗 **Источники:**
1. [Название](ссылка) — пояснение
2. [Название](ссылка) — пояснение

💡 **Совет:**
[рекомендация пользователю]"""

        return self._call([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ], max_tokens=2000)

    def refine_queries(self, original: str, prev_queries: List[str], note: str) -> List[str]:
        raw = self._call([{
            "role": "user",
            "content": f"""Запрос: "{original}"
Предыдущие запросы: {prev_queries}
Проблема: {note}
Придумай 3 новых, более точных поисковых запроса для российских сервисов.
JSON без markdown: {{"queries": ["запрос1", "запрос2", "запрос3"]}}"""
        }], max_tokens=300)
        if not raw:
            return prev_queries
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(clean).get("queries", prev_queries)
        except Exception:
            return prev_queries


# =============================================================================
#  PIPELINE
# =============================================================================

class Pipeline:
    def __init__(self, bot: telebot.TeleBot):
        self.bot = bot
        self.searcher = SearchAggregator()
        self.llm = LLM()

    def _action(self, chat_id: int, action: str):
        try:
            self.bot.send_chat_action(chat_id, action)
        except Exception:
            pass

    def _send(self, chat_id: int, text: str, **kwargs):
        chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
        for chunk in chunks:
            try:
                self.bot.send_message(chat_id, chunk, disable_web_page_preview=True, **kwargs)
            except Exception as e:
                logger.warning("Send error (%s), trying plain", e)
                try:
                    plain = re.sub(r'[\\*_\[\]()~`>#+=|{}.!\-]', '', chunk)
                    self.bot.send_message(chat_id, plain, disable_web_page_preview=True)
                except Exception as e2:
                    logger.error("Failed to send message: %s", e2)
            time.sleep(0.2)

    def _format_raw(self, query: str, category: str, sources: List[Dict]) -> str:
        icon = CATEGORIES.get(category, "🔍")
        lines = [
            f"{icon} **Результаты поиска:** {query}",
            "⚠️ _AI-анализ временно недоступен — показываю сырые результаты_\n"
        ]
        for i, s in enumerate(sources[:12], 1):
            title = s.get("title", "Без названия")
            url = s.get("url", "")
            snippet = s.get("snippet", "")[:150]
            src_icon = {"yandex": "🟡", "shikimori": "🎌", "vk_music": "🎵",
                       "yandex_music": "🎶", "kinopoisk": "🎬", "lastfm": "🎸"}.get(s.get("source",""), "🔗")
            lines.append(f"{src_icon} **{i}. [{title}]({url})**\n_{snippet}_\n")
        return "\n".join(lines)

    def run(self, chat_id: int, user_id: int, query: str):
        category = detect_category(query)
        icon = CATEGORIES.get(category, "🔍")
        status = "error"
        sources_count = 0

        try:
            # ЭТАП 1: АНАЛИЗ
            self._action(chat_id, "typing")
            self._send(chat_id,
                f"{icon} *Категория:* `{category}`\n"
                f"🧠 *Анализирую запрос\\.\\.\\.*",
                parse_mode="MarkdownV2"
            )

            analysis = self.llm.analyze(query, category)
            if analysis:
                search_queries = analysis.get("queries", [query])[:5]
                intent = analysis.get("intent", query)
                self._send(chat_id,
                    f"💡 *Понял:* _{escape_md(intent)}_\n"
                    f"🔎 Формирую {len(search_queries)} поисковых запросов\\.\\.\\.",
                    parse_mode="MarkdownV2"
                )
            else:
                search_queries = [query]
                intent = query

            # ЭТАПЫ 2-3: ПОИСК + ПРОВЕРКА
            best_sources = []
            iteration = 0

            while iteration < MAX_SEARCH_ITERS:
                iteration += 1
                self._action(chat_id, "find_location")
                self._send(chat_id,
                    f"🌐 *Итерация {iteration}/{MAX_SEARCH_ITERS}: ищу по {len(search_queries)} запросам\\.\\.\\.*",
                    parse_mode="MarkdownV2"
                )

                sources = self.searcher.search(search_queries[0], category)
                if len(search_queries) > 1:
                    with ThreadPoolExecutor(max_workers=4) as pool:
                        futures = [pool.submit(self.searcher.search, q, category) for q in search_queries[1:]]
                        for f in as_completed(futures):
                            try:
                                sources.extend(f.result())
                            except Exception:
                                pass

                seen = set()
                unique_sources = []
                for s in sources:
                    url = s.get("url", "")
                    if url not in seen:
                        seen.add(url)
                        unique_sources.append(s)
                sources = unique_sources

                sources_count = len(sources)

                if not sources:
                    self._send(chat_id, "❌ Поиск не дал результатов. Попробуйте уточнить запрос.")
                    DB.add_log(user_id, query, category, 0, "no_results")
                    return

                self._action(chat_id, "upload_document")
                self._send(chat_id,
                    f"✅ *Найдено {sources_count} источников\\.* Оцениваю качество\\.\\.\\.",
                    parse_mode="MarkdownV2"
                )

                verification = self.llm.verify(query, sources, category)

                if verification is None:
                    raw_msg = self._format_raw(query, category, sources)
                    self._send(chat_id, raw_msg, parse_mode="Markdown")
                    DB.add_log(user_id, query, category, sources_count, "llm_unavailable")
                    DB.inc_requests(user_id, category)
                    return

                avg = verification.get("avg", 5.0)
                note = verification.get("note", "")
                self._send(chat_id,
                    f"📊 *Релевантность:* {escape_md(str(round(avg, 1)))}/10 — _{escape_md(note[:80])}_",
                    parse_mode="MarkdownV2"
                )

                if avg >= RELEVANCE_THRESHOLD:
                    scores = verification.get("scores", [])
                    if scores:
                        paired = sorted(zip(scores, sources[:len(scores)]), key=lambda x: x[0], reverse=True)
                        best_sources = [s for _, s in paired[:20]]
                    else:
                        best_sources = sources[:20]
                    break
                else:
                    if iteration < MAX_SEARCH_ITERS:
                        self._send(chat_id,
                            "🔄 *Уточняю запросы для лучшего результата\\.\\.\\.*",
                            parse_mode="MarkdownV2"
                        )
                        search_queries = self.llm.refine_queries(query, search_queries, note)
                    else:
                        best_sources = sources[:20]
                        self._send(chat_id,
                            "⚠️ *После 3 попыток показываю лучшее из найденного\\.*",
                            parse_mode="MarkdownV2"
                        )

            # ЭТАП 4: ГЕНЕРАЦИЯ ОТВЕТА
            self._action(chat_id, "typing")
            self._send(chat_id, "✍️ *Готовлю ответ\\.\\.\\.*", parse_mode="MarkdownV2")

            answer = self.llm.generate(query, best_sources, category)

            if answer is None:
                raw_msg = self._format_raw(query, category, best_sources)
                self._send(chat_id, raw_msg, parse_mode="Markdown")
                DB.add_log(user_id, query, category, sources_count, "llm_unavailable")
                DB.inc_requests(user_id, category)
                return

            # ЭТАП 5: КРАСИВЫЙ ОТВЕТ
            divider = "━" * 28
            header = f"{icon} *Результат поиска*\n{escape_md(divider)}\n\n"
            footer = f"\n\n{escape_md(divider)}\n_Найдено источников: {sources_count} · /help_"

            full = header + escape_md(answer) + footer
            try:
                self._send(chat_id, full, parse_mode="MarkdownV2")
            except Exception:
                self._send(chat_id, answer, parse_mode="Markdown")

            status = "success"
            DB.add_log(user_id, query, category, sources_count, status)
            DB.inc_requests(user_id, category)

        except Exception as e:
            logger.error("Pipeline crash: %s", e, exc_info=True)
            try:
                self._send(chat_id, "❌ Что-то пошло не так. Попробуйте ещё раз или уточните запрос.")
            except Exception:
                pass
            DB.add_log(user_id, query, category, sources_count, "crash")


# =============================================================================
#  ИНИЦИАЛИЗАЦИЯ БОТА
# =============================================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
pipe = Pipeline(bot)


# =============================================================================
#  ХЭНДЛЕРЫ
# =============================================================================

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    DB.upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    name = escape_md(msg.from_user.first_name or "друг")
    text = (
        f"🔥 Привет, *{name}*\\!\n\n"
        "Я — *универсальный поисковый бот* с AI\\-анализом\\.\n"
        "Нахожу всё и сразу, с умом и красиво\\.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎵 *Музыка и треки*\n"
        "┗ Яндекс\\.Музыка · VK Music · Last\\.fm\n\n"
        "🎌 *Аниме и манга*\n"
        "┗ Shikimori\\.one · полная база с рейтингами\n\n"
        "🎬 *Фильмы и сериалы*\n"
        "┗ Кинопоиск · описания · рейтинги\n\n"
        "🔍 *Любые запросы*\n"
        "┗ Яндекс · DuckDuckGo · AI\\-анализ\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💬 *Просто напишите любой запрос\\!*\n"
        "Можно обрывками, с ошибками, как угодно — разберусь\\.\n\n"
        "📖 /help — инструкция\n"
        "🔎 /search \\[запрос\\] — явный поиск"
    )
    bot.send_message(msg.chat.id, text, parse_mode="MarkdownV2")


@bot.message_handler(commands=["help"])
def cmd_help(msg):
    text = (
        "📖 *Как пользоваться ботом*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎵 *Поиск музыки:*\n"
        "Напишите: `трек Монеточка`, `альбом Земфира`, `новинки 2026`\n\n"
        "🎌 *Поиск аниме:*\n"
        "Напишите: `аниме про школу романтика`, `Наруто серии`, `топ аниме 2024`\n\n"
        "🎬 *Поиск фильмов:*\n"
        "Напишите: `фильм Дюна смотреть`, `Достучаться до небес` или просто название\n\n"
        "🔍 *Любой поиск:*\n"
        "Пишите что угодно — бот определит категорию сам\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚙️ *Команды:*\n"
        "/start — главное меню\n"
        "/help — эта справка\n"
        "/search \\[запрос\\] — явный поиск\n\n"
        "⏱ *Время ответа:* 20–60 секунд\n\n"
        "_Бот оптимизирован для пользователей из России_"
    )
    bot.send_message(msg.chat.id, text, parse_mode="MarkdownV2")


@bot.message_handler(commands=["search"])
def cmd_search(msg):
    DB.upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    args = msg.text.partition(" ")[2].strip()
    if not args:
        bot.send_message(msg.chat.id, "✏️ Укажите запрос: `/search ваш запрос`", parse_mode="MarkdownV2")
        return
    threading.Thread(
        target=pipe.run,
        args=(msg.chat.id, msg.from_user.id, args),
        daemon=True
    ).start()


# =============================================================================
#  АДМИНКА
# =============================================================================

def is_admin(msg) -> bool:
    try:
        return msg.from_user.id == ADMIN_ID
    except Exception:
        return False


def is_admin_cb(call) -> bool:
    try:
        return call.from_user.id == ADMIN_ID
    except Exception:
        return False


@bot.message_handler(commands=["admin"])
def cmd_admin(msg):
    if not is_admin(msg):
        bot.send_message(msg.chat.id, "⛔ Нет доступа.")
        return
    _show_admin_menu(msg.chat.id)


def _show_admin_menu(chat_id: int):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("📢 Рассылка", callback_data="a_broadcast"),
        telebot.types.InlineKeyboardButton("📊 Статистика", callback_data="a_stats"),
        telebot.types.InlineKeyboardButton("🧠 Промпт", callback_data="a_prompt"),
        telebot.types.InlineKeyboardButton("🔌 Провайдеры", callback_data="a_providers"),
        telebot.types.InlineKeyboardButton("📋 Логи", callback_data="a_logs_0"),
    )
    bot.send_message(
        chat_id,
        "🔧 *Панель администратора*\n_Выберите действие:_",
        parse_mode="MarkdownV2",
        reply_markup=markup
    )


@bot.message_handler(commands=["stats"])
def cmd_stats(msg):
    if not is_admin(msg):
        bot.send_message(msg.chat.id, "⛔ Нет доступа."); return
    _send_stats(msg.chat.id)


@bot.message_handler(commands=["logs"])
def cmd_logs(msg):
    if not is_admin(msg):
        bot.send_message(msg.chat.id, "⛔ Нет доступа."); return
    _send_logs(msg.chat.id, 0)


@bot.message_handler(commands=["setprompt"])
def cmd_setprompt(msg):
    if not is_admin(msg):
        bot.send_message(msg.chat.id, "⛔ Нет доступа."); return
    admin_states[msg.from_user.id] = "await_prompt"
    cur = escape_md(DB.get_system_prompt()[:250])
    bot.send_message(
        msg.chat.id,
        f"🧠 *Текущий промпт:*\n_{cur}_\n\nОтправьте новый системный промпт:",
        parse_mode="MarkdownV2"
    )


@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(msg):
    if not is_admin(msg):
        bot.send_message(msg.chat.id, "⛔ Нет доступа."); return
    args = msg.text.partition(" ")[2].strip()
    if args:
        _prepare_broadcast(msg.chat.id, msg.from_user.id, args)
    else:
        admin_states[msg.from_user.id] = "await_broadcast"
        bot.send_message(msg.chat.id, "📢 Введите текст сообщения для рассылки:")


def _send_stats(chat_id: int):
    s = DB.stats()
    top_txt = ""
    for i, u in enumerate(s["top3"], 1):
        name = escape_md(u.get("first_name") or u.get("username") or "N/A")
        cnt = u.get("requests_count", 0)
        cat = u.get("favorite_category", "general")
        top_txt += f"  {i}\\. {name} — {cnt} зап\\. \\({CATEGORIES.get(cat,'🔍')} {cat}\\)\n"

    text = (
        f"📊 *Статистика бота*\n\n"
        f"👥 Пользователей: *{s['total_users']}*\n"
        f"🔢 Всего запросов: *{s['total_requests']}*\n"
        f"📅 Активны сегодня: *{s['active_today']}*\n\n"
        f"🏆 *Топ\\-3:*\n{top_txt or '_нет данных_'}"
    )
    bot.send_message(chat_id, text, parse_mode="MarkdownV2")


def _send_logs(chat_id: int, page: int):
    logs = DB.get_logs(20)
    start = page * 10
    chunk = logs[start:start + 10]
    if not chunk:
        bot.send_message(chat_id, "📋 Логи пусты."); return

    lines = [f"📋 *Логи* \\(стр\\. {page+1}\\)\n"]
    for e in reversed(chunk):
        ts = e.get("ts", "")[:16].replace("T", " ")
        cat = e.get("category", "?")
        q = escape_md(e.get("query", "")[:50])
        src = e.get("sources", 0)
        st = e.get("status", "?")
        icon = CATEGORIES.get(cat, "🔍")
        lines.append(f"`{ts}` {icon} _{q}_ | {src} ист\\. | `{st}`")

    markup = telebot.types.InlineKeyboardMarkup()
    btns = []
    if page > 0:
        btns.append(telebot.types.InlineKeyboardButton("⬅️", callback_data=f"a_logs_{page-1}"))
    if start + 10 < len(logs):
        btns.append(telebot.types.InlineKeyboardButton("➡️", callback_data=f"a_logs_{page+1}"))
    if btns:
        markup.add(*btns)

    bot.send_message(
        chat_id, "\n".join(lines),
        parse_mode="MarkdownV2",
        reply_markup=markup if btns else None
    )


def _send_providers_menu(chat_id: int):
    cfg = DB.get_providers()
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    icons = {
        "yandex": "🟡 Яндекс", "duckduckgo": "🦆 DuckDuckGo",
        "vk": "🔵 VK Music", "shikimori": "🎌 Shikimori",
        "lastfm": "🎸 Last.fm"
    }
    for name, label in icons.items():
        state = "✅" if cfg.get(name, True) else "❌"
        markup.add(telebot.types.InlineKeyboardButton(
            f"{state} {label}", callback_data=f"toggle_{name}"
        ))
    bot.send_message(
        chat_id, "🔌 *Управление провайдерами:*",
        parse_mode="MarkdownV2", reply_markup=markup
    )


def _prepare_broadcast(chat_id: int, admin_uid: int, text: str):
    users = DB.get_users()
    count = len(users)
    preview = escape_md(text[:200])
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("✅ Отправить", callback_data="confirm_bc"),
        telebot.types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_bc"),
    )
    admin_states[admin_uid] = f"confirm_bc:{text}"
    bot.send_message(
        chat_id,
        f"📢 *Предпросмотр рассылки:*\n_{preview}_\n\n👥 Получателей: *{count}*\n\nОтправить?",
        parse_mode="MarkdownV2",
        reply_markup=markup
    )


def _do_broadcast(chat_id: int, text: str):
    users = DB.get_users()
    ok, fail = 0, 0
    for uid_str in users:
        try:
            bot.send_message(int(uid_str), text, parse_mode="Markdown", disable_web_page_preview=True)
            ok += 1
            time.sleep(0.05)
        except Exception:
            fail += 1
    bot.send_message(
        chat_id,
        f"✅ Рассылка завершена\\!\n✅ Успешно: *{ok}*\n❌ Не доставлено: *{fail}*",
        parse_mode="MarkdownV2"
    )


# =============================================================================
#  CALLBACKS
# =============================================================================

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    cid = call.message.chat.id
    uid = call.from_user.id

    if not is_admin_cb(call):
        bot.answer_callback_query(call.id, "⛔ Нет доступа"); return

    d = call.data

    if d == "a_broadcast":
        admin_states[uid] = "await_broadcast"
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "📢 Введите текст для рассылки:")

    elif d == "a_stats":
        bot.answer_callback_query(call.id)
        _send_stats(cid)

    elif d == "a_prompt":
        admin_states[uid] = "await_prompt"
        bot.answer_callback_query(call.id)
        cur = escape_md(DB.get_system_prompt()[:250])
        bot.send_message(cid, f"🧠 *Текущий промпт:*\n_{cur}_\n\nОтправьте новый:", parse_mode="MarkdownV2")

    elif d == "a_providers":
        bot.answer_callback_query(call.id)
        _send_providers_menu(cid)

    elif d.startswith("a_logs_"):
        page = int(d.split("_")[-1])
        bot.answer_callback_query(call.id)
        _send_logs(cid, page)

    elif d.startswith("toggle_"):
        prov = d[7:]
        new_state = DB.toggle_provider(prov)
        label = "включён ✅" if new_state else "выключен ❌"
        bot.answer_callback_query(call.id, f"{prov}: {label}")
        _send_providers_menu(cid)

    elif d == "confirm_bc":
        state = admin_states.get(uid, "")
        if state.startswith("confirm_bc:"):
            text = state[len("confirm_bc:"):]
            admin_states.pop(uid, None)
            bot.answer_callback_query(call.id, "Рассылка начата!")
            threading.Thread(target=_do_broadcast, args=(cid, text), daemon=True).start()
        else:
            bot.answer_callback_query(call.id, "Нет данных.")

    elif d == "cancel_bc":
        admin_states.pop(uid, None)
        bot.answer_callback_query(call.id, "Отменено.")
        bot.send_message(cid, "❌ Рассылка отменена.")

    else:
        bot.answer_callback_query(call.id)


# =============================================================================
#  ГЛАВНЫЙ ХЭНДЛЕР
# =============================================================================

@bot.message_handler(func=lambda m: m.content_type == "text" and not m.text.startswith("/"))
def handle_text(msg):
    uid = msg.from_user.id
    DB.upsert_user(uid, msg.from_user.username, msg.from_user.first_name)

    state = admin_states.get(uid, "")

    if state == "await_prompt" and msg.from_user.id == ADMIN_ID:
        DB.set_system_prompt(msg.text.strip())
        admin_states.pop(uid, None)
        bot.send_message(msg.chat.id, "✅ Системный промпт обновлён\\!", parse_mode="MarkdownV2")
        return

    if state == "await_broadcast" and msg.from_user.id == ADMIN_ID:
        admin_states.pop(uid, None)
        _prepare_broadcast(msg.chat.id, uid, msg.text)
        return

    if state.startswith("confirm_bc:") and msg.from_user.id == ADMIN_ID:
        bot.send_message(msg.chat.id, "Используйте кнопки для подтверждения рассылки.")
        return

    query = msg.text.strip()
    if len(query) < 2:
        bot.send_message(msg.chat.id, "✏️ Напишите более подробный запрос.")
        return

    threading.Thread(
        target=pipe.run,
        args=(msg.chat.id, uid, query),
        daemon=True
    ).start()


# =============================================================================
#  ЗАПУСК
# =============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  🤖 UNIVERSAL SEARCH BOT — RUSSIA EDITION (Termux)")
    logger.info("=" * 60)
    logger.info("  LLM: %s", LLM_MODEL)
    logger.info("  VK API: %s", "✅ настроен" if VK_ACCESS_TOKEN else "❌ не настроен (веб-поиск)")
    logger.info("  Last.fm: %s", "✅ настроен" if LASTFM_API_KEY else "❌ не настроен (опционально)")
    logger.info("  Admin ID: %s", ADMIN_ID)
    logger.info("=" * 60)
    logger.info("  Бот запущен! Жду сообщений...")
    logger.info("=" * 60)

    bot.infinity_polling(
        logger_level=logging.WARNING,
        timeout=60,
        long_polling_timeout=30,
    )
