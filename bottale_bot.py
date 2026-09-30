import asyncio
import json
import logging
import os
import random
import threading
import time

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    BotCommand,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН")

router = Router()

# --- ДУШИ И СМОСОБНОСТИ ---

SOULS = {
    "det": {"name": "Решимость", "emoji": "❤️"},
    "bra": {"name": "Храбрость", "emoji": "🧡"},
    "jus": {"name": "Справедливость", "emoji": "💛"},
    "pat": {"name": "Терпение", "emoji": "🩵"},
    "kin": {"name": "Доброта", "emoji": "💚"},
    "int": {"name": "Искренность", "emoji": "💙"},
    "per": {"name": "Упорство", "emoji": "💜"},
}

SOUL_ABILITIES = {
    "det": "15% шанс подлечиться при своём ударе (лайфстил).",
    "bra": "+4 к урону в каждом раунде.",
    "jus": "30% шанс критического удара (×1.5 урона) вместо обычных 10%.",
    "pat": "25% шанс уменьшить входящий удар вдвое (уклонение).",
    "kin": "+5 HP в начале каждого своего раунда (регенерация).",
    "int": "Удары игнорируют чужое уклонение и защитные предметы.",
    "per": "+30% урона, пока собственное HP ниже 30%.",
}

PAIRS = {
    "det-det": (74, "Двое, одержимых одной целью — идти до конца."),
    "bra-det": (91, "Взрывное сочетание: рвутся вперёд и не дают друг другу остановиться."),
    "det-jus": (82, "Несгибаемая воля и жажда справедливости — добьются правды любой ценой."),
    "det-pat": (58, "Терпению тяжело поспевать, но именно оно не даёт решимости сгореть."),
    "det-kin": (70, "Доброта смягчает жёсткость, решимость даёт доброте смелость."),
    "det-int": (85, "Прямолинейная честность и несгибаемая воля — без недосказанностей."),
    "det-per": (88, "Оба падают и поднимаются бесконечно — один громко, другой молча."),
    "bra-bra": (63, "Двойное безрассудство: сначала прыгают, потом думают."),
    "bra-jus": (93, "Классические защитники — смелость и уверенность в правом деле."),
    "bra-pat": (52, "Огонь и штиль: трение неизбежно, но рождает лучшие сюжеты."),
    "bra-kin": (87, "Храбрость прикрывает, доброта лечит после боя."),
    "bra-int": (76, "Оба не умеют молчать о своих мыслях — шумно, но честно."),
    "bra-per": (80, "Передний край: храбрость бьёт первой, упорство держит линию."),
    "jus-jus": (66, "Два судьи в одном деле — спорят долго и принципиально."),
    "jus-pat": (84, "Справедливость, готовая ждать нужных доказательств."),
    "jus-kin": (95, "Правосудие с милосердием — почти каноничный геройский дуэт."),
    "int-jus": (90, "Честность и справедливость идут рука об руку без обмана."),
    "jus-per": (78, "Не закрывает дело, пока не добьётся правды, сколько бы ни ждать."),
    "pat-pat": (60, "Тишь да гладь — сюжету может не хватать искры."),
    "kin-pat": (89, "Мягкая пара, рядом с которой затихает даже хаос."),
    "int-pat": (81, "Комфортное молчание и честность без лишних доказательств."),
    "pat-per": (73, "Медленно, но верно — не форсируют события, просто не сдаются."),
    "kin-kin": (71, "Забота через край — рискуют разбаловать друг друга."),
    "int-kin": (86, "Тёплая честность без лишней резкости."),
    "kin-per": (92, "Тот, кто лечит, и тот, кто не даёт сдаться — держат всех на плаву."),
    "int-int": (69, "Максимально честная пара, правда режет без наркоза."),
    "int-per": (83, "Принципы без перемен и воля без предела — надёжный дуэт."),
    "per-per": (77, "Двойное упрямство — устанут все вокруг, кроме них самих."),
}

