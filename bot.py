import asyncio
import random
import re
import json
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram import types
from aiogram.fsm.state import default_state
from config import owners, admins, API_TOKEN
from games import (bet_multipliers, roulette_numbers, bet_aliases)
from games import RouletteState, CrashState,generate_crash_coef
from aiogram.filters import StateFilter
from keyboards import (
    work_kb,
    menu_kb,
    click_kb,
    games_kb,
    settings_kb,
    ref_kb,
    top_ref_kb,
    top_balance_kb,
    mining_kb,
    admin_kb,
    admin_set_kb,
    get_bank_action_kb,
    get_bank_main_kb,
    get_deposit_terms_kb,
    
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
import time
from shop import router as shop_router
from shop import get_assets_text, SHOP_ITEMS, ASSET_EMOJIS
from texts import ( 
    roulette_help_text,
    transfer_help_text,
    miner_help_text,
    dvor_help_text,
    work_help_text,
    games_help_text,
    admin_panel_help_text,
    cladman_help_text,
    shop_help_text,
    assets_help_text,
    sell_help_text,
    bank_help_text,
    deposit_help_text,
    crash_help_text,
    all_commands_text,
    clicker_help_text,
    report_help_text,
    coin_help_text,
    bonus_help_text,
    top_help_text,
    profile_help_text,
    work_help_text,
)
from games import router as roulette_router
from config import admins
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery
import utils
from config import API_TOKEN, owners, bot
from utils import (
    load_user_data,
    save_user_data,
    get_user,
    get_balance,
    update_balance,
    set_name,
    get_name,
    get_game_id,
    parse_k,
    round_amount,
    fix_user_data,
    round_all_balances,
    round_balance,
    update_telegram_username,
    generate_work_keyboard,
    is_emoji_present,
    find_user_by_identifier,
    send_shop_items,
    check_and_pay_deposit,
    process_deposits,
    process_all_deposits,
    format_amount,
    safe_reply_kb,
    reset_user_data,
    clickable_name,
)


help_synonyms = {
    "рулетка": ["рулетка", "рулетки", "рулетку", "рулетке", "рулеточ", "рулет", "рулету"],
    "передать": ["передать", "перевод", "перевести", "передачи", "переводы"],
    "работа": ["работа", "работу", "работы", "работе", "работать"],
    "шахтер": ["шахтер", "шахтёр", "шахтера", "шахтёра", "шахтеру", "шахтёру", "шахтеры", "шахтёры"],
    "дворник": ["дворник", "дворника", "дворнику", "дворники"],
    "игры": ["игры", "игра", "игру", "игре", "игр", "игрульки"],
    "кладмен": ["кладмен", "кладмена", "кладмену", "клад", "клады"],
    "продать": ["продать", "продажи", "продать", "продал", "продам"],
    "магазин": ["магазин", "магазину", "магазина", "магазине", "шоп"],
    "имущество": ["имущество", "имущества", "имуществу", "имуществе", "им"],
    "банк": ["банк", "банка", "банку", "банке", "банки"],
    "вклад": ["вклад", "вклады", "вкладу", "вклада", "вкладах"],
    "краш": ["краш", "краша", "крашу", "краше", "крашик", "crash"],
    "кликер": ["кликер", "кликеру", "кликера", "кликере", "жмак", "жмакер", "клик", "clicker"],
    "репорт": ["репорт", "репорта", "репорту", "репорте", "поддержка", "support"],
    "монетка": ["монетка", "монетку", "монетки", "монетке", "монеточка", "монеточ", "монет"],
    "бонус": ["бонус", "бонуса", "бонусу", "бонусы"],
    "топ": ["топ", "топы", "топу", "топов", "топа", "топ по балансу", "топ рефералов"],
    "профиль": ["профиль", "профиля", "профилю", "профиле", "profile", "я", "яша"],
    "ник": ["ник", "имя", "сменить ник", "сменить имя", "изменить имя"],
    "кликабельность": ["кликабельность", "кликабельный", "кликабельность ника"],
    "help": ["help", "команды", "помощь", "справка", "all commands"],
}



router = Router()
dp = Dispatcher(storage=MemoryStorage())
bets = {}
user_names = {}
game_ids = {}
user_data_file = os.path.join(os.path.dirname(__file__), "users.json")
last_bonus_time = {}
dp.include_router(roulette_router)
dp.include_router(shop_router)
available_topics = ["рулетка"]
BANK_DEPOSIT_LIMIT = 1_000_000
BOT_NAME = "GameBot"  # Замените на своё название, если нужно
REPORTS_FILE = os.path.join(os.path.dirname(__file__), "reports.json")
REPORTS_STATE = {}


class SellState(StatesGroup):
    waiting_for_confirmation = State()

class AdminInfoState(StatesGroup):
    waiting_for_user_id = State()


class AdminGiveMoneyState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

class BankDepositState(StatesGroup):
    waiting_for_deposit_amount = State()

class AdminSetState(StatesGroup):
    waiting_for_choice = State()
    waiting_for_user_id = State()
    waiting_for_value = State()
    waiting_for_confirmation = State()


class AdminResetState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_confirmation = State()


class Reg(StatesGroup):
    waiting_for_name = State()


class SettingsState(StatesGroup):
    waiting_for_new_name = State()


class BankSaveState(StatesGroup):
    waiting_for_bank_save_add = State()
    waiting_for_bank_save_withdraw = State()
    

@dp.message(CommandStart())
async def send_welcome(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    tg_first_name = message.from_user.first_name
    username = message.from_user.username
    if username:
        update_telegram_username(user_id, username)
    args = command.args
    user = get_user(user_id)
    # Если у пользователя ещё нет имени — ставим Telegram first_name
    if not user.get("name"):
        set_name(user_id, tg_first_name)
        user["name"] = tg_first_name
        save_user_data()
    if args and args.startswith("ref"):
        referrer_id = args[3:]
        if referrer_id.isdigit() and int(referrer_id) != user_id:
            referrer_id = int(referrer_id)
            referrer = get_user(referrer_id)
            if referrer:
                user["referrer"] = referrer_id
                referrer["referrals"].append(user_id)
                save_user_data()
                referrer_bonus = 10000
                update_balance(referrer_id, get_balance(referrer_id) + referrer_bonus)
                invited_bonus = 5000
                update_balance(user_id, get_balance(user_id) + invited_bonus)
                await message.answer(
                    f"🎉 Вы были приглашены пользователем {clickable_name(referrer_id, referrer['name'])}!\n"
                    f"Он получил <b>{referrer_bonus}$</b> за приглашение, а вы получили <b>{invited_bonus}$</b>!",
                    reply_markup=safe_reply_kb(message, menu_kb),
                    parse_mode="HTML"
                )
    start_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать", callback_data="show_menu")]
        ]
    )
    await message.answer(
        f"👋 Добро пожаловать, {clickable_name(user_id, user.get('name', tg_first_name))}!\n"
        f"Это <b>{BOT_NAME}</b> — твой игровой и экономический помощник.\n\n"
        f"Нажмите <b>Начать</b>, чтобы открыть меню.\n\n"
        f"Если пропали кнопки напишите <code>меню</code>",
        reply_markup=start_kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "show_menu")
async def show_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text("Меню:", reply_markup=menu_kb)
    await callback.answer()




