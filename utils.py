import json
import os
import time
import math
import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import Message
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

user_data_file = os.path.join(os.path.dirname(__file__), "users.json")
user_data = {}


def load_user_data():
    global user_data
    if os.path.exists(user_data_file):
        try:
            with open(user_data_file, "r", encoding="utf-8") as f:
                user_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            user_data = {}
            print("Ошибка чтения users.json. Создана пустая база данных.")
    else:
        user_data = {}
        print("Файл users.json не найден. Создана пустая база данных.")

def save_user_data():
    try:
        with open(user_data_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения users.json: {e}")

def update_telegram_username(user_id, username):
    user = get_user(user_id)
    if user and username and user.get("telegram_username") != username:
        user["telegram_username"] = username
        save_user_data()

def get_user(user_id):
    global user_data
    user_id = str(user_id)
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": 0,
            "name": "Без имени",
            "game_id": None,
            "last_bonus_time": 0,
            "referrals": [],
            "referrer": None,
            "telegram_username": None,
            "clickable_name": True,
            "assets": {  # Инициализируем имущество
                "cars": [],
                "houses": [],
                "yachts": [],
                "planes": [],
                "helicopters": [],
                "smartphones": [],
            },
            "user_deposits": [],  # <--- добавлено
        }
    # Если ключ `assets` отсутствует, добавляем его
    if "assets" not in user_data[user_id]:
        user_data[user_id]["assets"] = {
            "cars": [],
            "houses": [],
            "yachts": [],
            "planes": [],
            "helicopters": [],
            "smartphones": [],
        }
    if "user_deposits" not in user_data[user_id]:
        user_data[user_id]["user_deposits"] = []
    return user_data[user_id]


def process_deposits(user):
    now = int(time.time())
    deposits = user.get("user_deposits", [])
    new_deposits = []
    changed = False

    for dep in deposits:
        start = dep["start"]
        days = dep["days"]
        percent = dep["percent"]
        amount = dep["amount"]

        # Сколько дней прошло с момента открытия вклада
        days_passed = (now - start) // 86400
        if days_passed <= 0:
            new_deposits.append(dep)
            continue

        # Капитализация процентов за прошедшие дни
        for _ in range(days_passed):
            amount = math.floor(amount * (1 + percent / 100))

        # Если срок вклада истёк — возвращаем деньги на счёт
        if days_passed >= days:
            if user.get("game_id") is not None:
                update_balance(user["game_id"], get_balance(user["game_id"]) + amount)
            changed = True
        else:
            # Обновляем сумму и дату старта (чтобы не начислять повторно)
            dep["amount"] = amount
            dep["start"] = start + days_passed * 86400
            new_deposits.append(dep)
            changed = True

    if changed:
        user["user_deposits"] = new_deposits
        save_user_data()


def generate_work_keyboard(correct_emoji: str):
    emojis = ["🗑️", "♻️", "🧹", "🚮", "🪠", "🧼"]
    random.shuffle(emojis)  

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=emojis[0]),
                KeyboardButton(text=emojis[1]),
                KeyboardButton(text=emojis[2]),
            ],
            [
                KeyboardButton(text=emojis[3]),
                KeyboardButton(text=emojis[4]),
                KeyboardButton(text=emojis[5]),
            ],
        ],
        resize_keyboard=True,
    )
    return keyboard

async def send_shop_items(message: Message, category: str, items: list):
    user_id = message.from_user.id
    user = get_user(user_id)

    # Формируем текст с товарами
    text = f"🛒 Раздел: {category.capitalize()}\n\n"
    for i, item in enumerate(items, start=1):
        text += f"{i}. {item['name']} — {item['price']}$\n"

    text += "\nНапишите номер предмета, чтобы купить его."

    # Сохраняем текущий раздел и товары в данных пользователя
    user["current_shop_category"] = category
    user["current_shop_items"] = items
    save_user_data()

    # Отправляем сообщение с товарами
    await message.answer(text, reply_markup=ReplyKeyboardRemove())


