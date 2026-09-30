import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, BotCommand

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_ЕСЛИ_НЕТ_В_VARS")

router = Router()

USERS_DATA = {}

def get_chat_db(chat_id):
    if chat_id not in USERS_DATA:
        USERS_DATA[chat_id] = {}
    return USERS_DATA[chat_id]

def display_name(message: Message) -> str:
    return message.from_user.first_name or "Игрок"

def ensure_profile(chat_id, user_id, name):
    db = get_chat_db(chat_id)
    if user_id not in db:
        db[user_id] = {
            "name": name,
            "hp": 100,
            "max_hp": 100,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "msg_count": 0,
            "soul": "Неизвестна",
            "partner": None,
            "proposal_from": None,
            "pet": None,
            "items": {},
        }
    else:
        db[user_id]["name"] = name
    return db[user_id]

def save_user(chat_id, user_id, data):
    db = get_chat_db(chat_id)
    db[user_id] = data

def all_users(chat_id):
    return get_chat_db(chat_id)

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь / Команды"),
        BotCommand(command="profile", description="Профиль и HP"),
        BotCommand(command="soul", description="Узнать цвет души"),
        BotCommand(command="fight", description="Дуэль (ответом)"),
        BotCommand(command="top", description="Топ бойцов"),
        BotCommand(command="propose", description="Сделать предложение"),
        BotCommand(command="accept", description="Принять предложение"),
        BotCommand(command="divorce", description="Развестись"),
        BotCommand(command="compat", description="Совместимость"),
        BotCommand(command="namepet", description="Завести питомца"),
        BotCommand(command="pet", description="Питомец"),
        BotCommand(command="feed", description="Покормить питомца"),
        BotCommand(command="play", description="Поиграть с питомцем"),
        BotCommand(command="inventory", description="Инвентарь"),
        BotCommand(command="use", description="Использовать предмет"),
    ]
    await bot.set_my_commands(commands)

SOUL_TYPES = [
    ("❤️️ Красная", "Решимость! Твоя сила воли не знает границ."),
    ("🩵 Голубая", "Терпение! Ты умеешь ждать идеального момента."),
    ("🧡 Оранжевая", "Храбрость! Ты рвёшься в бой без страха."),
    ("💙 Синяя", "Порядочность! Честность и гармония — твой путь."),
    ("💜 Фиолетовая", "Настойчивость! Ты учишься на ошибках и идешь вперёд."),
    ("💚 Зелёная", "Доброта! Твоё милосердие исцеляет всё вокруг."),
    ("💛 Жёлтая", "Справедливость! Твой взгляд видит правду насквозь.")
]

DROP_POOL = [
    "🧪 Зелье HP (+30 HP)",
    "🍎 Яблоко (+15 HP)",
    "🗡️ Старый меч (+5 к атаке)",
    "🛡️ Деревянный щит (+5 к защите)",
    "🍬 Конфета (+10 HP)",
]

@router.message(Command("start"))
async def cmd_start(message: Message):
    ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    await message.answer(
        "✨ **ДОБРО ПОЖАЛОВАТЬ В BOTTALE!** ✨\n\n"
        "Бот успешно запущен и готов к работе!\n"
        "Используй `/help` для просмотра всех команд."
    )