@dp.message(F.reply_to_message, F.text.lower().startswith("передать"))
async def transfer_money_reply(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    reply = message.reply_to_message
    recipient_id = reply.from_user.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            f"❌ {clickable_name(user_id, name)}, укажите сумму. Пример: <code>передать 1000</code>",
            parse_mode="HTML"
        )
        return
    amount_text = parts[1].strip()
    sender_balance = get_balance(user_id)
    amount = sender_balance if amount_text.lower() == "все" else parse_k(amount_text)
    if amount is None or amount <= 0 or sender_balance < amount:
        await message.answer(
            f"❌ {clickable_name(user_id, name)}, недостаточно средств или некорректная сумма.",
            parse_mode="HTML"
        )
        return
    recipient = get_user(recipient_id)
    if not recipient:
        await message.answer(
            f"❌ Получатель не найден. Пусть он напишет боту /start.",
            parse_mode="HTML"
        )
        return
    update_balance(user_id, sender_balance - amount)
    update_balance(recipient_id, get_balance(recipient_id) + amount)
    save_user_data()
    await message.answer(
        f"✅ {clickable_name(user_id, name)} перевёл <b>{amount}$</b> пользователю {clickable_name(recipient_id, recipient.get('name', 'Без имени'))}.",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            recipient_id,
            f"💸 {clickable_name(user_id, name)} перевёл вам <b>{amount}$</b>!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    

    
    
@dp.message(F.text.lower().in_(["баланс", "балик", "💰 баланс", 'balance', 'б']))
async def show_balance(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    balance = get_balance(user_id)
    await message.answer(
        f"💰 Баланс {clickable_name(user_id, name)}: <b>{format_amount(balance)}$</b>",
        parse_mode="HTML"
    )


@dp.message(F.text.lower().in_(["🎁 бонус", "бонус"]))
async def bonus_command(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    current_time = time.time()
    last_bonus_time = user.get("last_bonus_time", 0)
    elapsed_time = current_time - last_bonus_time
    if elapsed_time < 3600:
        remaining_time = int((3600 - elapsed_time) / 60)
        await message.answer(
            f"❌ {clickable_name(user_id, name)}, вы уже получали бонус.\n"
            f"Попробуйте через <b>{remaining_time}</b> мин.",
            parse_mode="HTML"
        )
        return
    bonus_amount = 1000
    update_balance(user_id, get_balance(user_id) + bonus_amount)
    user["last_bonus_time"] = current_time
    save_user_data()
    await message.answer(
        f"🎉 {clickable_name(user_id, name)}, вы получили бонус: <b>{bonus_amount}$</b>!\n"
        f"💰 Новый баланс: <b>{format_amount(get_balance(user_id))}$</b>",
        parse_mode="HTML"
    )

@dp.message(F.text.lower().in_(["реф", "реферальная система", "рефка", "/ref", "🔗 реферальная система"]))
async def send_referral_link(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    referral_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    if message.chat.type == "private":
        await message.answer(
            f"🔗 {clickable_name(user_id, name, clickable)} ваша реферальная ссылка:\n{referral_link}\n\n"
            "Приглашайте друзей и получайте бонусы за каждого приглашенного!",
            reply_markup=safe_reply_kb(message, ref_kb),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🔗 {clickable_name(user_id, name, clickable)} ваша реферальная ссылка:\n{referral_link}\n\n"
            "Приглашайте друзей и получайте бонусы за каждого приглашенного!\n\n"
            "Клавиатура доступна только в личных сообщениях с ботом.",
            parse_mode="HTML"
        )


@dp.message(F.text.lower().startswith("помощь"))
async def help_command(message: Message):
    text = message.text.lower().replace("ё", "е").split()
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    if len(text) < 2:
        await message.answer(
            f"❓ {clickable_name(message.from_user.id, name, clickable)}, укажите тему или команду для получения инструкции.\n\n"
            "📌 <b>Пример:</b> <code>помощь рулетка</code>\n"
            "📋 Для списка всех команд: <code>команды</code>\n\n"
            "💡 Если нашли баг или есть предложение — напишите <b>репорт</b> или <b>поддержка</b> и ваш текст.\n"
            "✉️ Пример: <code>репорт не работает банк</code>",
            parse_mode="HTML",
        )
        return

    topic = text[1]
    # Поиск по синонимам
    found_key = None
    for key, synonyms in help_synonyms.items():
        if topic in synonyms:
            found_key = key
            break

    help_texts = {
        "рулетка": roulette_help_text,
        "передать": transfer_help_text,
        "работа": work_help_text,
        "шахтер": miner_help_text,
        "дворник": dvor_help_text,
        "игры": games_help_text,
        "кладмен": cladman_help_text,
        "продать": sell_help_text,
        "магазин": shop_help_text,
        "имущество": assets_help_text,
        "банк": bank_help_text,
        "вклад": deposit_help_text,
        "краш": crash_help_text,
        "кликер": clicker_help_text,
        "репорт": report_help_text,
        "монетка": coin_help_text,
        "бонус": bonus_help_text,
        "топ": top_help_text,
        "профиль": profile_help_text,
        "ник": profile_help_text,
        "кликабельность": profile_help_text,
        "help": all_commands_text,
    }

    if found_key and found_key in help_texts:
        await message.answer(help_texts[found_key], parse_mode="HTML")
    else:
        await message.answer(
            f"❌ {clickable_name(message.from_user.id, name, clickable)}, нет инструкции по теме: {topic}\n"
            "Для списка всех команд используйте <code>команды</code>.",
            parse_mode="HTML"
        )


@dp.message(F.text.lower().in_(["команды", "список команд", "all commands"]))
async def all_commands_handler(message: Message):
    await message.answer(all_commands_text, parse_mode="HTML")


@dp.message(F.text.lower().in_(["✏️ изменить имя", "изменить имя"]))
async def change_name_prompt(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    await message.answer("Введите новое имя:")
    await state.set_state(SettingsState.waiting_for_new_name)


@dp.message(
    F.text.lower().in_(["рефералы", "мои рефералы", "/referrals", "👥 рефералы"])
)
async def show_referrals(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    referrals = user.get("referrals", [])
    if not referrals:
        await message.answer(
            f"❌ {clickable_name(user_id, name)}, у вас пока нет приглашённых пользователей.",
            parse_mode="HTML"
        )
        return

    referral_list = ""
    for i, ref in enumerate(referrals):
        ref_user = get_user(ref)
        if not ref_user:
            continue  # Пропускаем несуществующих пользователей
        ref_name = ref_user.get("name", "Без имени")
        referral_list += f"{i + 1}. {clickable_name(ref, ref_name)} — {get_balance(ref)}$\n"

    if not referral_list:
        referral_list = "Нет активных приглашённых пользователей."

    await message.answer(
        f"👥 {clickable_name(user_id, name)}, ваши приглашённые пользователи:\n\n{referral_list}",
        reply_markup=safe_reply_kb(message, menu_kb),
        parse_mode="HTML"
    )


@dp.message(SettingsState.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    new_name = message.text.strip()
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    if len(new_name) > 30:
        await message.answer("❌ Имя слишком длинное. Максимум 30 символов.")
        return

    set_name(user_id, new_name)  # Сохраняем новое имя
    await message.answer(f"✅ Ваше имя изменено на: {new_name}", reply_markup=safe_reply_kb(message, menu_kb))
    await state.clear()


@dp.message(F.text.lower().in_(["топ рефералов", "топ реф"]))
async def show_top_referrals(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени") if user else "Без имени"
    clickable = user.get("clickable_name", True) if user else True
    sorted_users = sorted(
        utils.user_data.items(),
        key=lambda x: len(x[1].get("referrals", [])),
        reverse=True,
    )
    top_users = sorted_users[:10]
    all_ids = [uid for uid, _ in sorted_users]

    if not top_users:
        top_text = "❌ Нет данных о рефералах."
    else:
        top_text = f"🏆 <b>{clickable_name(user_id, name, clickable)}</b>:\n<b>Топ пользователей по количеству рефералов:</b>\n\n"
        for i, (uid, data) in enumerate(top_users, start=1):
            uname = data.get("name", "Без имени")
            top_clickable = data.get("clickable_name", True)
            referrals_count = len(data.get("referrals", []))
            top_text += f"{i}. {clickable_name(uid, uname, top_clickable)} — {referrals_count} рефералов\n"
        if user_id not in [uid for uid, _ in top_users]:
            place = all_ids.index(user_id) + 1 if user_id in all_ids else None
            if place:
                top_text += f"\nВаше место: {place} из {len(all_ids)}"

    await message.answer(top_text, parse_mode="HTML", reply_markup=top_ref_kb)


@dp.message(F.text.lower().in_(["топ по балансу", "топ балик"]))
async def show_top_rich(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    sorted_users = sorted(
        utils.user_data.items(),
        key=lambda x: x[1].get("balance", 0),
        reverse=True,
    )
    top_users = sorted_users[:10]
    all_ids = [uid for uid, _ in sorted_users]

    if not top_users:
        top_text = "❌ Нет данных о пользователях."
    else:
        top_text = "<b>🏆 Топ пользователей по балансу:</b>\n\n"
        for i, (uid, data) in enumerate(top_users, start=1):
            uname = data.get("name", "Без имени")
            balance = data.get("balance", 0)
            top_text += f"{i}. {clickable_name(uid, uname, data.get('clickable_name', True))} — {format_amount(balance)}$\n"
        if user_id not in [uid for uid, _ in top_users]:
            place = all_ids.index(user_id) + 1 if user_id in all_ids else None
            if place:
                top_text += f"\nВаше место: {place} из {len(all_ids)}"

    await message.answer(top_text, parse_mode="HTML", reply_markup=top_balance_kb)




@dp.message(F.text.lower() == "жопа")
async def handle_caczka_command(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Жопа", callback_data="жопа")]
        ]
    )
    await message.answer("ㅤ", reply_markup=keyboard)

@dp.callback_query(F.data == "жопа")
async def handle_caczka_callback(callback: CallbackQuery):
    await callback.answer("ㅤ\nㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤЖопа", show_alert=True)


@dp.message(F.text.lower().in_(["🏆 топ", "топ"]))
async def show_top(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    # Если имя не найдено — fallback на Telegram first_name
    name = user.get("name") if user and user.get("name") else message.from_user.first_name
    clickable = user.get("clickable_name", True) if user else True

    text = message.text.lower()
    if "реф" in text or "по рефералам" in text:
        await show_top_referrals(message)
    else:
        # Передаём имя и кликабельность явно
        await show_top_rich(message, name, clickable)

# Исправленный show_top_rich с поддержкой передачи имени и кликабельности
async def show_top_rich(message: Message, name=None, clickable=True):
    user_id = message.from_user.id
    if name is None or clickable is None:
        user = get_user(user_id)
        name = user.get("name") if user and user.get("name") else message.from_user.first_name
        clickable = user.get("clickable_name", True) if user else True
    sorted_users = sorted(
        utils.user_data.items(),
        key=lambda x: x[1].get("balance", 0),
        reverse=True,
    )
    top_users = sorted_users[:10]
    all_ids = [uid for uid, _ in sorted_users]

    if not top_users:
        top_text = "❌ Нет данных о пользователях."
    else:
        top_text = f"<b>🏆 {clickable_name(user_id, name, clickable)}</b>:\n<b>Топ пользователей по балансу:</b>\n\n"
        for i, (uid, data) in enumerate(top_users, start=1):
            uname = data.get("name", "Без имени")
            top_clickable = data.get("clickable_name", True)
            balance = data.get("balance", 0)
            top_text += f"{i}. {clickable_name(uid, uname, top_clickable)} — {format_amount(balance)}$\n"
        if user_id not in [uid for uid, _ in top_users]:
            place = all_ids.index(user_id) + 1 if user_id in all_ids else None
            if place:
                top_text += f"\nВаше место: {place} из {len(all_ids)}"

    await message.answer(top_text, parse_mode="HTML", reply_markup=top_balance_kb)


@dp.callback_query(F.data == "top_balance")
async def show_top_balance_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user.get("name") if user and user.get("name") else callback.from_user.first_name
    clickable = user.get("clickable_name", True) if user else True
    sorted_users = sorted(
        utils.user_data.items(),
        key=lambda x: x[1].get("balance", 0),
        reverse=True,
    )
    top_users = sorted_users[:10]
    all_ids = [int(uid) for uid, _ in sorted_users]

    if not top_users:
        top_text = "❌ Нет данных о пользователях."
    else:
        top_text = f"<b>🏆 {clickable_name(user_id, name, clickable)}</b>:\n<b>Топ пользователей по балансу:</b>\n\n"
        for i, (uid, data) in enumerate(top_users, start=1):
            uname = data.get("name", "Без имени")
            top_clickable = data.get("clickable_name", True)
            balance = data.get("balance", 0)
            top_text += f"{i}. {clickable_name(int(uid), uname, top_clickable)} — {format_amount(balance)}$\n"
        if user_id not in [int(uid) for uid, _ in top_users]:
            place = all_ids.index(user_id) + 1 if user_id in all_ids else None
            if place:
                top_text += f"\nВаше место: {place} из {len(all_ids)}"

    await callback.message.edit_text(top_text, parse_mode="HTML", reply_markup=top_balance_kb)
    await callback.answer()

@dp.callback_query(F.data == "top_ref")
async def show_top_ref_callback(callback: CallbackQuery):
    # Используем тот же код, что и выше, только для callback.message
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user.get("name") if user and user.get("name") else callback.from_user.first_name
    clickable = user.get("clickable_name", True) if user else True
    sorted_users = sorted(
        utils.user_data.items(),
        key=lambda x: len(x[1].get("referrals", [])),
        reverse=True,
    )
    top_users = sorted_users[:10]
    all_ids = [int(uid) for uid, _ in sorted_users]

    if not top_users:
        top_text = "❌ Нет данных о рефералах."
    else:
        top_text = f"🏆 <b>{clickable_name(user_id, name, clickable)}</b>:\n<b>Топ пользователей по количеству рефералов:</b>\n\n"
        for i, (uid, data) in enumerate(top_users, start=1):
            uname = data.get("name", "Без имени")
            top_clickable = data.get("clickable_name", True)
            referrals_count = len(data.get("referrals", []))
            top_text += f"{i}. {clickable_name(int(uid), uname, top_clickable)} — {referrals_count} рефералов\n"
        if user_id not in [int(uid) for uid, _ in top_users]:
            place = all_ids.index(user_id) + 1 if user_id in all_ids else None
            if place:
                top_text += f"\nВаше место: {place} из {len(all_ids)}"

    await callback.message.edit_text(top_text, parse_mode="HTML", reply_markup=top_ref_kb)
    await callback.answer()



@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery):
    await callback.message.answer("Меню:", reply_markup=safe_reply_kb(callback.message, menu_kb))
    await callback.answer()

@dp.message(F.text.lower().in_(["🔗 кликабельность ника", "кликабельность ника"]))
async def toggle_clickable_name(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    # Переключаем состояние кликабельности
    user["clickable_name"] = not user.get("clickable_name", True)
    save_user_data()

    # Отправляем сообщение о текущем состоянии
    if user["clickable_name"]:
        await message.answer(
            "✅ Кликабельность ника включена.", reply_markup=safe_reply_kb(message, settings_kb)
        )
    else:
        await message.answer(
            "❌ Кликабельность ника отключена.", reply_markup=safe_reply_kb(message, settings_kb)
        )
        

@dp.message(F.text.lower().in_(["Жмак", "жмак", "жмяк", "клик", "👆 жмак"]))
async def click(message: Message):
    user_id = message.from_user.id
    balance = get_balance(user_id) + 1
    update_balance(user_id, balance)
    await message.answer("+1$", reply_markup=safe_reply_kb(message, click_kb))


@dp.message(F.text.lower().in_(["кликер", "clicker", "жмакер", "👆 жмакер"]))
async def show_clicker(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    await message.answer(
        f"🎮 Кликер для {clickable_name(user_id, name, clickable)}:\n"
        "👆 Жмакай <code>жмак</code> чтобы получить +1$ к балансу\n"
        "💰 Проверить баланс: <code>баланс</code>",
        parse_mode="HTML",
        reply_markup=safe_reply_kb(message, click_kb),
    )
    
    
    
@dp.message(F.text.lower().in_(["🎰 рулетка", "рулетка"]))
async def roulette_instruction(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    await message.answer(
        f"🎰 {clickable_name(message.from_user.id, name, clickable)} — инструкция по рулетке:\n"
        "Напиши: <code>рулетка [тип ставки] [сумма]</code>\n"
        "Пример: <code>рулетка красное 1000</code>\n"
        "Подробнее: <code>помощь рулетка</code>",
        parse_mode="HTML"
    )
    

@dp.message(F.text.lower().in_(["💥 краш", "краш"]))
async def crash_instruction(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    await message.answer(
        f"💥 {clickable_name(message.from_user.id, name, clickable)} — инструкция по крашу:\n"
        "Напиши: <code>краш [коэффициент] [сумма]</code>\n"
        "Пример: <code>краш 2.5 1000</code>\n"
        "Подробнее: <code>помощь краш</code>",
        parse_mode="HTML"
    )


@dp.message(F.text.lower().in_(["profile", "профиль", "проф", "я", "z", "👤 профиль"]))
async def show_profile(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    if username:
        update_telegram_username(user_id, username)
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    game_id = user.get("game_id", "Не указан")
    balance = get_balance(user_id)

    profile_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Имущество", callback_data="show_assets_from_profile")]
        ]
    )

    await message.answer(
        f"{clickable_name(user_id, name, clickable)},\n"
        f"👤 Ваш профиль:\n"
        f"Имя: {name}\n"
        f"🆔: <code>{game_id}</code>\n"
        f"💰 Баланс: {format_amount(balance)}$",
        reply_markup=profile_kb,
        parse_mode="HTML",
    )
    
    
@dp.callback_query(F.data == "show_assets_from_profile")
async def show_assets_from_profile_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    assets_text = get_assets_text(user)
    sell_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Продать имущество", callback_data="sell_assets")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_profile")],
        ]
    )
    await callback.message.edit_text(
        f"📦 {clickable_name(user_id, name, clickable)} ваше имущество:\n{assets_text}",
        reply_markup=sell_kb,
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "show_assets")
async def show_assets_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    assets_text = get_assets_text(user)
    sell_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Продать имущество", callback_data="sell_assets")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_profile")],
        ]
    )
    await callback.message.edit_text(
        f"📦 {clickable_name(user_id, name, clickable)} ваше имущество:\n{assets_text}",
        reply_markup=sell_kb,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_profile")
async def back_to_profile_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    update_telegram_username(user_id, username)
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    game_id = user.get("game_id", "Не указан")
    balance = get_balance(user_id)

    profile_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Имущество", callback_data="show_assets_from_profile")]
        ]
    )

    await callback.message.edit_text(
        f"{clickable_name(user_id, name, clickable)},\n"
        f"👤 Ваш профиль:\n"
        f"Имя: {name}\n"
        f"🆔: <code>{game_id}</code>\n"
        f"💰 Баланс: {balance}$",
        reply_markup=profile_kb,
        parse_mode="HTML",
    )
    await callback.answer()

@dp.callback_query(F.data == "sell_assets")
async def sell_assets_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    # Собираем список имущества для продажи
    assets = []
    for cat in SHOP_ITEMS.keys():
        item = user.get(cat)
        if item:
            emoji = ASSET_EMOJIS.get(cat, "")
            assets.append((cat, item, emoji))
    if not assets:
        await callback.answer("У вас нет имущества для продажи.", show_alert=True)
        return
    # Формируем инлайн-клавиатуру для продажи каждого предмета
    sell_buttons = [
        [InlineKeyboardButton(text=f"{emoji} {item}", callback_data=f"sell_{cat}")]
        for cat, item, emoji in assets
    ]
    sell_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="show_assets")])
    kb = InlineKeyboardMarkup(inline_keyboard=sell_buttons)
    await callback.message.edit_text(
        f"{clickable_name(user_id, name, clickable)}, выберите, что хотите продать:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sell_"))