CHILD_STAGES = ["Яйцо", "Малыш", "Подросток", "Юный монстр", "Взрослый"]
PET_STAGE_EMOJIS = ["🥚", "🐣", "🦖", "👹", "😈"]

def pair_key(a: str, b: str) -> str:
    return "-".join(sorted([a, b]))

def compat(a: str, b: str):
    return PAIRS.get(pair_key(a, b), (50, "Загадочный резонанс душ..."))

def soul_label(key: str) -> str:
    if not key or key not in SOULS:
        return "Неизвестно"
    s = SOULS[key]
    return f"{s['emoji']} {s['name']}"

def soul_ability_text(key: str) -> str:
    return SOUL_ABILITIES.get(key, "")


# --- ВОПРОСЫ ТЕСТА ---

SOUL_KEYS = ["det", "bra", "jus", "pat", "kin", "int", "per"]

QUIZ_QUESTIONS = [
    {
        "text": "Друг совершил ошибку и хочет соврать, чтобы не подставлять команду. Что ты сделаешь?",
        "options": [
            ("Скажу как есть — правда важнее", {"int": 3}),
            ("Помогу прикрыть, дружба важнее", {"kin": 2, "bra": 1}),
            ("Разберусь, кто виноват и почему", {"jus": 3}),
            ("Разрулю молча, без лишней драмы", {"pat": 2, "per": 1}),
        ],
    },
    {
        "text": "Тебе дали задание, которое кажется невыполнимым. Твоя реакция?",
        "options": [
            ("Всё равно буду пытаться, пока не получится", {"det": 3}),
            ("Ринусь делать сразу, разберусь по ходу", {"bra": 3}),
            ("Составлю план и буду двигаться методично", {"pat": 2, "int": 1}),
            ("Даже если 10 раз не выйдет — попробую 11-й", {"per": 3}),
        ],
    },
    {
        "text": "Ты видишь, как обижают того, кто слабее. Твои действия?",
        "options": [
            ("Встряну немедленно, не думая о последствиях", {"bra": 3}),
            ("Разберусь, кто прав, и восстановлю справедливость", {"jus": 3}),
            ("Подойду поддержать и утешить пострадавшего", {"kin": 3}),
            ("Дождусь момента и решу вопрос спокойно", {"pat": 2}),
        ],
    },
    {
        "text": "Что для тебя важнее всего в людях?",
        "options": [
            ("Честность", {"int": 3}),
            ("Доброта и забота", {"kin": 3}),
            ("Смелость", {"bra": 2, "det": 1}),
            ("Умение не сдаваться", {"per": 2, "det": 1}),
        ],
    },
    {
        "text": "Ты потерпел крупную неудачу. Что дальше?",
        "options": [
            ("Встаю и иду дальше, будто ничего не было", {"det": 3}),
            ("Тихо переживаю, но не сдаюсь", {"per": 3}),
            ("Разбираюсь, кто виноват, и добиваюсь правды", {"jus": 2}),
            ("Успокаиваюсь и жду, пока пройдёт", {"pat": 3}),
        ],
    },
    {
        "text": "Какой у тебя стиль в конфликте?",
        "options": [
            ("Иду напролом", {"bra": 3}),
            ("Ищу компромисс и остываю первым", {"pat": 3}),
            ("Говорю прямо, что думаю, без экивоков", {"int": 3}),
            ("Забочусь, чтобы никто не пострадал", {"kin": 2}),
        ],
    },
    {
        "text": "Выбери девиз, который тебе ближе всего:",
        "options": [
            ("Никогда не сдамся", {"det": 2, "per": 2}),
            ("Помогай другим — и мир станет добрее", {"kin": 3}),
            ("Правда всегда побеждает", {"jus": 2, "int": 1}),
            ("Смелость города берёт", {"bra": 3}),
        ],
    },
]

def new_scores() -> dict:
    return {k: 0 for k in SOUL_KEYS}

def determine_soul(scores: dict) -> str:
    best = max(scores.values())
    candidates = [k for k, v in scores.items() if v == best]
    return random.choice(candidates)


# --- ПРЕДМЕТЫ ---