@router.message(Command("soul"))
async def cmd_soul(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    soul_name, soul_desc = random.choice(SOUL_TYPES)
    p["soul"] = soul_name
    save_user(message.chat.id, message.from_user.id, p)
    await message.answer(f"💔 **Твоя душа:** {soul_name}\n✨ *{soul_desc}*")

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    pet_str = p['pet']['name'] if p['pet'] else "Нет"
    partner_str = p['partner'] if p['partner'] else "Нет"
    text = (
        f"📊 **ПРОФИЛЬ: {p['name']}**\n"
        f"💔 **Душа:** {p['soul']}\n"
        f"❤️ **HP:** {p['hp']}/{p['max_hp']}\n"
        f"⚔️ **Статистика:** {p['wins']}W / {p['losses']}L / {p.get('draws', 0)}D\n"
        f"💍 **Партнёр:** {partner_str}\n"
        f"🐾 **Питомец:** {pet_str}\n"
        f"💬 **Сообщений:** {p['msg_count']}"
    )
    await message.answer(text)
@router.message(Command("compat"))
async def cmd_compat(message: Message):
    if not message.reply_to_message:
        await message.answer("💞 Ответь этой командой на сообщение пользователя!")
        return
    u1 = display_name(message)
    u2 = display_name(message.reply_to_message)
    percent = random.randint(0, 100)
    bar_len = 10
    filled = int(percent / 100 * bar_len)
    bar = "💖" * filled + "🖤" * (bar_len - filled)
    await message.answer(f"💞 **Совместимость {u1} и {u2}:**\n[{bar}] {percent}%")

@router.message(Command("propose"))
async def cmd_propose(message: Message):
    if not message.reply_to_message:
        await message.answer("💍 Ответь этой командой на сообщение того, кому делаешь предложение!")
        return
    from_user = message.from_user
    to_user = message.reply_to_message.from_user
    if from_user.id == to_user.id:
        await message.answer("Нельзя сделать предложение самому себе!")
        return
    me = ensure_profile(message.chat.id, from_user.id, display_name(message))
    foe = ensure_profile(message.chat.id, to_user.id, display_name(message.reply_to_message))
    if me['partner']:
        await message.answer("Ты уже состоишь в браке! Сначала сделай `/divorce`.")
        return
    if foe['partner']:
        await message.answer(f"{foe['name']} уже состоите в браке!")
        return
    foe['proposal_from'] = from_user.id
    save_user(message.chat.id, to_user.id, foe)
    await message.answer(f"💍 **{me['name']}** делает предложение руки и сердца **{foe['name']}**!\nНапиши `/accept` чтобы принять.")

@router.message(Command("accept"))
async def cmd_accept(message: Message):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not me.get("proposal_from"):
        await message.answer("Тебе никто не делал предложение!")
        return
    from_id = me["proposal_from"]
    from_p = ensure_profile(message.chat.id, from_id, "Партнёр")
    me["partner"] = from_p["name"]
    from_p["partner"] = me["name"]
    me["proposal_from"] = None
    save_user(message.chat.id, message.from_user.id, me)
    save_user(message.chat.id, from_id, from_p)
    await message.answer(f"🎉 **ПОЗДРАВЛЯЕМ!** 🎉\n{me['name']} и {from_p['name']} теперь официально вместе! 💍❤️")

@router.message(Command("divorce"))
async def cmd_divorce(message: Message):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not me['partner']:
        await message.answer("Ты не состоишь в браке!")
        return
    partner_name = me['partner']
    me['partner'] = None
    save_user(message.chat.id, message.from_user.id, me)
    await message.answer(f"💔 **{me['name']}** и **{partner_name}** развелись...")

@router.message(Command("namepet"))
async def cmd_namepet(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи имя питомца: `/namepet Барсик`")
        return
    pet_name = args[1]
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    p["pet"] = {"name": pet_name, "satiety": 100, "level": 1}
    save_user(message.chat.id, message.from_user.id, p)
    await message.answer(f"🐾 У тебя появился питомец **{pet_name}**!")

@router.message(Command("pet"))
async def cmd_pet(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p["pet"]:
        await message.answer("У тебя нет питомца! Заведи через `/namepet Имя`")
        return
    pet = p["pet"]
    await message.answer(f"🐾 **ПИТОМЕЦ:** {pet['name']}\n🍖 Сытость: {pet['satiety']}%\n⭐ Уровень: {pet.get('level', 1)}")

@router.message(Command("feed"))
async def cmd_feed(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p["pet"]:
        await message.answer("У тебя нет питомца!")
        return
    p["pet"]["satiety"] = min(100, p["pet"]["satiety"] + 30)
    save_user(message.chat.id, message.from_user.id, p)
    await message.answer(f"🍽️️ Ты покормил(а) **{p['pet']['name']}**! Сытость: {p['pet']['satiety']}%")

@router.message(Command("play"))
async def cmd_play(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p["pet"]:
        await message.answer("У тебя нет питомца!")
        return
    if random.random() < 0.6:
        item = random.choice(DROP_POOL)
        p.setdefault("items", {})
        p["items"][item] = p["items"].get(item, 0) + 1
        save_user(message.chat.id, message.from_user.id, p)
        await message.answer(f"🎾 Поиграли с **{p['pet']['name']}** и нашли предмет: **{item}**!")
    else:
        await message.answer(f"🎾 Ты весело провёл время с **{p['pet']['name']}**!")

@router.message(Command("inventory"))
async def cmd_inventory(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    items = p.get("items", {})
    if not items:
        await message.answer("🎒 Твой инвентарь пуст.")
        return
    lines = ["🎒 **ТВОЙ ИНВЕНТАРЬ:**"]
    for k, v in items.items():
        lines.append(f"• {k}: {v} шт.")
    await message.answer("\n".join(lines))

@router.message(Command("use"))
async def cmd_use(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    items = p.get("items", {})
    if not items:
        await message.answer("У тебя нет предметов для использования!")
        return
    for item in list(items.keys()):
        if items[item] > 0 and "Зелье HP" in item:
            items[item] -= 1
            if items[item] == 0:
                del items[item]
            p["hp"] = min(p["max_hp"], p["hp"] + 30)
            save_user(message.chat.id, message.from_user.id, p)
            await message.answer(f"🧪 Ты выпил Зелье HP! Твоё здоровье: {p['hp']}/{p['max_hp']}")
            return
    await message.answer("У тебя нет подходящих зелий для использования.")
    @router.message(Command("fight"))
async def cmd_fight(message: Message):
    if not message.reply_to_message:
        await message.answer("⚔️ Ответь этой командой на сообщение соперника!")
        return
    foe_id = message.reply_to_message.from_user.id
    if message.from_user.id == foe_id:
        await message.answer("Нельзя драться с самим собой!")
        return
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    foe = ensure_profile(message.chat.id, foe_id, display_name(message.reply_to_message))
    
    lines = [f"⚔️ **ДУЭЛЬ:** {me['name']} VS {foe['name']}\n"]
    my_hp, foe_hp = me["hp"], foe["hp"]
    
    for round_num in range(1, 4):
        my_dmg = random.randint(10, 25)
        foe_dmg = random.randint(10, 25)
        foe_hp -= my_dmg
        my_hp -= foe_dmg
        lines.append(f"Раунд {round_num}: {me['name']} наносит {my_dmg} урона, {foe['name']} наносит {foe_dmg} урона!")
        if my_hp <= 0 or foe_hp <= 0:
            break
            
    if my_hp > 0 and foe_hp <= 0:
        me["wins"] += 1
        foe["losses"] += 1
        lines.append(f"\n🏆 **Победил {me['name']}!**")
        drop = random.choice(DROP_POOL)
        me.setdefault("items", {})
        me["items"][drop] = me["items"].get(drop, 0) + 1
        lines.append(f"🎁 Трофей: {drop}")
    elif foe_hp > 0 and my_hp <= 0:
        me["losses"] += 1
        foe["wins"] += 1
        lines.append(f"\n💀 **Победил {foe['name']}!**")
    else:
        me["draws"] = me.get("draws", 0) + 1
        foe["draws"] = foe.get("draws", 0) + 1
        lines.append("\n🤝 **Ничья!**")
        
    save_user(message.chat.id, message.from_user.id, me)
    save_user(message.chat.id, foe_id, foe)
    await message.answer("\n".join(lines))

@router.message(Command("top"))
async def cmd_top(message: Message):
    users = all_users(message.chat.id)
    ranked = sorted(users.values(), key=lambda u: u.get("wins", 0), reverse=True)
    ranked = [u for u in ranked if u.get("wins", 0) > 0][:10]
    if not ranked:
        await message.answer("Пока никто не побеждал в /fight.")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 **ТОП БОЙЦОВ ЧАТА:**\n"]
    for i, u in enumerate(ranked):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} {u['name']} — {u.get('wins', 0)}W / {u.get('losses', 0)}L")
    await message.answer("\n".join(lines))

@router.message(Command("help"))
@router.callback_query(F.data == "btn_help")
async def cmd_help(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event

    help_text = (
        "📜 **ПОЛНЫЙ СПИСОК КОМАНД:**\n\n"
        "💔 `/soul` — пройти тест и узнать цвет души\n"
        "📊 `/profile` — твоя карточка и HP\n"
        "💞 `/compat` (ответом) — проверить совместимость\n\n"
        "💍 `/propose` (ответом) — сделать предложение\n"
        "✅ `/accept` — принять предложение\n"
        "💔 `/divorce` — развестись\n\n"
        "🐾 `/namepet Имя` — завести питомца\n"
        "🐾 `/pet` — карточка питомца\n"
        "🍽️ `/feed` — покормить питомца\n"
        "🎾 `/play` — поиграть с питомцем (шанс найти предмет)\n\n"
        "⚔️ `/fight` (ответом) — дуэль с игроком\n"
        "🎒 `/inventory` — твои предметы\n"
        "🧪 `/use` — использовать зелье HP\n"
        "🏆 `/top` — топ победителей\n\n"
        "✨ *HP восстанавливается автоматически: +10 HP за каждые 5 сообщений в чате.*"
    )
    await message.answer(help_text)

@router.message(F.text & ~F.text.startswith("/"))
async def on_any_text(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    p["msg_count"] += 1
    if p["msg_count"] % 5 == 0:
        p["hp"] = min(p["max_hp"], p["hp"] + 10)
    save_user(message.chat.id, message.from_user.id, p)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await setup_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