async def confirm_sell_asset(callback: CallbackQuery):
    user_id = callback.from_user.id
    cat = callback.data.replace("sell_", "")
    user = get_user(user_id)
    item_name = user.get(cat)
    if not item_name:
        await callback.answer("У вас нет этого имущества.", show_alert=True)
        return
    price = next((item["price"] for item in SHOP_ITEMS[cat] if item["name"] == item_name), None)
    if not price:
        await callback.answer("Ошибка при продаже.", show_alert=True)
        return
    sell_price = int(price * 0.6)
    update_balance(user_id, get_balance(user_id) + sell_price)
    user[cat] = None
    save_user_data()
    await callback.message.edit_text(
        f"Вы продали {item_name} за {sell_price}$!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="show_assets")],
            ]
        ),
        parse_mode="HTML"
    )



@dp.message(
    F.text.lower().in_(["настройки", "settings", "/settings", "/setting", "настройка", "⚙️ настройки"])
)
async def show_settings(message: Message):
    if message.chat.type == "private":
        await message.answer("⚙️ Настройки:", reply_markup=safe_reply_kb(message, settings_kb)
        )
    else:
        await message.answer("⚙️ Настройки доступны только в личных сообщениях с ботом.")


@dp.message(F.text.lower().in_(["menu", "меню", "менюшка", "/menu", "🏠 меню", 'м', 'm']))
async def show_menu(message: Message):
    if message.chat.type == "private":
        await message.answer("Меню:", reply_markup=safe_reply_kb(message, menu_kb))
    else:
        await message.answer("Меню доступно только в личных сообщениях с ботом.")