ITEMS = {
    "potion": {"label": "🧪 Зелье лечения", "desc": "Восстанавливает 30 HP сразу при использовании.", "kind": "heal", "value": 30},
    "sword": {"label": "🗡️ Заряженный клинок", "desc": "В следующем бою: +8 к урону в каждом раунде.", "kind": "buff_dmg", "value": 8},
    "shield": {"label": "🛡️ Оберег", "desc": "В следующем бою: весь входящий урон снижен на 40%.", "kind": "buff_def", "value": 0.4},
    "feather": {"label": "🪶 Лёгкое перо", "desc": "В следующем бою: +20% к шансу уклониться от удара.", "kind": "buff_dodge", "value": 0.20},
    "treat": {"label": "🍖 Вкусняшка", "desc": "Мгновенно повышает сытость питомца на 40.", "kind": "pet_food", "value": 40},
}

DROP_POOL = list(ITEMS.keys())

def item_label(key: str) -> str:
    return ITEMS[key]["label"] if key in ITEMS else key

def inventory_text(inv: dict) -> str:
    owned = [(k, c) for k, c in inv.items() if c > 0]
    if not owned:
        return "Пусто. Побеждай в /fight (40% шанс) или играй с питомцем /play — предметы иногда выпадают."
    lines = []
    for key, count in owned:
        item = ITEMS.get(key)
        if not item:
            continue
        lines.append(f"{item['label']} ×{count} — {item['desc']}")
    return "\n".join(lines)


# --- ХРАНИЛИЩЕ ДАННЫХ (JSON) ---

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
_lock = threading.Lock()

def _load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def _save(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def default_profile(name: str) -> dict:
    return {
        "name": name,
        "soul": None,
        "hp": 100,
        "max_hp": 100,
        "msg_count": 0,
        "married_to": None,
        "marry_score": 0,
        "marry_msg_at": 0,
        "pet_name": None,
        "pending_proposal_from": None,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "last_fight_ts": 0.0,
        "items": {},
        "active_buff": None,
        "hunger": 100,
        "bond": 0,
        "last_feed_ts": 0.0,
        "last_play_ts": 0.0,
    }

def get_user(chat_id: int, user_id: int) -> dict | None:
    with _lock:
        data = _load()
        return data.get(str(chat_id), {}).get(str(user_id))

def get_or_create_user(chat_id: int, user_id: int, name: str) -> dict:
    with _lock:
        data = _load()
        chat = data.setdefault(str(chat_id), {})
        key = str(user_id)
        if key not in chat:
            chat[key] = default_profile(name)
            _save(data)
        else:
            changed = False
            for k, v in default_profile(name).items():
                if k not in chat[key]:
                    chat[key][k] = v
                    changed = True
            if changed:
                _save(data)
        return chat[key]

def save_user(chat_id: int, user_id: int, profile: dict) -> None:
    with _lock:
        data = _load()
        chat = data.setdefault(str(chat_id), {})
        chat[str(user_id)] = profile
        _save(data)

def all_users(chat_id: int) -> dict:
    with _lock:
        data = _load()
        return dict(data.get(str(chat_id), {}))


# --- КЛАВИАТУРЫ И СЕССИИ ТЕСТА ---

FIGHT_COOLDOWN = 180
FEED_COOLDOWN = 600
PLAY_COOLDOWN = 600
ITEM_DROP_CHANCE = 0.40
PLAY_DROP_CHANCE = 0.30

quiz_sessions: dict[tuple[int, int], dict] = {}

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

def quiz_keyboard(qindex: int) -> InlineKeyboardMarkup:
    options = QUIZ_QUESTIONS[qindex]["options"]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"quiz:{qindex}:{i}")]
        for i, (label, _weights) in enumerate(options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def ensure_profile(chat_id: int, user_id: int, name: str) -> dict:
    return get_or_create_user(chat_id, user_id, name)

def display_name(message: Message) -> str:
    u = message.from_user
    return u.first_name or u.username or "Персонаж"

def target_from_reply(message: Message):
    if not message.reply_to_message:
        return None
    target = message.reply_to_message.from_user
    profile = get_user(message.chat.id, target.id)
    if profile is None:
        return None
    return target.id, profile

def compute_damage(attacker: dict, defender: dict) -> tuple[int, bool, bool, int]:
    dmg = random.randint(10, 25)

    if attacker.get("soul") == "bra":
        dmg += 4
    if attacker.get("active_buff") == "sword":
        dmg += ITEMS["sword"]["value"]

    crit_chance = 0.30 if attacker.get("soul") == "jus" else 0.10
    is_crit = random.random() < crit_chance
    if is_crit:
        dmg = int(dmg * 1.5)

    if attacker.get("soul") == "per" and attacker["hp"] <= attacker["max_hp"] * 0.3:
        dmg = int(dmg * 1.3)

    dodge_chance = 0.0
    if defender.get("soul") == "pat":
        dodge_chance += 0.25
    if defender.get("active_buff") == "feather":
        dodge_chance += ITEMS["feather"]["value"]

    dodged = False
    if attacker.get("soul") != "int" and dodge_chance > 0 and random.random() < dodge_chance:
        dmg = dmg // 2
        dodged = True

    if defender.get("active_buff") == "shield":
        dmg = int(dmg * (1 - ITEMS["shield"]["value"]))

    dmg = max(1, dmg)

    healed = 0
    if attacker.get("soul") == "det" and random.random() < 0.15:
        healed = random.randint(5, 10)

    return dmg, is_crit, dodged, healed


# --- ОБРАБОТЧИКИ КОМАНД И ИНТЕРФЕЙСА ---

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="soul", description="Пройти тест на душу"),
        BotCommand(command="profile", description="Профиль и HP"),
        BotCommand(command="fight", description="Вызвать на дуэль (в ответ)"),
        BotCommand(command="compat", description="Совместимость (в ответ)"),
        BotCommand(command="propose", description="Сделать предложение (в ответ)"),
        BotCommand(command="pet", description="Информация о питомце"),
        BotCommand(command="help", description="Полная инструкция"),
    ]
    await bot.set_my_commands(commands)