def find_user_by_identifier(identifier, users_data):
    """
    Ищет пользователя по игровому ID, Telegram ID или Telegram-юзернейму (с @ и без, любой регистр).
    Возвращает (user_id, user_data) или (None, None), если пользователь не найден.
    """
    identifier = identifier.strip().lower().lstrip("@")
    for user_id, user_data in users_data.items():
        tg_username = user_data.get('telegram_username')
        # Проверяем по game_id, Telegram ID
        if str(user_data.get("game_id")) == identifier or str(user_id) == identifier:
            return int(user_id), user_data
        # Проверяем по юзернейму с @ и без
        if isinstance(tg_username, str):
            if tg_username.lower() == identifier or f"@{tg_username.lower()}" == identifier:
                return int(user_id), user_data
    return None, None


def is_emoji_present(text: str) -> bool:
    """Проверяет, содержит ли текст смайлики."""
    return any(char for char in text if char in ["🗑️", "♻️", "🧹", "🚮", "🪠", "🧼", "⛏️"])


def get_balance(user_id):
    return get_user(user_id)["balance"]


def update_balance(user_id, amount):
    user = get_user(user_id)
    user["balance"] = round_amount(amount)
    save_user_data()


def set_name(user_id, name):
    user = get_user(user_id)
    user["name"] = name
    save_user_data()


def get_name(user_id):
    return get_user(user_id)["name"]


def get_game_id(user_id):
    return get_user(user_id)["game_id"]


def generate_id():
    while True:
        game_id = random.randint(100000, 999999)
        if not any(user.get("game_id") == game_id for user in user_data.values()):
            return game_id


def parse_k(text: str, balance: int | float = 0) -> int | None:
    text = text.strip().lower().replace(",", ".")
    if "/" in text:
        try:
            num, denom = map(float, text.split("/"))
            if denom == 0:
                return None
            return round_amount(balance * (num / denom))
        except (ValueError, ZeroDivisionError):
            return None
    num_part = []
    k_count = 0
    for char in text:
        if char.isdigit() or char == ".":
            num_part.append(char)
        elif char in "кk":
            k_count += 1
        else:
            return None
    if not num_part:
        return None
    try:
        number = float("".join(num_part)) if "." in num_part else int("".join(num_part))
    except ValueError:
        return None
    return round_amount(number * (10 ** (3 * k_count)))


def round_amount(amount: float) -> int:
    return int(round(amount))


def round_balance():
    for user_id, data in user_data.items():
        if "balance" in data:
            data["balance"] = round(data["balance"])
    save_user_data()


def fix_user_data():
    global user_data
    """
    Исправляет структуру данных пользователей, добавляя отсутствующие ключи.
    """
    for user_id, user in user_data.items():
        if "assets" not in user:
            user["assets"] = {
                "cars": [],
                "houses": [],
                "yachts": [],
                "planes": [], 
                "helicopters": [],
                "smartphones": [],
            }
        # Добавляем user_deposits, если его нет или он не список
        if "user_deposits" not in user or not isinstance(user["user_deposits"], list):
            user["user_deposits"] = []
    save_user_data()


def round_all_balances():
    modified = False
    for uid, data in user_data.items():
        if "balance" in data:
            old_balance = data["balance"]
            new_balance = round_amount(old_balance)
            if new_balance != old_balance:
                data["balance"] = new_balance
                modified = True
    if modified:
        save_user_data()


def check_and_pay_deposit(user_id):
    global user_data
    user = get_user(user_id)
    deposits = user.get("user_deposits", [])
    now = int(time.time())
    paid_total = 0
    new_deposits = []
    for dep in deposits:
        if now - dep["start"] >= dep["days"] * 86400:
            total = int(dep["amount"] * (1 + dep["percent"] / 100) ** dep["days"])
            paid_total += total
        else:
            new_deposits.append(dep)
    if paid_total > 0:
        update_balance(user_id, get_balance(user_id) + paid_total)
        user["user_deposits"] = new_deposits
        save_user_data()
        return paid_total
    return None


def format_amount(amount: int | float) -> str:
    return f"{int(amount):,}".replace(",", ".")


def process_all_deposits():
    for user in user_data.values():
        process_deposits(user)
    save_user_data()
    
    
def safe_reply_kb(message, kb):
    return kb if getattr(message, "chat", None) and message.chat.type == "private" else None


def reset_user_data(user_id):
    """Удаляет все данные о пользователе из памяти бота."""
    if user_id in user_data:
        del user_data[user_id]
        save_user_data()
        
        
def clickable_name(user_id, name, clickable=True):
    if not clickable:
        return name
    return f'<a href="tg://user?id={user_id}">{name}</a>'
    