@dp.message(F.text.lower().in_(["игры", "games", "игрульки", "🎮 игры"]))
async def show_games(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    games_text = (
        f"🎮 {clickable_name(user_id, name, clickable)}, вот доступные игры:\n\n"
        "• 🎰 <b>Рулетка</b> — угадай цвет или число и выиграй!\n"
        "   Пример: <code>рулетка красное 1000</code>\n"
        "• 💥 <b>Краш</b> — угадай коэффициент и забери выигрыш!\n"
        "   Пример: <code>краш 2.5 1000</code>\n"
        "• 🪙 <b>Монетка</b> — брось вызов: выбери орёл или решка, поставь сумму и жди соперника!\n"
        "   Пример: <code>монетка орел 1000</code>\n"
        "• 👆 <b>Кликер</b> — жми <code>жмак</code> и получай деньги!\n"
        "• 💼 <b>Работа</b> — выбери профессию и зарабатывай!\n"
        "• 📦 <b>Имущество</b> — покупай и продавай активы в магазине.\n"
        "\nДля подробной инструкции по игре напиши <code>помощь [игра]</code>.\n"
        "Например: <code>помощь монетка</code>"
    )
    if message.chat.type == "private":
        await message.answer(
            games_text,
            parse_mode="HTML",
            reply_markup=safe_reply_kb(message, games_kb),
        )
    else:
        await message.answer(
            f"🎮 {clickable_name(user_id, name, clickable)}, клавиатура доступна только в личных сообщениях с ботом.",
            parse_mode="HTML"
        )
        
        
@dp.message(F.text.lower().in_(["🪙 монетка"]))
async def coin_game_instruction(message: Message):
    await message.answer(
        "🪙 <b>Монетка</b> — игра на удачу между двумя игроками!\n\n"
        "1. Создай игру: <code>монетка орел 1000</code> или <code>монетка решка все</code>\n"
        "2. Жди соперника или отправь <code>монетка</code> для просмотра списка игр\n"
        "3. Чтобы принять игру: <code>монетка 1</code> (где 1 — номер игры)\n\n"
        "Победитель определяется случайно. Если угадаешь сторону — получишь удвоенную ставку!",
        parse_mode="HTML"
    )
        


@dp.message(F.text.lower().startswith("ник"))
async def change_name_command(message: Message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "❌ Укажите новое имя. Пример: <code>ник Иван</code>", parse_mode="HTML"
        )
        return

    new_name = parts[1].strip()

    if len(new_name) > 30:
        await message.answer("❌ Имя слишком длинное. Максимум 30 символов.")
        return

    set_name(user_id, new_name)
    await message.answer(f"✅ Ваше имя изменено на: {new_name}", reply_markup=safe_reply_kb(message, menu_kb))
    


@dp.message(F.text.lower().in_(["💼 работа", "работа", 'работы']))
async def start_work(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    text = (
        f"💼 {clickable_name(message.from_user.id, name, clickable)}, выберите работу:\n\n"
        "🧹 Дворник — убирайте мусор и зарабатывайте деньги!\n"
        "⛏️ Шахтёр — добывайте ресурсы и зарабатывайте деньги!\n"
        "💰 Кладмен — ищите клады и продавайте их!"
    )
    await message.answer(text, reply_markup=work_kb, parse_mode="HTML")



@dp.message(F.text.lower().in_(["❓ помощь"]))
async def help_short(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    await message.answer(
        f"❓ {clickable_name(message.from_user.id, name, clickable)}, укажите тему или команду для получения инструкции.\n"
        "Пример: <code>помощь рулетка</code>\n"
        "Для списка всех команд используйте <code>команды</code>.\n"
        "Если вы нашли баг или у вас есть предложение по улучшению бота — напишите в поддержку.\n"
        "Команда: Репорт (сообщение)\n",
        parse_mode="HTML",
    )


@dp.message(F.text.lower().in_(["кладмен", "клад", "💰 кладмен"]))
async def start_cladman_work(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    keyboard, available_emojis = generate_cladman_keyboard()
    user["available_emojis"] = available_emojis
    user["current_work"] = "cladman"
    save_user_data()
    if message.chat.type == "private":
        await message.answer(
            f"💰 {clickable_name(user_id, name, clickable)}, вы начали работу кладменом!\n\n"
            "Найдите клад и продайте его, чтобы получить деньги. Нажмите на один из смайликов ниже:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"💰 {clickable_name(user_id, name, clickable)}, вы начали работу кладменом!\n\n"
            "Найдите клад и продайте его, чтобы получить деньги. (Клавиатура доступна только в личных сообщениях с ботом!)",
            parse_mode="HTML"
        )


@dp.message(F.text.in_(["💎", "📿", "🪙", "🪵", "🪞", "🪶", "🪔", "🪄", "🪓", "🪤"]))
async def handle_cladman_choice(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    # Проверяем, находится ли пользователь в работе кладменом
    if user.get("current_work") != "cladman":
        await message.answer("❌ Этот смайлик недоступен для работы кладменом. Напишите `кладмен`, чтобы начать работу.")
        return

    # Проверяем, есть ли доступные смайлики
    available_emojis = user.get("available_emojis", [])
    if not available_emojis:
        await message.answer("❌ У вас нет доступных кладов. Напишите `кладмен`, чтобы начать работу.")
        return

    choice = message.text.strip()

    # Проверяем, выбран ли смайлик из доступных
    if choice not in available_emojis:
        await message.answer("❌ Этот клад недоступен. Выберите смайлик с клавиатуры.")
        return

    # Определяем ценность выбранного смайлика
    item_values = {
        "💎": 100,
        "📿": 50,
        "🪙": 10,
        "🪵": 5,
        "🪞": 20,
        "🪶": 15,
        "🪔": 30,
        "🪄": 40,
        "🪓": 25,
        "🪤": 35,
    }
    reward = item_values.get(choice, 0)

    # Увеличиваем баланс пользователя
    balance = get_balance(user_id) + reward
    update_balance(user_id, balance)

    await message.answer(
        f"✅ Вы продали {choice} за {reward}$!\n"
        f"💰 Ваш текущий баланс: {balance}$",
    )

    # Генерируем новую клавиатуру
    keyboard, available_emojis = generate_cladman_keyboard()

    # Сохраняем новые доступные смайлики
    user["available_emojis"] = available_emojis
    save_user_data()

    await message.answer(
        "Выберите следующий клад:",
        reply_markup=keyboard,
    )


def generate_cladman_keyboard():
    items = [
        {"emoji": "💎", "value": 100, "probability": 5},  # Очень дорогой предмет
        {"emoji": "📿", "value": 50, "probability": 10},  # Дорогой предмет
        {"emoji": "🪙", "value": 10, "probability": 30},  # Средний предмет
        {"emoji": "🪵", "value": 5, "probability": 40},   # Дешевый предмет
        {"emoji": "🪞", "value": 20, "probability": 15},  # Средний предмет
        {"emoji": "🪶", "value": 15, "probability": 20},  # Средний предмет
        {"emoji": "🪔", "value": 30, "probability": 10},  # Дорогой предмет
        {"emoji": "🪄", "value": 40, "probability": 8},   # Дорогой предмет
        {"emoji": "🪓", "value": 25, "probability": 12},  # Средний предмет
        {"emoji": "🪤", "value": 35, "probability": 7},   # Дорогой предмет
    ]

    # Генерируем список смайликов на основе вероятностей
    emojis = random.choices(
        [item["emoji"] for item in items],
        weights=[item["probability"] for item in items],
        k=10,  # Количество кнопок на клавиатуре
    )

    # Создаем клавиатуру (2 ряда по 5 кнопок)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=emojis[i]) for i in range(5)],
            [KeyboardButton(text=emojis[i]) for i in range(5, 10)],
        ],
        resize_keyboard=True,
    )

    return keyboard, emojis




@dp.message(F.text.lower().in_(["🧹 дворник", "дворник"]))
async def start_dvor_work(message: Message):
    correct_emoji = random.choice(["🗑️", "♻️", "🧹", "🚮", "🪠", "🧼"])
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    user["correct_emoji"] = correct_emoji
    user["current_work"] = "dvor"
    save_user_data()
    if message.chat.type == "private":
        await message.answer(
            f"🧹 {clickable_name(user_id, name, clickable)}, вы начали работу дворником!\n\n"
            f"Найдите правильный смайлик: {correct_emoji}",
            reply_markup=generate_work_keyboard(correct_emoji),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🧹 {clickable_name(user_id, name, clickable)}, вы начали работу дворником!\n\n"
            f"(Клавиатура доступна только в личных сообщениях с ботом!)",
            parse_mode="HTML"
        )


@dp.message(F.text.in_(["🗑️", "♻️", "🧹", "🚮", "🪠", "🧼"]))
async def handle_work_choice(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    # Проверяем, находится ли пользователь в работе дворником
    if user.get("current_work") != "dvor":
        await message.answer("❌ Этот смайлик недоступен для работы дворником. Напишите `дворник`, чтобы начать работу.")
        return

    # Проверяем, есть ли сохранённый правильный смайлик
    correct_emoji = user.get("correct_emoji")
    if not correct_emoji:
        return  # Если пользователь не начал работу, ничего не делаем

    choice = message.text.strip()

    if choice == correct_emoji:
        # Увеличиваем баланс пользователя
        balance = get_balance(user_id) + 50
        update_balance(user_id, balance)
        await message.answer(
            f"✅ Вы выбрали правильный смайлик и заработали 50$!\n"
            f"💰 Ваш текущий баланс: {balance}$",
        )
        # Предлагаем продолжить работу
        correct_emoji = random.choice(["🗑️", "♻️", "🧹", "🚮", "🪠", "🧼"])
        user["correct_emoji"] = correct_emoji
        save_user_data()
        await message.answer(
            f"Найдите правильный смайлик: {correct_emoji}",
            reply_markup=generate_work_keyboard(correct_emoji),
        )
    else:
        await message.answer(
            "❌ Неправильный выбор. Попробуйте снова!",
            reply_markup=generate_work_keyboard(correct_emoji),
        )


@dp.message(F.text.lower().in_(["⛏️ шахтёр", "шахтёр", "шахтер", "⛏️ шахтер"]))
async def start_mining_work(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    await message.answer(
        f"⛏️ {clickable_name(message.from_user.id, name, clickable)}, вы начали работу шахтёром!\n\n"
        "Выберите шахту для добычи ресурсов:\n"
        "1️⃣ Малая шахта — низкий риск, низкая награда.\n"
        "2️⃣ Средняя шахта — средний риск, средняя награда.\n"
        "3️⃣ Глубокая шахта — высокий риск, высокая награда.",
        reply_markup=safe_reply_kb(message, mining_kb),
    )


@dp.message(
    F.text.in_(
        [
            "⛏️ Малая шахта",
            "Малая шахта",
            "⛏️ Средняя шахта",
            "Средняя шахта",
            "⛏️ Глубокая шахта",
            "Глубокая шахта",
        ]
    )
)
async def handle_mining_choice(message: Message):
    user_id = message.from_user.id
    choice = message.text

    if choice in ["⛏️ Малая шахта", "Малая шахта"]:
        reward = random.choices(
            ["уголь", "золото", "ничего"],
            weights=[50, 20, 30],
            k=1,
        )[0]
        reward_amount = random.randint(2, 5)
    elif choice in ["⛏️ Средняя шахта", "Средняя шахта"]:
        reward = random.choices(
            ["уголь", "золото", "алмазы", "ничего"],
            weights=[30, 20, 10, 40],
            k=1,
        )[0]
        reward_amount = random.randint(5, 10)
    elif choice in ["⛏️ Глубокая шахта", "Глубокая шахта"]:
        reward = random.choices(
            ["уголь", "золото", "алмазы", "ничего"],
            weights=[8, 17, 25, 50],
            k=1,
        )[0]
        reward_amount = random.randint(10, 20)

    if reward == "ничего":
        await message.answer(
            "😢 Вы ничего не нашли. Попробуйте снова!", reply_markup=safe_reply_kb(message, mining_kb)
        )
    else:
        balance = get_balance(user_id) + reward_amount
        update_balance(user_id, balance)
        await message.answer(
            f"🎉 Вы нашли {reward} и заработали {reward_amount}$!\n"
            f"💰 Ваш текущий баланс: {balance}$",
            reply_markup=safe_reply_kb(message, mining_kb),
        )

@dp.message(F.text.lower().in_(["имущество", "им"]))
async def show_assets_command(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    assets_text = get_assets_text(user)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Продать имущество", callback_data="sell_assets")],
        ]
    )
    await message.answer(
        f"📦 {clickable_name(user_id, name, clickable)} ваше имущество:\n{assets_text}",
        reply_markup=kb,
        parse_mode="HTML"
    )


@dp.message(F.text.lower().in_(["банк", "bank", "/bank", "🏦 банк"]))
async def show_bank_menu(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    bank_sum = user.get('user_bank', 0)
    await message.answer(
        f"🏦 <b>Банк {clickable_name(message.from_user.id, name, clickable)}</b>\n\n"
        f"📦 <b>Счёт:</b> <code>{format_amount(bank_sum)}$</code>\n\n\n"
        "➕ <b>Пополнить</b>: <code>банк (сумма)</code>\n"
        "➖ <b>Снять</b>: <code>банк -(сумма)</code>\n",
        parse_mode="HTML",
        reply_markup=get_bank_main_kb()
    )


@dp.callback_query(F.data == "bank_deposits")
async def bank_deposits_callback(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    deposits = user.get("user_deposits", [])
    text = "📈 <b>Ваши вклады:</b>\n\n"
    total = 0
    if not deposits:
        text += "Нет активных вкладов.\n"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать вклад", callback_data="create_deposit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
            ]
        )
    else:
        for i, dep in enumerate(deposits, 1):
            text += (
            f"{i}. {format_amount(dep['amount'])}$ — {dep['days']} дн., {dep['percent']}%/день\n"
        )
            total += dep['amount']
        text += f"\n<b>Сумма всех вкладов:</b> <code>{format_amount(total)}$</code>\n"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать вклад", callback_data="create_deposit")],
                [InlineKeyboardButton(text="❌ Закрыть вклад", callback_data="close_deposit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
            ]
        )
    text += "\nМаксимум 3 вклада, общая сумма не более 1 000 000$."
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()
    
    
    
@dp.callback_query(F.data == "close_deposit")
async def close_deposit_callback(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    deposits = user.get("user_deposits", [])
    if not deposits:
        await callback.answer("У вас нет вкладов.", show_alert=True)
        return
    # Кнопки по номерам вкладов
    buttons = [
        [InlineKeyboardButton(text=f"Вклад {i+1}", callback_data=f"close_deposit_{i}")]
        for i in range(len(deposits))
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_deposits")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        "Выберите вклад для закрытия:",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("close_deposit_"))
async def close_deposit_number_callback(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    deposits = user.get("user_deposits", [])
    try:
        idx = int(callback.data.replace("close_deposit_", ""))
        deposit = deposits[idx]
    except (ValueError, IndexError):
        await callback.answer("Некорректный номер вклада.", show_alert=True)
        return

    # Проверяем, истёк ли срок вклада
    now = int(time.time())
    days_passed = (now - deposit["start"]) // 86400
    is_early = days_passed < deposit["days"]

    if is_early:
        # Сохраняем индекс вклада в FSM для подтверждения
        await state.update_data(close_deposit_idx=idx)
        await callback.message.edit_text(
            f"⚠️ Вы собираетесь закрыть вклад досрочно!\n"
            f"Вам будет возвращена только исходная сумма: <b>{format_amount(deposit['amount'])}$</b> (без процентов).\n\n"
            "Вы уверены, что хотите закрыть вклад?\n\n"
            "Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_deposits")]
                ]
            ),
            parse_mode="HTML"
        )
        await state.set_state("waiting_for_close_deposit_confirm")
    else:
        update_balance(callback.from_user.id, get_balance(callback.from_user.id) + deposit["amount"])
        deposits.pop(idx)
        save_user_data()
        await callback.message.edit_text(
            f"✅ Вклад на <b>{format_amount(deposit['amount'])}$</b> закрыт и возвращён на счёт.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits")],
                    [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")],
                ]
            ),
            parse_mode="HTML"
        )
        await callback.answer()
    
    