async def start_quiz_session(chat_id: int, user_id: int, send_func):
    key = (chat_id, user_id)
    quiz_sessions[key] = {"scores": new_scores(), "q": 0}
    q = QUIZ_QUESTIONS[0]
    text = f"✨ **Тест на душу** — Вопрос 1/{len(QUIZ_QUESTIONS)}:\n\n{q['text']}"
    await send_func(text, reply_markup=quiz_keyboard(0))


@router.message(Command("start"))
async def cmd_start(message: Message):
    ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    undertale_text = (
        "Приветствую тебя в Подземелье, человек! 🖐️\n\n"
        "Вижу, ты уже знакома с этим миром... Но знаешь ли ты, каков цвет твоей Души? "
        "Здесь решительность, искренность и выдержка определят твою судьбу.\n\n"
        "Выбери нужное действие на кнопках ниже или используй синюю кнопку **«Меню»** слева от поля ввода! ✨"
    )
    await message.answer(undertale_text, reply_markup=get_start_inline_keyboard())


@router.message(Command("soul"))
async def cmd_soul(message: Message):
    ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    await start_quiz_session(message.chat.id, message.from_user.id, message.answer)


@router.callback_query(F.data == "btn_soul")
async def cb_start_soul(callback: CallbackQuery):
    await callback.answer()
    ensure_profile(callback.message.chat.id, callback.from_user.id, callback.from_user.first_name or "Персонаж")
    await start_quiz_session(callback.message.chat.id, callback.from_user.id, callback.message.answer)


