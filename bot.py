#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot для мониторинга буксов
"""

import os
import logging
import sqlite3
import re
from datetime import datetime

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) or 1241661286
DB_PATH = os.getenv("DB_PATH", "bux.db")

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =============================================================================
# АДМИН - ПРОВЕРКА ПРАВ
# =============================================================================
def is_admin(uid: int) -> bool:
    """Проверка прав администратора"""
    result = uid == MY_ADMIN_ID
    logger.info(f"admin_check: uid={uid} MY_ADMIN_ID={MY_ADMIN_ID} result={result}")
    return result

# =============================================================================
# БАЗА ДАННЫХ
# =============================================================================
def get_connection():
    """Получение соединения с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def sql_query(query: str, params: tuple = ()):
    """Выполнение SQL запроса"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result

def init_database():
    """Инициализация базы данных"""
    sql_query("""
        CREATE TABLE IF NOT EXISTS bux (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            real_url TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    # Добавляем буксы по умолчанию
    default_bux = [
        ("ABVIZ", "https://abviz.ru/", "элитный"),
        ("SEO-SPRINGS", "https://seo-springs.ru/", "элитный"),
        ("INVES-NEXT", "https://inves-next.ru/", "платит"),
        ("DOXODCENTER", "https://www.doxodcenter.ru/", "платит"),
        ("TONIABUX", "https://toniabux.com/", "платит"),
        ("SEO-FAST", "https://seo-fast.ru/", "элитный"),
        ("IPWEB", "https://www.ipweb.ru/", "элитный"),
        ("MJPUBLIC", "https://mjpublic.com/", "платит"),
        ("SERFEARN", "https://serfearn.com/", "платит"),
        ("SEOLIFT", "https://seolift.pro/", "платит"),
        ("COINBUX", "https://coinbux.ru/", "платит"),
        ("SERFBUX", "https://serfbux.win/", "платит"),
        ("SEO-TASK", "https://seo-task.com/", "платит"),
        ("BIQ1", "https://biq1.ru/", "платит"),
        ("COINPAYU", "https://www.coinpayu.com/", "платит"),
        ("YU.SU", "https://yu.su/", "платит"),
        ("SOLOSURF", "https://solosurf.ru/", "платит"),
        ("SEOKLYB", "https://seoklyb.ru/", "платит"),
        ("TASK-VISIT", "https://task-visit.ru/", "платит"),
        ("GOLDBAX", "https://goldbax.ru/", "платит"),
        ("A-DOVA", "https://a-dova.com/", "платит"),
        ("SEOTIME", "https://seotime.ru/", "платит"),
        ("SEOLAYF", "https://seolayf.top/", "платит"),
        ("ADVEART", "https://adveart.ru/", "платит"),
        ("ADS-TARGET", "https://ads-target.ru/", "платит"),
        ("PROFITCENTR", "https://profitcentr.com/", "платит"),
        ("ADSVISION", "https://adsvision.ru/", "платит"),
        ("WMZONA", "https://wmzona.com/", "платит"),
        ("SOOFASTBUX", "https://soofastbux.ru/", "платит"),
        ("PROFITSERFING", "https://profitserfing.ru/", "платит"),
        ("SURF-MINI", "https://surf-mini.ru/", "платит"),
        ("SEOTARGET", "https://seotarget.xyz/", "платит"),
        ("HITBUX", "https://hitbux.ru/", "платит"),
        ("AVISO", "https://aviso.bz/", "платит"),
        ("SERFTIME", "https://serftime.ru/", "платит"),
        ("OJOOO", "https://ojooo.com/", "платит"),
        ("SEO-24", "https://seo-24.pro/", "платит"),
        ("ADBTC", "https://adbtc.top/", "платит"),
        ("UPMONEY", "https://upmoney.ru/", "платит"),
        ("SOCPUBLIC", "https://socpublic.com/", "платит"),
        ("DYN-COIN", "https://dyn-coin.com/", "платит"),
        ("WEB-IP", "https://www.web-ip.ru/", "платит"),
        ("NEOBUX", "https://neobux.com/", "платит"),
        ("ZOOMAD", "https://zoomad.ru/", "платит"),
        ("WMMAIL", "https://www.wmmail.ru/i", "платит"),
        ("HEEDYOU", "https://heedyou.com/", "платит"),
        ("SEOSPRINT", "https://seosprint.net/", "платит"),
        ("SEOFAST", "https://seofast.ru/", "платит"),
        ("ADSBOOK", "https://adsbook.ru/", "платит"),
        ("7BUX", "https://7bux.ru/", "платит"),
        ("TOPBUX", "https://topbux.ru/", "платит"),
    ]
    
    for name, url, status in default_bux:
        try:
            sql_query(
                "INSERT INTO bux(name, real_url, description) VALUES (?, ?, ?)",
                (name, url, status),
            )
        except sqlite3.IntegrityError:
            pass
    
    logger.info(f"✅ Добавлено {len(default_bux)} буксов по умолчанию")
    
    sql_query("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT
        )
    """)
    sql_query("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    sql_query("""
        CREATE TABLE IF NOT EXISTS parse_logs (
            added INTEGER,
            updated INTEGER,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    sql_query("""
        CREATE TABLE IF NOT EXISTS partners (
            name TEXT UNIQUE,
            url TEXT
        )
    """)
    # Партнёрские ссылки по умолчанию
    sql_query(
        "INSERT OR IGNORE INTO partners(name, url) VALUES (?, ?)",
        ("bothost", "https://bothost.ru/register.php?ref=1501FA5F"),
    )
    sql_query(
        "INSERT OR IGNORE INTO partners(name, url) VALUES (?, ?)",
        ("linkslot", "https://linkslot.ru/?ref=DMITRY967"),
    )
    logger.info("✅ База данных инициализирована")

def add_user(uid: int, username: str):
    """Добавление пользователя"""
    try:
        sql_query("INSERT INTO users(id, username) VALUES (?, ?)", (uid, username))
        logger.info(f"User added: {username} ({uid})")
    except sqlite3.IntegrityError:
        pass

# Операции с буксами
def get_all_bux():
    """Получить все активные буксы"""
    return sql_query("SELECT * FROM bux WHERE is_active = 1 ORDER BY name")

def add_bux(name: str, url: str, description: str):
    """Добавить букс"""
    try:
        sql_query(
            "INSERT INTO bux(name, real_url, description) VALUES (?, ?, ?)",
            (name, url, description),
        )
        logger.info(f"Bux added: {name}")
    except sqlite3.IntegrityError:
        sql_query(
            "UPDATE bux SET real_url = ?, description = ? WHERE name = ?",
            (url, description, name),
        )
        logger.info(f"Bux updated: {name}")

def delete_bux(bux_id: int):
    """Удалить букс"""
    sql_query("DELETE FROM bux WHERE id = ?", (bux_id,))
    logger.info(f"Bux deleted: id={bux_id}")

def update_bux(field: str, value: str, bux_id: int):
    """Обновить поле букса"""
    allowed_fields = ["name", "real_url", "description", "is_active"]
    if field not in allowed_fields:
        logger.warning(f"Attempted to update disallowed field: {field}")
        return
    sql_query(f"UPDATE bux SET {field} = ? WHERE id = ?", (value, bux_id))
    logger.info(f"Bux updated: id={bux_id} {field}={value}")

def get_all_users():
    """Получить всех пользователей"""
    return sql_query("SELECT * FROM users")

def add_parse_log(added: int, updated: int):
    """Добавить лог парсинга"""
    sql_query(
        "INSERT INTO parse_logs(added, updated) VALUES (?, ?)",
        (added, updated),
    )

def add_broadcast(message: str):
    """Добавить запись о рассылке"""
    sql_query("INSERT INTO broadcasts(message) VALUES (?)", (message,))

def get_partners():
    """Получить все партнёрские ссылки"""
    results = sql_query("SELECT name, url FROM partners")
    return {row["name"]: row["url"] for row in results}

def set_partner(name: str, url: str):
    """Установить партнёрскую ссылку"""
    sql_query(
        "INSERT OR REPLACE INTO partners(name, url) VALUES (?, ?)",
        (name, url),
    )

# =============================================================================
# ПАРСЕР
# =============================================================================
DOM_BASES = {
    "paymer": "https://paymer.fun/",
    "doxodcenter": "https://www.doxodcenter.ru/",
    "toniabux": "https://toniabux.com/",
    "seo-springs": "https://seo-springs.ru/",
    "abviz": "https://abviz.ru/",
    "seo-fast": "https://seo-fast.ru/",
    "ipweb": "https://www.ipweb.ru/",
    "mjpublic": "https://mjpublic.com/",
    "serfearn": "https://serfearn.com/",
    "seolift": "https://seolift.pro/",
    "coinbux": "https://coinbux.ru/",
    "serfbux": "https://serfbux.win/",
    "seo-task": "https://seo-task.com/",
    "biq1": "https://biq1.ru/",
    "coinpayu": "https://www.coinpayu.com/",
    "coinzi": "https://coinzi.net/",
    "yu.su": "https://yu.su/",
    "inves-next": "https://inves-next.ru/",
    "solosurf": "https://solosurf.ru/",
    "seoklyb": "https://seoklyb.ru/",
    "task-visit": "https://task-visit.ru/",
    "goldbax": "https://goldbax.ru/",
    "a-dova": "https://a-dova.com/",
    "makeyoutask": "https://makeyoutask.ru/",
    "seotime": "https://seotime.ru/",
    "seolayf": "https://seolayf.top/",
    "adveart": "https://adveart.ru/",
    "b2bx": "https://b2bx.fun/",
    "ads-target": "https://ads-target.ru/",
    "profitcentr": "https://profitcentr.com/",
    "buxomaster": "https://buxo.monster/",
    "adsvision": "https://adsvision.ru/",
    "wmzona": "https://wmzona.com/",
    "soofastbux": "https://soofastbux.ru/",
    "profitserfing": "https://profitserfing.ru/",
    "surf-mini": "https://surf-mini.ru/",
    "seotarget": "https://seotarget.xyz/",
    "hitbux": "https://hitbux.ru/",
    "exellent": "https://exellent.site/",
    "aviso": "https://aviso.bz/",
    "prodvisots": "https://prodvisots.ru/",
    "serftime": "https://serftime.ru/",
    "ojooo": "https://ojooo.com/",
    "seo-24": "https://seo-24.pro/",
    "exp-megabux": "https://exp-megabux.ru/",
    "acashly": "https://www.acashly.com/",
    "adbtc": "https://adbtc.top/",
    "upmoney": "https://upmoney.ru/",
    "socpublic": "https://socpublic.com/",
    "dyn-coin": "https://dyn-coin.com/",
    "mnmix": "https://mnmix.ru/",
    "buxseo": "https://buxseo.ru/",
    "web-ip": "https://www.web-ip.ru/",
    "neobux": "https://neobux.com/",
    "zoomad": "https://zoomad.ru/",
    "wmmail": "https://www.wmmail.ru/i",
    "heedyou": "https://heedyou.com/",
    "seosprint": "https://seosprint.net/",
    "seofast": "https://seofast.ru/",
    "adsbook": "https://adsbook.ru/",
    "7bux": "https://7bux.ru/",
    "topbux": "https://topbux.ru/",
}

async def parse_workprom():
    """Парсинг workprom.ru"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://workprom.ru/monitor/",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=30,
            ) as response:
                html = await response.text()

        logger.info(f"HTML length: {len(html)}")
        added, updated = 0, 0
        
        # Ищем все ссылки на буксы в таблице
        pattern = r'<a href="(https?://[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)
        logger.info(f"Total links found: {len(matches)}")
        
        for url, name in matches:
            # Пропускаем не буксы
            if any(x in url.lower() for x in ['workprom', 'register', 'login', 'profile', 'css', 'js']):
                continue
            name = name.strip()
            if len(name) < 2 or len(name) > 50:
                continue
            
            logger.info(f"Found: {name} - {url}")
            
            # Определяем реальный URL из DOM_BASES
            real_url = url
            for key, base_url in DOM_BASES.items():
                if key in url.lower():
                    real_url = base_url
                    break

            try:
                sql_query(
                    "INSERT INTO bux(name, real_url, description) VALUES (?, ?, ?)",
                    (name, real_url, "добавлен"),
                )
                added += 1
            except sqlite3.IntegrityError:
                sql_query(
                    "UPDATE bux SET real_url = ?, description = ? WHERE name = ?",
                    (real_url, "обновлен", name),
                )
                updated += 1

        add_parse_log(added, updated)
        logger.info(f"Parse complete: +{added} ~{updated}")
        return {"added": added, "updated": updated}

    except Exception as e:
        logger.error(f"Parse error: {e}")
        return {"error": str(e)}

# =============================================================================
# КЛАВИАТУРЫ
# =============================================================================
def keyboard_admin():
    """Клавиатура администратора"""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Добавить", callback_data="a1"),
                InlineKeyboardButton("🗑 Удалить", callback_data="a2"),
            ],
            [
                InlineKeyboardButton("✏️ Редактировать", callback_data="a3"),
                InlineKeyboardButton("🌐 Парсинг", callback_data="a4"),
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="a5"),
                InlineKeyboardButton("📢 Рассылка", callback_data="a6"),
            ],
            [
                InlineKeyboardButton("👥 Юзеры", callback_data="a7"),
                InlineKeyboardButton("📋 Логи", callback_data="a8"),
            ],
            [
                InlineKeyboardButton("🔗 Партнёрки", callback_data="a9"),
                InlineKeyboardButton("⏱ Интервал", callback_data="aa"),
            ],
            [InlineKeyboardButton("⬅️ Назад", callback_data="bk")],
        ]
    )

def keyboard_main():
    """Основная клавиатура"""
    buttons = [
        [
            InlineKeyboardButton("📊 Мониторинг", callback_data="m1"),
            InlineKeyboardButton("🔍 Поиск", callback_data="m2"),
        ],
        [
            InlineKeyboardButton("📈 Статистика", callback_data="m3"),
            InlineKeyboardButton("🔄 Обновить", callback_data="m4"),
        ],
        [
            InlineKeyboardButton("🤖 Bothost", callback_data="m5"),
            InlineKeyboardButton("🔗 Linkslot", callback_data="m6"),
        ],
        [
            InlineKeyboardButton("💼 Добавить букс", callback_data="m7"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)

def keyboard_back():
    """Клавиатура назад"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="bk")]])

# =============================================================================
# ОБРАБОТЧИКИ КОМАНД
# =============================================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    uid = update.effective_user.id
    username = update.effective_user.username
    add_user(uid, username)
    is_admin_user = is_admin(uid)
    logger.info(f"START: uid={uid} username={username} admin={is_admin_user}")
    await update.message.reply_text(
        f"👋 *Привет!* {'[ADMIN]' if is_admin_user else ''}",
        reply_markup=keyboard_main(),
        parse_mode="Markdown",
    )

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin"""
    uid = update.effective_user.id
    is_admin_user = is_admin(uid)
    logger.info(f"ADMIN: uid={uid} admin={is_admin_user}")
    if not is_admin_user:
        await update.message.reply_text(
            f"❌ Нет прав\nВаш ID: {uid}\nAdmin ID: {MY_ADMIN_ID}"
        )
        return
    await update.message.reply_text(
        "🔧 *АДМИНКА*", reply_markup=keyboard_admin(), parse_mode="Markdown"
    )

# =============================================================================
# ОБРАБОТЧИК CALLBACK
# =============================================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()
    is_admin_user = is_admin(uid)
    logger.info(f"CALLBACK: uid={uid} data={data} admin={is_admin_user}")

    # Возврат назад
    if data == "bk":
        return await cmd_start(update, context)

    # Админка
    if data == "a0":
        if not is_admin_user:
            return await query.edit_message_text("❌", reply_markup=keyboard_back())
        return await query.edit_message_text(
            "🔧 *АДМИНКА*", reply_markup=keyboard_admin(), parse_mode="Markdown"
        )

    # Добавить букс
    if data == "a1":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        context.user_data["action"] = "add_name"
        return await query.edit_message_text("➕ Введите название:", reply_markup=keyboard_back())

    # Удалить букс - список
    if data == "a2":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        bux_list = get_all_bux()
        if not bux_list:
            return await query.edit_message_text("❌ Пусто", reply_markup=keyboard_back())
        buttons = [
            [InlineKeyboardButton(f"🗑 {b['name'][:15]}", callback_data=f"d{b['id']}")]
            for b in bux_list[:15]
        ]
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="a0")])
        return await query.edit_message_text(
            "🗑 Удалить букс:", reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Редактировать букс - список
    if data == "a3":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        bux_list = get_all_bux()
        if not bux_list:
            return await query.edit_message_text("❌ Пусто", reply_markup=keyboard_back())
        buttons = [
            [InlineKeyboardButton(f"✏️ {b['name'][:15]}", callback_data=f"e{b['id']}")]
            for b in bux_list[:15]
        ]
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="a0")])
        return await query.edit_message_text(
            "✏️ Редактировать букс:", reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Парсинг
    if data == "a4":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        await query.edit_message_text("🔄 Парсинг...")
        result = await parse_workprom()
        return await query.edit_message_text(
            f"✅ Добавлено: {result.get('added', 0)}\nОбновлено: {result.get('updated', 0)}",
            reply_markup=keyboard_back(),
        )

    # Статистика админ
    if data == "a5":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        total_bux = len(get_all_bux())
        total_users = len(get_all_users())
        return await query.edit_message_text(
            f"📊 Статистика\n\nБуксов: {total_bux}\nПользователей: {total_users}",
            reply_markup=keyboard_back(),
        )

    # Рассылка
    if data == "a6":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        context.user_data["action"] = "broadcast"
        return await query.edit_message_text(
            "📢 Введите текст рассылки:", reply_markup=keyboard_back()
        )

    # Юзеры
    if data == "a7":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        users = get_all_users()[:20]
        msg = "👥 Пользователи:\n\n" + "\n".join(
            f"@{u['username'] or '-'} ({u['id']})" for u in users
        )
        return await query.edit_message_text(msg, reply_markup=keyboard_back())

    # Логи парсинга
    if data == "a8":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        logs = sql_query(
            "SELECT added, updated, parsed_at FROM parse_logs ORDER BY parsed_at DESC LIMIT 10"
        )
        msg = "📋 Логи парсинга:\n\n" + "\n".join(
            f"+{l['added']} ~{l['updated']} {l['parsed_at']}" for l in logs
        )
        return await query.edit_message_text(msg, reply_markup=keyboard_back())

    # Партнёрки
    if data == "a9":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✏️ Bothost", callback_data="pb"),
                    InlineKeyboardButton("✏️ Linkslot", callback_data="pl"),
                ],
                [InlineKeyboardButton("⬅️ Назад", callback_data="a0")],
            ]
        )
        return await query.edit_message_text("🔗 Партнёрки:", reply_markup=buttons)

    # Интервал
    if data == "aa":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        context.user_data["action"] = "interval"
        return await query.edit_message_text("⏱ Интервал (сек):", reply_markup=keyboard_back())

    # Редактировать партнёрку
    if data in ("pb", "pl"):
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        partner_name = "bothost" if data == "pb" else "linkslot"
        context.user_data["partner_name"] = partner_name
        context.user_data["action"] = "partner_url"
        return await query.edit_message_text(
            f"🔗 Введите ссылку для {partner_name}:", reply_markup=keyboard_back()
        )

    # Удалить букс
    if data.startswith("d"):
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        bux_id = int(data[1:])
        delete_bux(bux_id)
        await query.answer("✅ Удалено", show_alert=True)
        return await cmd_admin(update, context)

    # Редактировать букс - выбор поля
    if data.startswith("e"):
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        bux_id = int(data[1:])
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Название", callback_data=f"en{bux_id}"),
                    InlineKeyboardButton("Ссылка", callback_data=f"eu{bux_id}"),
                ],
                [InlineKeyboardButton("Статус", callback_data=f"ed{bux_id}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="a3")],
            ]
        )
        return await query.edit_message_text("✏️ Выберите поле:", reply_markup=buttons)

    # Редактирование - название
    if data.startswith("en"):
        if not is_admin_user:
            return
        context.user_data["edit_field"] = "name"
        context.user_data["edit_id"] = int(data[2:])
        return await query.edit_message_text("✏️ Введите новое название:")

    # Редактирование - ссылка
    if data.startswith("eu"):
        if not is_admin_user:
            return
        context.user_data["edit_field"] = "url"
        context.user_data["edit_id"] = int(data[2:])
        return await query.edit_message_text("🔗 Введите новую ссылку:")

    # Редактирование - статус
    if data.startswith("ed"):
        if not is_admin_user:
            return
        context.user_data["edit_field"] = "description"
        context.user_data["edit_id"] = int(data[2:])
        return await query.edit_message_text("📝 Введите новый статус:")

    # ===== МЕНЮ =====
    # Мониторинг
    if data == "m1":
        bux_list = get_all_bux()
        if not bux_list:
            return await query.edit_message_text("❌ Пусто", reply_markup=keyboard_back())
        msg = "📊 Мониторинг:\n\n" + "\n\n".join(
            f"*{b['name'].replace('_', ' ')}*\n{b['description'] or '-'}" for b in bux_list[:15]
        )
        try:
            return await query.edit_message_text(
                msg, parse_mode="Markdown", reply_markup=keyboard_back()
            )
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            msg_plain = "📊 Мониторинг:\n\n" + "\n\n".join(
                f"{b['name']}\n{b['description'] or '-'}" for b in bux_list[:15]
            )
            return await query.edit_message_text(
                msg_plain, reply_markup=keyboard_back()
            )

    # Поиск
    if data == "m2":
        context.user_data["action"] = "search"
        return await query.edit_message_text("🔍 Введите название для поиска:", reply_markup=keyboard_back())

    # Статистика
    if data == "m3":
        total_bux = len(get_all_bux())
        total_users = len(get_all_users())
        return await query.edit_message_text(
            f"📊 Статистика\n\nБуксов: {total_bux}\nПользователей: {total_users}",
            reply_markup=keyboard_back(),
        )

    # Обновить (парсинг)
    if data == "m4":
        if not is_admin_user:
            return await query.answer("❌", show_alert=True)
        await query.edit_message_text("🔄 Парсинг...")
        result = await parse_workprom()
        return await query.edit_message_text(
            f"✅ +{result.get('added', 0)} ~{result.get('updated', 0)}",
            reply_markup=keyboard_back(),
        )

    # Bothost
    if data == "m5":
        partners = get_partners()
        url = partners.get("bothost", "https://bothost.ru/register.php?ref=1501FA5F")
        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💻 Хостинг", url=url)],
                [InlineKeyboardButton("⬅️ Назад", callback_data="bk")],
            ]
        )
        return await query.edit_message_text(f"🤖 Bothost\n{url}", reply_markup=buttons)

    # Linkslot
    if data == "m6":
        partners = get_partners()
        url = partners.get("linkslot", "https://linkslot.ru/?ref=DMITRY967")
        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("📢 Реклама", url=url)],
                [InlineKeyboardButton("⬅️ Назад", callback_data="bk")],
            ]
        )
        return await query.edit_message_text(f"🔗 Linkslot\n{url}", reply_markup=buttons)

    # Добавить букс - инфо
    if data == "m7":
        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✉️ Написать", url="https://t.me/DMITRY967")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="bk")],
            ]
        )
        return await query.edit_message_text(
            "💼 Добавить букс в мониторинг\n\nПишите: @DMITRY967",
            reply_markup=buttons,
        )

# =============================================================================
# ОБРАБОТЧИК СООБЩЕНИЙ
# =============================================================================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    uid = update.effective_user.id
    text = update.message.text
    is_admin_user = is_admin(uid)
    action = context.user_data.get("action")
    logger.info(f"MESSAGE: uid={uid} text={text} action={action} admin={is_admin_user}")

    # Добавление букса - название
    if action == "add_name" and is_admin_user:
        context.user_data["tmp_name"] = text
        context.user_data["action"] = "add_url"
        return await update.message.reply_text("📝 Введите ссылку:", reply_markup=keyboard_back())

    # Добавление букса - ссылка
    if action == "add_url" and is_admin_user:
        add_bux(context.user_data.get("tmp_name", "X"), text, "добавлен")
        context.user_data.pop("action", None)
        context.user_data.pop("tmp_name", None)
        return await update.message.reply_text("✅ Добавлено!", reply_markup=keyboard_admin())

    # Рассылка
    if action == "broadcast" and is_admin_user:
        users = get_all_users()
        ok, fail = 0, 0
        for user in users:
            try:
                await context.bot.send_message(user["id"], f"📢 {text}")
                ok += 1
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                fail += 1
        add_broadcast(text)
        context.user_data.pop("action", None)
        return await update.message.reply_text(
            f"✅ Рассылка завершена\nОтправлено: {ok}\nОшибок: {fail}",
            reply_markup=keyboard_admin(),
        )

    # Интервал (заглушка)
    if action == "interval" and is_admin_user:
        context.user_data.pop("action", None)
        return await update.message.reply_text("⏱ Интервал установлен", reply_markup=keyboard_admin())

    # Партнёрка - URL
    if action == "partner_url" and is_admin_user:
        partner_name = context.user_data.get("partner_name", "unknown")
        set_partner(partner_name, text)
        context.user_data.pop("action", None)
        context.user_data.pop("partner_name", None)
        return await update.message.reply_text("✅ Партнёрка обновлена", reply_markup=keyboard_admin())

    # Поиск
    if action == "search":
        context.user_data.pop("action", None)
        bux_list = get_all_bux()
        found = [b for b in bux_list if text.lower() in b["name"].lower()]
        if not found:
            return await update.message.reply_text("❌ Ничего не найдено", reply_markup=keyboard_back())
        msg = "🔍 Поиск:\n\n" + "\n\n".join(
            f"*{b['name']}*\n{b['description'] or '-'}" for b in found[:10]
        )
        return await update.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=keyboard_back()
        )

    # Редактирование букса
    edit_field = context.user_data.get("edit_field")
    edit_id = context.user_data.get("edit_id")
    if edit_field and edit_id:
        field_map = {"name": "name", "url": "real_url", "description": "description"}
        db_field = field_map.get(edit_field, edit_field)
        update_bux(db_field, text, edit_id)
        await update.message.reply_text("✅ Обновлено!", reply_markup=keyboard_admin())
        context.user_data.pop("edit_field", None)
        context.user_data.pop("edit_id", None)
        return

    # Сообщение по умолчанию
    await update.message.reply_text("❓ Используйте /start или /admin", reply_markup=keyboard_main())

# =============================================================================
# ЗАПУСК
# =============================================================================
def main():
    """Точка входа"""
    init_database()
    logger.info(f"🚀 Бот запущен! MY_ADMIN_ID={MY_ADMIN_ID}")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