@dp.callback_query(F.data == "create_deposit")
async def create_deposit_callback(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    deposits = user.get("user_deposits", [])
    total = sum(dep['amount'] for dep in deposits)
    if len(deposits) >= 3:
        await callback.message.answer("❌ У вас уже 3 вклада. Сначала закройте один из них.")
        await callback.answer()
        return
    if total >= 1_000_000:
        await callback.message.answer("❌ Сумма всех вкладов не может превышать 1 000 000$.")
        await callback.answer()
        return
    await callback.message.edit_text(
        "Выберите срок вклада:",
        reply_markup=get_deposit_terms_kb()
    )
    await state.set_state(BankDepositState.waiting_for_deposit_amount)
    await callback.answer()

@dp.callback_query(F.data == "bank_main")
async def bank_main_callback(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    process_deposits(user)
    bank_sum = user.get('user_bank', 0)
    deposits = user.get("user_deposits", [])
    deposits_text = ""
    if deposits:
        deposits_text = "\n📈 <b>Вклады:</b>\n"
        for i, dep in enumerate(deposits, 1):
            deposits_text += f"{i}. {format_amount(dep['amount'])}$ — {dep['days']} дн., {dep['percent']}%/день\n"
        deposits_text += f"\n<b>Сумма всех вкладов:</b> <code>{sum(dep['amount'] for dep in deposits):,}$</code>\n"
    else:
        deposits_text = "\n📈 Вклады: отсутствуют\n"

    await callback.message.answer(
        f"🏦 <b>Банк</b>\n\n"
        f"📦 <b>Счёт:</b> <code>{bank_sum:,}$</code>\n\n\n"
        "➕ <b>Пополнить</b>: <code>банк (сумма)</code>\n"
        "➖ <b>Снять</b>: <code>банк -(сумма)</code>\n",
        parse_mode="HTML",
        reply_markup=get_bank_main_kb()
    )
    await callback.answer()


@dp.message(StateFilter("waiting_for_close_deposit_confirm"))
async def confirm_close_deposit(message: Message, state: FSMContext):
    answer = message.text.strip().lower()
    data = await state.get_data()
    idx = data.get("close_deposit_idx")
    user = get_user(message.from_user.id)
    deposits = user.get("user_deposits", [])
    if answer == "да" and idx is not None and 0 <= idx < len(deposits):
        deposit = deposits[idx]
        update_balance(message.from_user.id, get_balance(message.from_user.id) + deposit["amount"])
        deposits.pop(idx)
        save_user_data()
        await message.answer(
            f"✅ Вклад на {format_amount(deposit['amount'])}$ досрочно закрыт и возвращён на счёт (без процентов).",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits")],
                    [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")],
                ]
            )
        )
        await state.clear()
    elif answer == "нет":
        await message.answer("❌ Закрытие вклада отменено.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits")]]
        ))
        await state.clear()
    else:
        await message.answer("❓ Напишите `да` для подтверждения или `нет` для отмены.")


@dp.message(F.text.lower().in_(["вклады", "вклад"]))
async def show_deposits_command(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    deposits = user.get("user_deposits", [])
    text = f"📈 <b>Вклады {clickable_name(message.from_user.id, name, clickable)}:</b>\n\n"
    total = 0
    if not deposits:
        text += "Нет активных вкладов.\n"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать вклад", callback_data="create_deposit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
            ]
        )
    else:
        for i, dep in enumerate(deposits, 1):
            text += (
                f"{i}. {dep['amount']:,}$ — {dep['days']} дн., {dep['percent']}%/день\n"
            )
            total += dep['amount']
        text += f"\n<b>Сумма всех вкладов:</b> <code>{total:,}$</code>\n"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать вклад", callback_data="create_deposit")],
                [InlineKeyboardButton(text="❌ Закрыть вклад", callback_data="close_deposit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
            ]
        )
    text += "\nМаксимум 3 вклада, общая сумма не более 1 000 000$."
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb,
    )


@dp.callback_query(F.data.in_(["deposit_1d", "deposit_3d", "deposit_7d"]))
async def deposit_choose_term(callback: CallbackQuery, state: FSMContext):
    terms = {
        "deposit_1d": (1, 3),
        "deposit_3d": (3, 5),
        "deposit_7d": (7, 7),
    }
    days, percent = terms[callback.data]
    await callback.message.edit_text(
        f"Введите сумму для депозита (до {format_amount(BANK_DEPOSIT_LIMIT)}$):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_deposits")]]
        )
    )
    await state.update_data(deposit_days=days, deposit_percent=percent)
    await state.set_state(BankDepositState.waiting_for_deposit_amount)
    await callback.answer()


@dp.message(StateFilter(BankDepositState.waiting_for_deposit_amount))
async def deposit_amount_input(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    data = await state.get_data()
    if "deposit_days" not in data or "deposit_percent" not in data:
        await message.answer("❌ Сначала выберите срок вклада через кнопки!")
        await state.clear()
        return
    days = data["deposit_days"]
    percent = data["deposit_percent"]
    text = message.text.lower().replace(" ", "")
    if text in ["все", "всё", "all"]:
        available = get_balance(message.from_user.id)
        amount = min(available, BANK_DEPOSIT_LIMIT)
        if amount < 100:
            await message.answer("❌ Недостаточно средств для открытия вклада (минимум 100$).")
            return
    else:
        text = text.replace("к", "000").replace("k", "000")
        try:
            amount = int(text)
        except ValueError:
            await message.answer("❌ Введите корректную сумму.")
            return
    if amount < 100 or amount > BANK_DEPOSIT_LIMIT:
        await message.answer(f"❌ Сумма вклада должна быть от 100 до {format_amount(BANK_DEPOSIT_LIMIT)}$.")
        return
    if get_balance(message.from_user.id) < amount:
        await message.answer("❌ Недостаточно средств на балансе.")
        return
    deposit = {
        "amount": amount,
        "start": int(time.time()),
        "days": days,
        "percent": percent,
    }
    user.setdefault("user_deposits", []).append(deposit)
    update_balance(message.from_user.id, get_balance(message.from_user.id) - amount)
    save_user_data()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")],
        ]
    )
    await message.answer(
        f"✅ Депозит на {format_amount(amount)}$ открыт на {days} дн. под {percent}% в день.",
        reply_markup=kb
    )
    await state.clear()
    
    
@dp.callback_query(F.data == "bank_save_add")
async def bank_save_add_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите сумму для пополнения счёта (например, 1000, 1к, все):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")]]
        ),
    )
    await state.set_state(BankSaveState.waiting_for_bank_save_add)
    await callback.answer()


@dp.callback_query(F.data == "bank_save_withdraw")
async def bank_save_withdraw_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите сумму для снятия со счёта (например, 1000, 1к, все):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")]]
        ),
    )
    await state.set_state(BankSaveState.waiting_for_bank_save_withdraw)
    await callback.answer()
    
    