@router.callback_query(F.data.startswith("quiz:"))
async def on_quiz_answer(callback: CallbackQuery):
    _, qindex_str, optindex_str = callback.data.split(":")
    qindex, optindex = int(qindex_str), int(optindex_str)

    key = (callback.message.chat.id, callback.from_user.id)
    session = quiz_sessions.get(key)
    if session is None or session["q"] != qindex:
        await callback.answer("Тест устарел, начни заново нажатием /soul", show_alert=True)
        return

    _, weights = QUIZ_QUESTIONS[qindex]["options"][optindex]
    for soul_key, w in weights.items():
        session["scores"][soul_key] += w
    session["q"] += 1

    if session["q"] < len(QUIZ_QUESTIONS):
        next_q = QUIZ_QUESTIONS[session["q"]]
        await callback.message.edit_text(
            f"✨ **Тест на душу** — Вопрос {session['q'] + 1}/{len(QUIZ_QUESTIONS)}:\n\n{next_q['text']}",
            reply_markup=quiz_keyboard(session["q"]),
        )
        await callback.answer()
        return

    result = determine_soul(session["scores"])
    del quiz_sessions[key]

    profile = ensure_profile(callback.message.chat.id, callback.from_user.id, callback.from_user.first_name or "Персонаж")
    profile["soul"] = result
    save_user(callback.message.chat.id, callback.from_user.id, profile)

    await callback.message.edit_text(
        f"🎉 **Тест завершён!**\n\n"
        f"Твоя душа: {soul_label(result)}\n"
        f"⚡ Способность в бою: {soul_ability_text(result)}\n\n"
        f"Пройти тест заново можно в любой момент командой /soul."
    )
    await callback.answer()


@router.message(Command("profile"))
@router.callback_query(F.data == "btn_profile")
async def cmd_profile(event: Message | CallbackQuery):
    is_cb = isinstance(event, CallbackQuery)
    if is_cb:
        await event.answer()
        message = event.message
        user = event.from_user
    else:
        message = event
        user = event.from_user

    p = ensure_profile(message.chat.id, user.id, user.first_name or "Персонаж")
    soul_txt = soul_label(p["soul"]) if p.get("soul") else "не выбрана (/soul)"
    lines = [
        f"📊 **ТВОЙ ПРОФИЛЬ:**",
        f"👤 Имя: {p['name']}",
        f"🔷 Душа: {soul_txt}",
        f"❤️ HP: {p['hp']} / {p['max_hp']}",
        f"⚔️ Побед/поражений/ничьих: {p.get('wins', 0)}/{p.get('losses', 0)}/{p.get('draws', 0)}",
    ]
    if p.get("active_buff"):
        lines.append(f"🔋 Активный буст: {item_label(p['active_buff'])}")
    owned_count = sum(c for c in p.get("items", {}).values() if c > 0)
    lines.append(f"🎒 Инвентарь: {owned_count} предметов (/inventory)")
    if p.get("married_to"):
        spouse = get_user(message.chat.id, p["married_to"])
        if spouse:
            lines.append(f"💍 В браке с: {spouse['name']} ({p.get('marry_score', 0)}%)")
        if p.get("pet_name"):
            lines.append(f"🐾 Питомец: {p['pet_name']} (сытость {p.get('hunger', 100)}/100, /pet)")

    txt = "\n".join(lines)
    if is_cb:
        await message.answer(txt)
    else:
        await message.answer(txt)


@router.callback_query(F.data == "btn_fight_info")
async def cb_fight_info(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("⚔️ Чтобы вызвать человека на дуэль, ответь командой `/fight` на его сообщение в чате!")

@router.callback_query(F.data == "btn_compat_info")
async def cb_compat_info(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("💞 Чтобы проверить совместимость душ, ответь командой `/compat` на сообщение человека в чате!")


@router.message(Command("compat"))
async def cmd_compat(message: Message):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    target = target_from_reply(message)
    if not target:
        await message.answer("Ответь этой командой на сообщение того, с кем сверяешь совместимость.")
        return
    _, other = target
    if not me.get("soul") or not other.get("soul"):
        await message.answer("У обоих должна быть выбрана душа (/soul).")
        return
    score, text = compat(me["soul"], other["soul"])
    await message.answer(
        f"{soul_label(me['soul'])} × {soul_label(other['soul'])} — {score}%\n{text}"
    )


@router.message(Command("propose"))
async def cmd_propose(message: Message):
    ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    target = target_from_reply(message)
    if
