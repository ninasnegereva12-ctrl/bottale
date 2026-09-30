import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand
)
from aiogram.filters import CommandStart, Command

# Получаем токен из переменных окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("ОШИБКА: Переменная BOT_TOKEN не найдена!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# 1. Настройка синей кнопки «Меню» (возле поля ввода)
async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Перезапустить бота"),
        BotCommand(command="soul", description="Пройти тест на душу"),
        BotCommand(command="profile", description="Профиль и HP"),
        BotCommand(command="fight", description="Вызвать на дуэль (в ответ)"),
        BotCommand(command="compat", description="Совместимость (в ответ)"),
        BotCommand(command="propose", description="Сделать предложение (в ответ)"),
        BotCommand(command="pet", description="Информация о питомце"),
        BotCommand(command="help", description="Полная инструкция"),
    ]
    await bot.set_my_commands(commands)


# 2. Инлайн-клавиатура с плашками под сообщением
def get_start_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💔 Определить душу", callback_data="btn_soul"),
                InlineKeyboardButton(text="📊 Мой профиль / HP", callback_data="btn_profile"),
            ],
            [
                InlineKeyboardButton(text="⚔️ Дуэль", callback_data="btn_fight_info"),
                InlineKeyboardButton(text="💞 Совместимость", callback_data="btn_compat_info"),
            ],
            [
                InlineKeyboardButton(text="🐾 Питомец", callback_data="btn_pet"),
                InlineKeyboardButton(text="📜 Все команды", callback_data="btn_help"),
            ]
        ]
    )


# 3. Приветствие в стиле Undertale при /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    undertale_text = (
        "Приветствую тебя в Подземелье, человек! 🖐️\n\n"
        "Вижу, ты уже знакома с этим миром... Но знаешь ли ты, каков цвет твоей Души? "
        "Здесь решительность, искренность и выдержка определят твою судьбу.\n\n"
        "Я — твой путеводитель. Я слежу за уровнем HP, боями, союзами и питомцами в этом чате.\n\n"
    )
    await message.answer(undertale_text, reply_markup=get_start_inline_keyboard())


# 4. Команда /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📜 **ПОЛНЫЙ СПИСОК КОМАНД:**\n\n"
        "💔 `/soul` — пройти тест на цвет души\n"
        "❤️ `/profile` — посмотреть HP и профиль\n"
        "⚔️ `/fight` — дуэль (ответом на сообщение человека)\n"
        "💞 `/compat` — проверить совместимость (ответом)\n"
        "💍 `/propose` — сделать предложение (ответом)\n"
        "✅ `/accept` — принять предложение руки и сердца\n"
        "🐾 `/pet` — открыть меню и статус питомца\n"
        "🍖 `/feed` — покормить питомца\n"
        "🎾 `/play` — поиграть с питомцем"
    )
    await message.answer(help_text, parse_mode="Markdown")


# 5. Обработка нажатий на плашки-кнопки
@dp.callback_query(F.data == "btn_soul")
async def process_soul(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "✨ Твоя Решимость наполняет тебя силами!\n"
        "Чтобы пройти тест на цвет души и узнать свои свойства, напиши команду: /soul"
    )

@dp.callback_query(F.data == "btn_profile")
async def process_profile(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📊 Чтобы узнать свой текущий уровень HP, статус брака и инвентарь, введи: /profile"
    )

@dp.callback_query(F.data == "btn_fight_info")
async def process_fight(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "⚔️ Чтобы вызвать человека на битву в стиле Undertale, ответь на его сообщение командой: /fight"
    )

@dp.callback_query(F.data == "btn_compat_info")
async def process_compat(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "💞 Ответь человеку командой /compat, чтобы узнать, насколько резонируют ваши души!"
    )

@dp.callback_query(F.data == "btn_pet")
async def process_pet(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🐾 Управление питомцем:\n"
        "• /pet — посмотреть карточку\n"
        "• /feed — покормить\n"
        "• /play — поиграть (есть шанс найти предмет!)"
    )

@dp.callback_query(F.data == "btn_help")
async def process_help(callback: CallbackQuery):
    await callback.answer()
    await cmd_help(callback.message)


# Запуск бота
async def main():
    await setup_bot_commands(bot)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                                     