@dp.message(StateFilter(BankSaveState.waiting_for_bank_save_add))
async def bank_save_add_amount(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    text = message.text.lower().replace(" ", "")
    if text in ["все", "всё", "all"]:
        amount = get_balance(message.from_user.id)
    else:
        text = text.replace("к", "000").replace("k", "000")
        try:
            amount = int(text)
        except ValueError:
            await message.answer("❌ Введите корректную сумму.")
            return
    if amount <= 0 or get_balance(message.from_user.id) < amount:
        await message.answer("❌ Недостаточно средств.")
        return
    user["user_bank"] = user.get("user_bank", 0) + amount
    update_balance(message.from_user.id, get_balance(message.from_user.id) - amount)
    save_user_data()
    await message.answer(
        f"✅ <code>{format_amount(amount)}</code>$ добавлено на счёт.\nВсего на счёте: <code>{format_amount(user.get('user_bank', 0))}$</code>.",
        parse_mode="HTML")
    await state.clear()


@dp.message(StateFilter(BankSaveState.waiting_for_bank_save_withdraw))
async def bank_save_withdraw_amount(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    text = message.text.lower().replace(" ", "")
    if text in ["все", "всё", "all"]:
        amount = user.get("user_bank", 0)
    else:
        text = text.replace("к", "000").replace("k", "000")
        try:
            amount = int(text)
        except ValueError:
            await message.answer("❌ Введите корректную сумму.")
            return
    if amount <= 0 or user.get("user_bank", 0) < amount:
        await message.answer("❌ Недостаточно средств на счёте.")
        return
    user["user_bank"] = user.get("user_bank", 0) - amount
    update_balance(message.from_user.id, get_balance(message.from_user.id) + amount)
    save_user_data()
    await message.answer(
        f"✅ <code>{format_amount(amount)}</code>$ снято со счёта.\nОсталось на счёте: <code>{format_amount(user.get('user_bank', 0))}$</code>.",
        parse_mode="HTML")
    await state.clear()




@dp.message(F.text.lower().startswith("банк"))
async def bank_command(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    parts = message.text.lower().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            f"❌ {clickable_name(message.from_user.id, name, clickable)}, укажите сумму. Пример:\n"
            "<code>банк 1000</code>\n"
            "<code>банк -500</code>\n"
            "<code>банк все</code>\n"
            "<code>банк -все</code>\n"
            "<code>банк 1/3</code>\n"
            "<code>банк -1/3</code>",
            parse_mode="HTML"
        )
        return

    text = parts[1].replace(" ", "")
    if text in ["все", "всё", "all"]:
        amount = get_balance(message.from_user.id)
    elif text in ["-все", "-всё", "-all"]:
        amount = -user.get("user_bank", 0)
    else:
        sign = -1 if text.startswith("-") else 1
        text_num = text.lstrip("-")
        try:
            amount_parsed = parse_k(text_num)
        except Exception:
            amount_parsed = None
        if amount_parsed is None:
            await message.answer(
                f"❌ {clickable_name(message.from_user.id, name, clickable)}, введите корректную сумму. Пример:\n"
                "<code>банк 1000</code>\n"
                "<code>банк -500</code>\n"
                "<code>банк все</code>\n"
                "<code>банк -все</code>\n"
                "<code>банк 1/3</code>\n"
                "<code>банк -1/3</code>",
                parse_mode="HTML"
            )
            return
        amount = amount_parsed * sign

    # Пополнение
    if amount > 0:
        if get_balance(message.from_user.id) < amount:
            await message.answer(
                f"❌ {clickable_name(message.from_user.id, name, clickable)}, недостаточно средств на балансе.",
                parse_mode="HTML"
            )
            return
        user["user_bank"] = user.get("user_bank", 0) + amount
        update_balance(message.from_user.id, get_balance(message.from_user.id) - amount)
        save_user_data()
        await message.answer(
            f"✅ {clickable_name(message.from_user.id, name, clickable)}, <code>{format_amount(amount)}$</code> добавлено на счёт.\n"
            f"Всего на счёте: <code>{format_amount(user['user_bank'])}$</code>.",
            parse_mode="HTML"
        )
    # Снятие
    elif amount < 0:
        amount = abs(amount)
        if user.get("user_bank", 0) < amount:
            await message.answer(
                f"❌ {clickable_name(message.from_user.id, name, clickable)}, недостаточно средств на счёте.",
                parse_mode="HTML"
            )
            return
        user["user_bank"] -= amount
        update_balance(message.from_user.id, get_balance(message.from_user.id) + amount)
        save_user_data()
        await message.answer(
            f"✅ {clickable_name(message.from_user.id, name, clickable)}, <code>{format_amount(amount)}$</code> снято со счёта.\n"
            f"Осталось на счёте: <code>{format_amount(user['user_bank'])}$</code>.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ {clickable_name(message.from_user.id, name, clickable)}, сумма должна быть больше 0.",
            parse_mode="HTML"
        )
        
        
        

@dp.message(F.text.lower().in_(["админ панель", "апанель", 'админская панель', 'админка']))
async def show_admin_panel(message: Message):
    user_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in admins:
        await message.answer(
            "⛔ У вас нет доступа к админской панели.", reply_markup=safe_reply_kb(message, menu_kb)
        )
        return

    # Отправляем админскую панель
    await message.answer("⚙️ Админская панель:", reply_markup=safe_reply_kb(message, admin_kb))


@dp.message(F.text == "💵 Выдать")
async def handle_give_money(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in admins:
        await message.answer("⛔ У вас нет прав", reply_markup=safe_reply_kb(message, menu_kb))
        return

    # Создаём инлайн-клавиатуру с кнопкой "Отмена"
    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_give_money")]
        ]
    )

    # Запускаем FSM и спрашиваем ID/юзернейм
    await message.answer(
        "Введите игровой ID, Telegram ID или @юзернейм пользователя, которому хотите выдать деньги:",
        reply_markup=cancel_kb,
    )
    await state.set_state(AdminGiveMoneyState.waiting_for_user_id)


@dp.callback_query(F.data == "cancel_give_money")
async def handle_cancel_give_money(callback: CallbackQuery, state: FSMContext):
    # Завершаем FSM
    await state.clear()

    # Отправляем сообщение о возврате в админ-панель
    await callback.message.answer("❌ Операция отменена.", reply_markup=safe_reply_kb(callback.message, admin_kb))

    # Закрываем уведомление о нажатии кнопки
    await callback.answer()

@dp.message(AdminGiveMoneyState.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    amount = parse_k(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ Укажите корректную сумму.")
        return

    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    recipient = get_user(recipient_id)
    if recipient_id is None or recipient is None:
        await message.answer("❌ Получатель не найден. Операция отменена.")
        await state.clear()
        return

    update_balance(recipient_id, get_balance(recipient_id) + amount)
    save_user_data()
    await state.clear()

    name = recipient.get("name", "Без имени")
    clickable = recipient.get("clickable_name", True)
    await message.answer(
        f"✅ Вы успешно выдали <b>{amount}$</b> пользователю {clickable_name(recipient_id, name, clickable)}.",
        parse_mode="HTML",
        reply_markup=safe_reply_kb(message, admin_kb),
    )

    try:
        await bot.send_message(
            recipient_id,
            f"💵 Вам выдали <b>{amount}$</b> администратор.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    

@dp.message(F.text.lower().startswith("обнулить"))
async def reset_user_command(message: Message):
    user_id = message.from_user.id
    if user_id not in admins:
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ Укажите ID пользователя для обнуления. Пример: `обнулить 123456789`")
        return
    target_user_id = int(parts[1])
    reset_user_data(target_user_id)
    recipient = get_user(target_user_id)
    name = recipient.get("name", "Без имени") if recipient else "Без имени"
    clickable = recipient.get("clickable_name", True) if recipient else True
    await message.answer(
        f"✅ Пользователь {clickable_name(target_user_id, name, clickable)} полностью удалён из базы.",
        parse_mode="HTML",
        reply_markup=safe_reply_kb(message, admin_kb),
    )


@dp.message(F.text == "🗑️ Обнулить")
async def handle_reset_button(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in admins:
        await message.answer("⛔ У вас нет прав для выполнения этой команды.", reply_markup=safe_reply_kb(message, menu_kb))
        return

    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_reset")]
        ]
    )

    # Запускаем FSM и запрашиваем идентификатор пользователя
    await message.answer(
        "Введите игровой ID, Telegram ID или @юзернейм пользователя, которого нужно обнулить:",
        reply_markup=cancel_kb,
    )
    await state.set_state(AdminResetState.waiting_for_user_id)


@dp.callback_query(F.data == "cancel_reset")
async def handle_cancel_reset(callback: CallbackQuery, state: FSMContext):
    # Завершаем FSM
    await state.clear()

    # Отправляем новое сообщение о возврате в админ-панель
    await callback.message.answer("❌ Операция отменена.", reply_markup=safe_reply_kb(callback.message, admin_kb))

    # Закрываем уведомление о нажатии кнопки
    await callback.answer()

@dp.message(AdminResetState.waiting_for_user_id)
async def process_reset_user(message: Message, state: FSMContext):
    user_input = message.text.strip()

    # Ищем пользователя
    recipient_id, recipient = find_user_by_identifier(user_input, utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Проверьте данные и попробуйте снова.")
        return

    # Сохраняем данные пользователя в FSM
    await state.update_data(
        recipient_id=recipient_id, recipient_name=recipient.get("name", "Без имени")
    )

    # Запрашиваем подтверждение
    await message.answer(
        f"Вы уверены, что хотите обнулить пользователя {recipient.get('name', 'Без имени')} (ID: {recipient_id})?\n"
        "Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.",
        parse_mode="HTML",
    )
    await state.set_state(AdminResetState.waiting_for_confirmation)


@dp.message(AdminGiveMoneyState.waiting_for_user_id)
async def process_give_money_user_id(message: Message, state: FSMContext):
    user_input = message.text.strip()
    recipient_id, recipient = find_user_by_identifier(user_input, utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Проверьте данные и попробуйте снова.")
        return

    await state.update_data(recipient_id=recipient_id)
    await message.answer("Введите сумму, которую хотите выдать:")
    await state.set_state(AdminGiveMoneyState.waiting_for_amount)


@dp.message(AdminResetState.waiting_for_confirmation)
async def confirm_reset_user(message: Message, state: FSMContext):
    confirmation = message.text.strip().lower()
    if confirmation == "да":
        data = await state.get_data()
        recipient_id = data.get("recipient_id")
        recipient_name = data.get("recipient_name")
        reset_user_data(recipient_id)
        await state.clear()
        # recipient уже не нужен, используем recipient_name
        await message.answer(
            f"✅ Пользователь {recipient_name} полностью удалён из базы.",
            parse_mode="HTML",
            reply_markup=safe_reply_kb(message, admin_kb),
        )
        try:
            await bot.send_message(
                recipient_id,
                "🗑️ Ваш аккаунт был полностью удалён администратором.",
                parse_mode="HTML",
            )
        except Exception:
            pass
    elif confirmation == "нет":
        await state.clear()
        await message.answer("❌ Обнуление отменено.", reply_markup=safe_reply_kb(message, admin_kb))
    else:
        await message.answer("❓ Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.", parse_mode="HTML")


@dp.message(F.text.lower().startswith("выдать"))
async def handle_give_money_command(message: Message):
    user_id = message.from_user.id
    if user_id not in admins:
        await message.answer(
            "⛔ У вас нет прав для выполнения этой команды.", reply_markup=safe_reply_kb(message, menu_kb)
        )
        return

    # Выдача по reply
    if message.reply_to_message:
        recipient_id = message.reply_to_message.from_user.id
        recipient = get_user(recipient_id)
        if not recipient:
            await message.answer("❌ Пользователь не найден. Пусть он напишет боту /start.")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("❌ Укажите сумму. Пример: <code>выдать 1000</code>", parse_mode="HTML")
            return
        amount_text = parts[1].strip()
        amount = parse_k(amount_text)
        if amount is None or amount <= 0:
            await message.answer("❌ Укажите корректную сумму. Пример: <code>выдать 1000</code>", parse_mode="HTML")
            return
        update_balance(recipient_id, get_balance(recipient_id) + amount)
        save_user_data()
        name = recipient.get("name", "Без имени")
        clickable = recipient.get("clickable_name", True)
        await message.answer(
            f"✅ Вы успешно выдали <b>{amount}$</b> пользователю {clickable_name(recipient_id, name, clickable)}.",
            parse_mode="HTML",
            reply_markup=safe_reply_kb(message, admin_kb),
        )
        try:
            await bot.send_message(
                recipient_id,
                f"💵 Вам выдали <b>{amount}$</b> администратор.",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    # Выдача по команде
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "❌ Неверный формат команды. Используйте:\n"
            "<code>выдать (тгюзернейм|айдиигровое|тгайди) (сумма)</code>\n"
            "Или ответьте на сообщение пользователя: <code>выдать 1000</code>",
            parse_mode="HTML",
        )
        return

    user_input = parts[1].strip()
    amount_text = parts[2].strip()
    recipient_id, recipient = find_user_by_identifier(user_input, utils.user_data)
    if not recipient:
        await message.answer(
            "❌ Пользователь не найден. Проверьте данные и попробуйте снова."
        )
        return  

    amount = parse_k(amount_text)
    if amount is None or amount <= 0:
        await message.answer(
            "❌ Укажите корректную сумму. Пример: <code>выдать @username 10к</code>",
            parse_mode="HTML"
        )
        return

    update_balance(recipient_id, get_balance(recipient_id) + amount)
    save_user_data()

    name = recipient.get("name", "Без имени")
    clickable = recipient.get("clickable_name", True)
    await message.answer(
        f"✅ Вы успешно выдали <b>{amount}$</b> пользователю {clickable_name(recipient_id, name, clickable)} (ID: {recipient_id}).",
        parse_mode="HTML",
        reply_markup=safe_reply_kb(message, admin_kb),
    )

    try:
        await bot.send_message(
            recipient_id,
            f"💵 Вам выдали <b>{amount}$</b> администратор.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    

@dp.message(AdminSetState.waiting_for_user_id)
async def process_set_user_id(message: Message, state: FSMContext):
    user_input = message.text.strip()
    recipient_id, recipient = find_user_by_identifier(user_input, utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Проверьте данные и попробуйте снова.")
        return

    await state.update_data(
        recipient_id=recipient_id, recipient_name=recipient.get("name", "Без имени")
    )

    data = await state.get_data()
    choice = data.get("choice")
    if choice == "game_id":
        await message.answer("Введите новый игровой ID:")
    elif choice == "balance":
        await message.answer("Введите новый баланс:")
    elif choice == "name":
        await message.answer("Введите новый ник:")
    elif choice == "bank":
        await message.answer("Введите новую сумму для банковского счёта:")
    await state.set_state(AdminSetState.waiting_for_value)
    
    
@dp.message(AdminSetState.waiting_for_choice)
async def process_set_choice(message: Message, state: FSMContext):
    choice = message.text.strip().lower()

    if choice == "ник":
        await state.update_data(choice="name")
        await message.answer("Введите новый ник:")
        await state.set_state(AdminSetState.waiting_for_value)
    elif choice == "айди":
        await state.update_data(choice="game_id")
        await message.answer("Введите новый игровой ID:")
        await state.set_state(AdminSetState.waiting_for_value)
    elif choice == "баланс":
        await state.update_data(choice="balance")
        await message.answer("Введите новый баланс:")
        await state.set_state(AdminSetState.waiting_for_value)
    elif choice in ["банк", "счет", "счёт"]:
        await state.update_data(choice="bank")
        await message.answer("Введите новую сумму для банковского счёта:")
        await state.set_state(AdminSetState.waiting_for_value)
    elif choice == "отмена":
        await state.clear()
        await message.answer("❌ Установка отменена.", reply_markup=safe_reply_kb(message, admin_kb))
    else:
        await message.answer(
            "❌ Неверный выбор. Пожалуйста, выберите: Ник, Айди, Баланс, Банк или Счёт.",
            reply_markup=safe_reply_kb(message, admin_kb)
        )


@dp.callback_query(F.data == "set_bank")
async def handle_set_bank(callback: CallbackQuery, state: FSMContext):
    await state.update_data(choice="bank")
    await callback.message.answer("Введите игровой ID, Telegram ID или @юзернейм пользователя:")
    await state.set_state(AdminSetState.waiting_for_user_id)
    await callback.answer()


@dp.message(AdminSetState.waiting_for_value)
async def process_set_value(message: Message, state: FSMContext):
    data = await state.get_data()
    choice = data.get("choice")
    value = message.text.strip()

    if choice == "game_id":
        if not value.isdigit():
            await message.answer("❌ Игровой ID должен быть числом. Попробуйте снова.")
            return
        field = "айди"
    elif choice == "balance":
        try:
            value = int(value)
            if value < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Баланс должен быть положительным числом. Попробуйте снова.")
            return
        field = "баланс"
    elif choice == "name":
        if len(value) > 30:
            await message.answer("❌ Ник слишком длинный. Максимум 30 символов.")
            return
        field = "ник"
    elif choice == "bank":
        try:
            amount = parse_k(value)
            if amount is None or amount < 0:
                raise ValueError
            value = amount
        except ValueError:
            await message.answer("❌ Сумма для банка должна быть положительным числом. Попробуйте снова.")
            return
        field = "банк"
    else:
        await message.answer("❌ Неверный выбор.")
        return

    await state.update_data(value=value, field=field, action="set_value")

    recipient_id = data.get("recipient_id")
    recipient = get_user(recipient_id)
    name = recipient.get("name", "Без имени") if recipient else "Без имени"
    clickable = recipient.get("clickable_name", True) if recipient else True
    field_name = {"айди": "Игровой ID", "баланс": "Баланс", "ник": "Ник", "банк": "Банк"}.get(field, field)
    await message.answer(
        f"Вы уверены, что хотите установить {field_name} для пользователя {clickable_name(recipient_id, name, clickable)}?\n"
        f"Новое значение: {value}\n\n"
        "Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.",
        parse_mode="HTML"
    )
    await state.set_state(AdminSetState.waiting_for_confirmation)




@dp.message(F.text == "🛠️ Установить")
async def handle_set_command(message: Message):
    user_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in admins:
        await message.answer("⛔ У вас нет прав", reply_markup=safe_reply_kb(message, menu_kb))
        return

    await message.answer(
        "Что вы хотите установить?",
        reply_markup=admin_set_kb,
    )


@dp.callback_query(F.data == "set_name")
async def handle_set_name(callback: CallbackQuery, state: FSMContext):
    await state.update_data(choice="name")
    await callback.message.answer("Введите игровой ID, Telegram ID или @юзернейм пользователя:")
    await state.set_state(AdminSetState.waiting_for_user_id)
    await callback.answer()


@dp.callback_query(F.data == "set_game_id")
async def handle_set_game_id(callback: CallbackQuery, state: FSMContext):
    await state.update_data(choice="game_id")
    await callback.message.answer("Введите игровой ID, Telegram ID или @юзернейм пользователя:")
    await state.set_state(AdminSetState.waiting_for_user_id)
    await callback.answer()


@dp.callback_query(F.data == "set_balance")
async def handle_set_balance(callback: CallbackQuery, state: FSMContext):
    await state.update_data(choice="balance")
    await callback.message.answer("Введите игровой ID, Telegram ID или @юзернейм пользователя:")
    await state.set_state(AdminSetState.waiting_for_user_id)
    await callback.answer()


@dp.callback_query(F.data == "cancel_set")
async def handle_cancel_set(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Установка отменена.", reply_markup=safe_reply_kb(callback.message, admin_kb))
    await callback.answer()

@dp.message(F.text.lower().startswith("установить"))
async def set_user_data_command(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in admins:
        await message.answer("⛔ У вас нет прав", reply_markup=safe_reply_kb(message, menu_kb))
        return

    # Разделяем команду на части
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(
            "❌ Неверный формат команды. Используйте:\n"
            "<code>установить (ник|айди|баланс|банк|счет) (пользователь) (значение)</code>",
            parse_mode="HTML",
        )
        return

    field = parts[1].strip().lower()
    user_input = parts[2].strip()
    value = parts[3].strip()

    # Проверяем корректность поля
    if field not in ["ник", "айди", "баланс", "банк", "счет", "счёт"]:
        await message.answer(
            "❌ Неверное поле. Используйте одно из: <code>ник</code>, <code>айди</code>, <code>баланс</code>, <code>банк</code>, <code>счет</code>.",
            parse_mode="HTML"
        )
        return

    # Ищем пользователя по игровому ID, Telegram ID или Telegram-юзернейму
    recipient_id, recipient = find_user_by_identifier(user_input, utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Проверьте данные и попробуйте снова.")
        return

    # Проверяем значение
    if field == "айди":
        if not value.isdigit():
            await message.answer("❌ Игровой ID должен быть числом.")
            return
    elif field == "баланс":
        try:
            amount = parse_k(value)
            if amount is None or amount < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Баланс должен быть положительным числом.")
            return
    elif field == "ник":
        if len(value) > 30:
            await message.answer("❌ Ник слишком длинный. Максимум 30 символов.")
            return
    elif field in ["банк", "счет", "счёт"]:
        try:
            amount = parse_k(value)
            if amount is None or amount < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Сумма для банка должна быть положительным числом.")
            return

    # Для отображения только кликабельного ника
    name = recipient.get("name", "Без имени")
    clickable = recipient.get("clickable_name", True)

    await state.update_data(
        field=field,
        recipient_id=recipient_id,
        recipient_name=name,
        value=value,
        action="set_value"
    )

    # Запрашиваем подтверждение
    await message.answer(
        f"Вы уверены, что хотите установить {field} для пользователя {clickable_name(recipient_id, name, clickable)}?\n"
        f"Новое значение: {value}\n\n"
        "Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.",
        parse_mode="HTML",
    )
    await state.set_state(AdminSetState.waiting_for_confirmation)


@dp.message(AdminSetState.waiting_for_confirmation)
async def confirm_set_value(message: Message, state: FSMContext):
    answer = message.text.strip().lower()
    data = await state.get_data()
    if answer == "да":
        recipient_id = data.get("recipient_id")
        value = data.get("value")
        field = data.get("field")
        recipient = get_user(recipient_id)
        name = recipient.get("name", "Без имени") if recipient else "Без имени"
        clickable = recipient.get("clickable_name", True) if recipient else True

        if field == "айди":
            recipient["game_id"] = int(value)
        elif field == "баланс":
            recipient["balance"] = int(value)
        elif field == "ник":
            recipient["name"] = value
        elif field == "банк" or field in ["счет", "счёт"]:
            recipient["user_bank"] = parse_k(str(value))
        save_user_data()
        await state.clear()
        await message.answer(
            f"✅ {field.capitalize()} пользователя {clickable_name(recipient_id, name, clickable)} успешно изменён.",
            parse_mode="HTML",
            reply_markup=safe_reply_kb(message, admin_kb),
        )
    elif answer == "нет":
        await state.clear()
        await message.answer("❌ Установка отменена.", reply_markup=safe_reply_kb(message, admin_kb))
    else:
        await message.answer(
            "❓ Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.",
            parse_mode="HTML"
        )



@dp.message(AdminResetState.waiting_for_confirmation)
async def confirm_reset_user2(message: Message, state: FSMContext):
    confirmation = message.text.strip().lower()

    if confirmation == "да":
        # Получаем данные из FSM
        data = await state.get_data()
        recipient_id = data.get("recipient_id")
        recipient_name = data.get("recipient_name")

        # Обнуляем баланс, игровой ID и имущество
        recipient = utils.user_data.get(str(recipient_id))
        if recipient:
            recipient["balance"] = 0
            recipient["game_id"] = random.randint(100000, 999999)
            recipient["assets"] = {
                "cars": [],
                "houses": [],
                "yachts": [],
                "planes": [],
                "helicopters": [],
                "smartphones": [],
            }
            save_user_data()

        # Завершаем FSM
        await state.clear()

        # Уведомляем администратора
        await message.answer(
            f"✅ Пользователь {recipient_name} (ID: {recipient_id}) успешно обнулён.\n"
            f"💰 Баланс: 0$\n🆔 Игровой ID: сброшен.\n📦 Имущество: удалено.",
            reply_markup=safe_reply_kb(message, admin_kb),
        )

        # Уведомляем пользователя
        try:
            await bot.send_message(
                recipient_id,
                "🗑️ Ваш баланс, игровой ID и имущество были обнулены администратором.",
                parse_mode="HTML",
            )
        except Exception:
            pass

    elif confirmation == "нет":
        await state.clear()
        await message.answer("❌ Обнуление отменено.", reply_markup=safe_reply_kb(message, admin_kb))
    else:
        await message.answer(
            "❓ Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.",
            parse_mode="HTML"
        )


@dp.message(F.text.lower().startswith("❓ руководство"))
async def admin_help_command(message: Message):
    user_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in admins:
        await message.answer("⛔ У вас нет прав для просмотра этого раздела.")
        return

    # Отправляем текст с руководством
    await message.answer(admin_panel_help_text, parse_mode="HTML")



@dp.message(F.text.lower().startswith("инфо "), StateFilter(default_state))
async def handle_info_with_argument(message: Message):
    user_id = message.from_user.id
    if user_id not in admins:
        await message.answer(
            "⛔ У вас нет прав для выполнения этой команды.", reply_markup=safe_reply_kb(message, menu_kb)
        )
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажите ID, игровой ID или @юзернейм пользователя.")
        return

    user_input = parts[1].strip()
    recipient_id, recipient = find_user_by_identifier(user_input, utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Проверьте данные и попробуйте снова.")
        return

    name = recipient.get("name", "Без имени")
    clickable = recipient.get("clickable_name", True)
    game_id = recipient.get("game_id", "Не указан")
    balance = recipient.get("balance", 0)
    bank_account = recipient.get("user_bank", 0)
    deposits = recipient.get("user_deposits", [])
    telegram_username = recipient.get("telegram_username", "Не указан")
    referrals = len(recipient.get("referrals", []))
    assets = get_assets_text(recipient)

    if deposits:
        deposits_text = "\n".join(
            [f"- {format_amount(dep['amount'])}$ на {dep['days']} дн. под {dep['percent']}%" for dep in deposits]
        )
        deposits_sum = sum(dep['amount'] for dep in deposits)
    else:
        deposits_text = "Нет активных вкладов."
        deposits_sum = 0

    info_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑️ Обнулить", callback_data=f"reset_user:{recipient_id}"),
                InlineKeyboardButton(text="💵 Выдать", callback_data=f"give_money:{recipient_id}"),
            ]
        ]
    )

    await message.answer(
        f"👤 Информация о пользователе:\n"
        f"Имя: {clickable_name(recipient_id, name, clickable)}\n"
        f"🆔 Игровой ID: <code>{game_id}</code>\n"
        f"💳 Telegram ID: <code>{recipient_id}</code>\n"
        f"💰 Баланс: <b>{format_amount(balance)}$</b>\n"
        f"🏦 Банк: <b>{format_amount(bank_account)}$</b>\n"
        f"📈 Вклады ({format_amount(deposits_sum)}$):\n{deposits_text}\n"
        f"📦 Имущество:\n{assets}\n"
        f"Telegram: @{telegram_username}\n"
        f"👥 Количество рефералов: {referrals}",
        parse_mode="HTML",
        reply_markup=info_kb,
    )


@dp.message(F.text == "ℹ️ Информация")
async def handle_info_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in admins:
        await message.answer(
            "⛔ У вас нет прав для выполнения этой команды.", reply_markup=safe_reply_kb(message, menu_kb)
        )
        return

    await message.answer("Введите игровой ID, Telegram ID или @юзернейм пользователя:")
    await state.set_state(AdminInfoState.waiting_for_user_id)

@dp.message(AdminInfoState.waiting_for_user_id)
async def process_info_user_id(message: Message, state: FSMContext):
    user_input = message.text.strip()
    recipient_id, recipient = find_user_by_identifier(user_input, utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Проверьте данные и попробуйте снова.")
        return

    await state.clear()

    name = recipient.get("name", "Без имени")
    clickable = recipient.get("clickable_name", True)
    game_id = recipient.get("game_id", "Не указан")
    balance = recipient.get("balance", 0)
    bank_account = recipient.get("user_bank", 0)
    deposits = recipient.get("user_deposits", [])
    telegram_username = recipient.get("telegram_username", "Не указан")
    referrals = len(recipient.get("referrals", []))
    assets = get_assets_text(recipient)

    if deposits:
        deposits_text = "\n".join(
            [f"- {format_amount(dep['amount'])}$ на {dep['days']} дн. под {dep['percent']}%" for dep in deposits]
        )
        deposits_sum = sum(dep['amount'] for dep in deposits)
    else:
        deposits_text = "Нет активных вкладов."
        deposits_sum = 0

    info_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑️ Обнулить", callback_data=f"reset_user:{recipient_id}"),
                InlineKeyboardButton(text="💵 Выдать", callback_data=f"give_money:{recipient_id}"),
            ]
        ]
    )

    await message.answer(
        f"👤 Информация о пользователе:\n"
        f"Имя: {clickable_name(recipient_id, name, clickable)}\n"
        f"🆔 Игровой ID: <code>{game_id}</code>\n"
        f"💳 Telegram ID: <code>{recipient_id}</code>\n"
        f"💰 Баланс: <b>{format_amount(balance)}$</b>\n"
        f"🏦 Банк: <b>{format_amount(bank_account)}$</b>\n"
        f"📈 Вклады ({format_amount(deposits_sum)}$):\n{deposits_text}\n"
        f"📦 Имущество:\n{assets}\n"
        f"Telegram: @{telegram_username}\n"
        f"👥 Количество рефералов: {referrals}",
        parse_mode="HTML",
        reply_markup=info_kb,
    )


@dp.callback_query(F.data.startswith("reset_user:"))
async def handle_reset_user_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins:
        await callback.answer("⛔ У вас нет прав для этого действия.", show_alert=True)
        return
    recipient_id = int(callback.data.split(":")[1])
    recipient = utils.user_data.get(str(recipient_id))
    if not recipient:
        await callback.message.answer("❌ Пользователь не найден. Проверьте данные и попробуйте снова.")
        return
    await state.update_data(recipient_id=recipient_id, recipient_name=recipient.get("name", "Без имени"))
    await callback.message.answer(
        f"Вы уверены, что хотите обнулить пользователя {recipient.get('name', 'Без имени')} (ID: {recipient_id})?\n"
        "Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.",
        parse_mode="HTML",
    )
    await state.set_state(AdminResetState.waiting_for_confirmation)
    await callback.answer()
    

@dp.callback_query(F.data.startswith("give_money:"))
async def handle_give_money_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins:
        await callback.answer("⛔ У вас нет прав для этого действия.", show_alert=True)
        return
    recipient_id = int(callback.data.split(":")[1])
    recipient = utils.user_data.get(str(recipient_id))
    if not recipient:
        await callback.message.answer("❌ Пользователь не найден. Проверьте данные и попробуйте снова.")
        return
    await state.update_data(recipient_id=recipient_id)
    await callback.message.answer("Введите сумму, которую хотите выдать:")
    await state.set_state(AdminGiveMoneyState.waiting_for_amount)
    await callback.answer()
    
    
@dp.callback_query(F.data.startswith("set_user:"))
async def inline_handle_set_user_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins:
        await callback.answer("⛔ У вас нет прав для этого действия.", show_alert=True)
        return

    recipient_id = int(callback.data.split(":")[1])

    # Сохраняем данные пользователя в FSM
    recipient = utils.user_data.get(str(recipient_id))
    if not recipient:
        await callback.message.answer("❌ Пользователь не найден.")
        return

    await state.update_data(recipient_id=recipient_id, recipient_name=recipient.get("name", "Без имени"))

    # Запрашиваем, что нужно установить
    await callback.message.answer(
        "Что вы хотите установить?",
        reply_markup=admin_set_kb,
    )
    await state.set_state(AdminSetState.waiting_for_choice)
    await callback.answer()
    


def load_reports():
    if os.path.exists(REPORTS_FILE):
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_reports(reports):
    try:
        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_next_report_id():
    reports = load_reports()
    if reports:
        return str(int(max(reports.keys(), key=int)) + 1)
    return "1"

@dp.message(F.text.lower().startswith(("репорт", "поддержка")))
async def report_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите текст сообщения для поддержки. Пример: <code>репорт не работает банк</code>",
            parse_mode="HTML"
        )
        return
    report_text = parts[1].strip()
    report_id = get_next_report_id()
    reports = load_reports()
    reports[report_id] = {
        "user_id": user_id,
        "user_name": name,
        "text": report_text,
        "status": "open",
        "chat_id": chat_id,
    }
    save_reports(reports)

    # Новый стиль подтверждения
    confirm_text = (
        f"{name}, ваше сообщение отправлено (№{report_id}) ✅\n"
        f"▶️ Ответ вы получите в данном диалоге"
    )
    await message.answer(confirm_text, parse_mode="HTML")

    # Сообщение админу (всем владельцам)
    for owner_id in owners:
        owner_user = get_user(owner_id)
        if not owner_user:
            continue
        try:
            msg = await bot.send_message(
                owner_id,
                f"Репорт #{report_id} от пользователя {clickable_name(user_id, name, clickable)}:\n{report_text}",
                parse_mode="HTML"
            )
            REPORTS_STATE[report_id] = {"user_id": user_id, "admin_msg_id": msg.message_id}
        except Exception:
            pass
        

# Ответ на репорт (админ отвечает на сообщение-репорт)
@dp.message(lambda m: m.reply_to_message and m.from_user.id in owners)
async def reply_to_report(message: Message):
    reply = message.reply_to_message
    text = message.text.strip()
    # Поиск report_id по тексту сообщения-репорта
    report_id = None
    for line in reply.text.splitlines():
        if line.startswith("Репорт #"):
            report_id = line.split("#")[1].split()[0]
            break
    if not report_id:
        return
    reports = load_reports()
    report = reports.get(report_id)
    if not report:
        await message.answer("Репорт не найден.")
        return
    user_id = report["user_id"]
    chat_id = report.get("chat_id", user_id)
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    dt = datetime.now().strftime("%d.%m.%Y %H:%M")
    answer_text = (
        f"🔔 {clickable_name(user_id, name, clickable)}, на твоё сообщение №{report_id} поступил ответ:\n"
        f"💬 {text}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Помогло", callback_data=f"report_helpful:{report_id}"),
                InlineKeyboardButton(text="👎 Не помогло", callback_data=f"report_not_helpful:{report_id}")
            ]
        ]
    )
    errors = []
    # Отправляем в личку
    try:
        await bot.send_message(user_id, answer_text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        errors.append(f"Не удалось отправить в ЛС: {e}")
    # Если репорт был из группы — отправляем и туда
    if chat_id != user_id:
        try:
            await bot.send_message(chat_id, answer_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            errors.append(f"Не удалось отправить в группу: {e}")
    report["status"] = "answered"
    save_reports(reports)
    if errors:
        await message.answer(f"Ответ на репорт #{report_id} отправлен, но есть ошибки:\n" + "\n".join(errors))
    else:
        await message.answer(f"Ответ на репорт #{report_id} отправлен пользователю.")
        

@dp.callback_query(F.data.startswith("report_helpful:"))
async def report_helpful_callback(callback: CallbackQuery):
    report_id = callback.data.split(":")[1]
    reports = load_reports()
    report = reports.get(report_id)
    if report:
        report["status"] = "closed_helpful"
        save_reports(reports)
    await callback.message.edit_text(f"👍 Спасибо за ваш отклик. Репорт #{report_id} закрыт как решённый.")

@dp.callback_query(F.data.startswith("report_not_helpful:"))
async def report_not_helpful_callback(callback: CallbackQuery):
    report_id = callback.data.split(":")[1]
    reports = load_reports()
    report = reports.get(report_id)
    if report:
        report["status"] = "closed_not_helpful"
        save_reports(reports)
    await callback.message.edit_text(
        f"👍 Спасибо за ваш отклик. Репорт №{report_id} отмечен как нерешённый. Если вопрос не решён, напишите новый репорт с уточнением."
    )


@dp.message(F.text.lower().startswith(("/alert", "alert", "алерт")))
async def alert_command(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("❌ Укажите текст для алерта. Пример: <code>алерт Привет!</code>", parse_mode="HTML")
        return
    alert_text = parts[1].strip()
    # Ограничение 50 символов (чтобы с запасом влезло в 64 байта)
    if len(alert_text.encode("utf-8")) > 50:
        await message.answer("❌ Текст для алерта слишком длинный. Максимум 50 символов (или меньше, если используются эмодзи/русские буквы).", parse_mode="HTML")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Показать алерт", callback_data=f"show_alert:{alert_text}")]
        ]
    )
    await message.answer("ㅤ", reply_markup=kb)

@dp.callback_query(F.data.startswith("show_alert:"))
async def show_alert_callback(callback: CallbackQuery):
    alert_text = callback.data[len("show_alert:") :]
    await callback.answer(alert_text, show_alert=True)



if __name__ == "__main__":
    import asyncio

    async def main():
        load_user_data()
        round_all_balances()
        fix_user_data()
        global admins
        admins = utils.user_data.get("admins", admins)
        scheduler = AsyncIOScheduler()
        scheduler.add_job(process_all_deposits, "interval", minutes=10)
        scheduler.start()
        await dp.start_polling(bot)

    asyncio.run(main())