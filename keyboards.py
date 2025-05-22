from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

click_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👆 Жмак")],  # Кнопка в отдельной строке
    ],
    input_field_placeholder="жмакай по кнопке",
    resize_keyboard=False,  # Включаем автоматическое изменение размера
)

menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👤 Профиль"),
            KeyboardButton(text="🎮 Игры"),
            KeyboardButton(text="🏆 Топ"),
        ],
        [
            KeyboardButton(text="❓ Помощь"),
            KeyboardButton(text="🎁 Бонус"),
            KeyboardButton(text="💼 Работа"),
        ],
        [
            KeyboardButton(text="🏦 Банк"),
            KeyboardButton(text="🛒 Магазин"),
            KeyboardButton(text="⚙️ Настройки"),
        ],
        [
            KeyboardButton(text="🔗 Реферальная система"),  # Добавлена кнопка "Банк"
        ],
    ],
    resize_keyboard=True,
)

games_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👆 Жмакер"),
            KeyboardButton(text="🪙 Монетка"),
        ],
        [
            KeyboardButton(text="🎰 Рулетка"),
            KeyboardButton(text="💥 Краш"),
        ],
        [
            KeyboardButton(text="🏠 Меню"),
        ],
    ],
    resize_keyboard=True,
)

settings_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="✏️ Изменить имя"),
            KeyboardButton(text="🔗 Кликабельность ника"),
        ],
        [
            KeyboardButton(text="🏠 Меню"),
        ],
    ],
    resize_keyboard=True,
)

ref_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👥 Рефералы"),
        ],
        [
            KeyboardButton(text="🏠 Меню"),
        ],
    ],
    resize_keyboard=True,
)

top_balance_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 Топ рефералов", callback_data="top_ref"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
        ]
    ]
)

top_ref_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 Топ по балансу", callback_data="top_balance"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
        ]
    ]
)
work_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧹 Дворник"), KeyboardButton(text="⛏️ Шахтёр")],
        [KeyboardButton(text="💰 Кладмен")], [KeyboardButton(text='🏠 Меню')]
    ],
    resize_keyboard=True,
)

mining_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⛏️ Малая шахта"), KeyboardButton(text="⛏️ Средняя шахта")],
        [KeyboardButton(text="⛏️ Глубокая шахта"), KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Выдать"), KeyboardButton(text="🗑️ Обнулить")],
        [
            KeyboardButton(text="🛠️ Установить"),
            KeyboardButton(text="ℹ️ Информация"),
        ],  # Добавлена кнопка "Информация"
        [KeyboardButton(text="❓ Руководство")],
        [KeyboardButton(text="🏠 Меню")],
    ],
    resize_keyboard=True,
)


admin_set_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Ник", callback_data="set_name"),
            InlineKeyboardButton(text="Айди", callback_data="set_game_id"),
        ],
        [
            InlineKeyboardButton(text="Баланс", callback_data="set_balance"),
            InlineKeyboardButton(text="Банк", callback_data="set_bank"),
        ],
        [
            
            InlineKeyboardButton(text="Отмена", callback_data="cancel_set"),
            
        ],
    ]
)


def get_bank_main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Пополнить", callback_data="bank_save_add"),
                InlineKeyboardButton(text="➖ Снять", callback_data="bank_save_withdraw"),
            ],
            [
                InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits"),
            ],
        ]
    )

def get_deposit_terms_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 день — 3%/день", callback_data="deposit_1d")],
            [InlineKeyboardButton(text="3 дня — 5%/день", callback_data="deposit_3d")],
            [InlineKeyboardButton(text="7 дней — 7%/день", callback_data="deposit_7d")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
        ]
    )

def get_bank_action_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Положить", callback_data="bank_save_add")],
            [InlineKeyboardButton(text="➖ Снять", callback_data="bank_save_withdraw")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
        ]
    )
    
    
