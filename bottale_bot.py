# ============================================================
# Bottale — телеграм-бот для флуда по Undertale.
# Всё в одном файле: тест на душу, совместимость, бои, брак и тамагочи.
# ============================================================

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
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН")



# ------------------------------------------------------------


# --- ДУШИ: данные и совместимость ---

# Данные о душах и их совместимости — та же логика, что в веб-инструменте.

SOULS = {
    "det": {"name": "Решимость", "emoji": "❤️"},
    "bra": {"name": "Храбрость", "emoji": "🧡"},
    "jus": {"name": "Справедливость", "emoji": "💛"},
    "pat": {"name": "Терпение", "emoji": "💙"},
    "kin": {"name": "Доброта", "emoji": "💚"},
    "int": {"name": "Искренность", "emoji": "🔷"},
    "per": {"name": "Упорство", "emoji": "💜"},
}

# Боевые способности душ — используются в /fight и показываются в /help и /soul.
SOUL_ABILITIES = {
    "det": "15% шанс подлечиться при своём ударе (лайфстил).",
    "bra": "+4 к урону в каждом раунде.",
    "jus": "30% шанс критического удара (×1.5 урона) вместо обычных 10%.",
    "pat": "25% шанс уменьшить входящий удар вдвое (уклонение).",
    "kin": "+5 HP в начале каждого своего раунда (регенерация).",
    "int": "Удары игнорируют чужое уклонение и защитные предметы.",
    "per": "+30% урона, пока собственное HP ниже 30%.",
}

# ключ — отсортированная пара "aaa-bbb"
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
    """Возвращает (score, text) для пары душ."""
    return PAIRS[pair_key(a, b)]


def soul_label(key: str) -> str:
    s = SOULS[key]
    return f"{s['emoji']} {s['name']}"


def soul_ability_text(key: str) -> str:
    return SOUL_ABILITIES.get(key, "")


# ------------------------------------------------------------


# --- ТЕСТ НА ДУШУ: вопросы и подсчёт баллов ---

# Тест на определение души — вопросы о характере и веса ответов по душам.
# Каждый вариант ответа даёт баллы одной или нескольким душам.
# По сумме баллов после всех вопросов выбирается душа с максимальным счётом
# (при равенстве — случайно среди лидеров).


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


# ------------------------------------------------------------


# --- ПРЕДМЕТЫ ---

# Предметы, которые можно получить за победы в бою или найти во время игры
# с питомцем (/play), и их эффекты.

ITEMS = {
    "potion": {
        "label": "🧪 Зелье лечения",
        "desc": "Восстанавливает 30 HP сразу при использовании.",
        "kind": "heal",
        "value": 30,
    },
    "sword": {
        "label": "🗡️ Заряженный клинок",
        "desc": "В следующем бою: +8 к урону в каждом раунде.",
        "kind": "buff_dmg",
        "value": 8,
    },
    "shield": {
        "label": "🛡️ Оберег",
        "desc": "В следующем бою: весь входящий урон снижен на 40%.",
        "kind": "buff_def",
        "value": 0.4,
    },
    "feather": {
        "label": "🪶 Лёгкое перо",
        "desc": "В следующем бою: +20% к шансу уклониться от удара.",
        "kind": "buff_dodge",
        "value": 0.20,
    },
    "treat": {
        "label": "🍖 Вкусняшка",
        "desc": "Мгновенно повышает сытость питомца на 40.",
        "kind": "pet_food",
        "value": 40,
    },
}

# Из этого пула случайно выпадает трофей после победы в бою или во время игры с питомцем.
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


# ------------------------------------------------------------


# --- ХРАНИЛИЩЕ ПРОФИЛЕЙ (JSON-файл) ---

# Простое хранилище на JSON-файле. Для одного флуд-чата этого достаточно —
# если бот когда-нибудь станет большим, это место для замены на нормальную БД.


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
        "married_to": None,      # user_id партнёра
        "marry_score": 0,
        "marry_msg_at": 0,
        "pet_name": None,
        "pending_proposal_from": None,  # user_id того, кто сделал предложение
        # --- бои ---
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "last_fight_ts": 0.0,
        # --- предметы ---
        "items": {},           # item_key -> количество
        "active_buff": None,   # item_key, который сработает в следующем бою
        # --- тамагочи ---
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
            # довносим новые поля старым профилям, чтобы не падать на KeyError
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
    """Возвращает {user_id_str: profile} для всех известных боту людей в чате."""
    with _lock:
        data = _load()
        return dict(data.get(str(chat_id), {}))


def find_by_name_or_id(chat_id: int, ident: str) -> tuple[int, dict] | None:
    """Ищет пользователя чата по user_id (число) или по сохранённому имени."""
    with _lock:
        data = _load()
        chat = data.get(str(chat_id), {})
        if ident.isdigit() and ident in chat:
            return int(ident), chat[ident]
        for uid, profile in chat.items():
            if profile.get("name", "").lower() == ident.lower():
                return int(uid), profile
    return None


# ------------------------------------------------------------


# --- ЛОГИКА БОТА: команды, бой, брак, тамагочи ---

import asyncio
import logging
import os
import random
import time

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)


BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН")

router = Router()

# ---------- настройки баланса ----------

FIGHT_COOLDOWN = 180     # секунд между боями у одного игрока (3 мин)
FEED_COOLDOWN = 600      # секунд между кормлениями питомца (10 мин)
PLAY_COOLDOWN = 600      # секунд между играми с питомцем (10 мин)
ITEM_DROP_CHANCE = 0.40  # шанс трофея после победы в бою
PLAY_DROP_CHANCE = 0.30  # шанс трофея во время игры с питомцем


# ---------- вспомогательное ----------

def quiz_keyboard(qindex: int) -> InlineKeyboardMarkup:
    options = QUIZ_QUESTIONS[qindex]["options"]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"quiz:{qindex}:{i}")]
        for i, (label, _weights) in enumerate(options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# состояние прохождения теста: (chat_id, user_id) -> {"scores": {...}, "q": int}
# живёт только в памяти процесса — тест короткий, переживать перезапуск бота не обязан
quiz_sessions: dict[tuple[int, int], dict] = {}


def ensure_profile(chat_id: int, user_id: int, name: str) -> dict:
    return get_or_create_user(chat_id, user_id, name)


def display_name(message: Message) -> str:
    u = message.from_user
    return u.first_name or u.username or "Персонаж"


def target_from_reply(message: Message):
    """Возвращает (user_id, profile) того, на чьё сообщение ответили, или None."""
    if not message.reply_to_message:
        return None
    target = message.reply_to_message.from_user
    profile = get_user(message.chat.id, target.id)
    if profile is None:
        return None
    return target.id, profile


def compute_damage(attacker: dict, defender: dict) -> tuple[int, bool, bool, int]:
    """Считает урон одного удара с учётом душ и активных предметов.

    Возвращает (урон, был_ли_крит, уменьшился_ли_урон_уклонением, сколько_вылечил_себе_атакующий).
    """
    dmg = random.randint(10, 25)

    if attacker["soul"] == "bra":
        dmg += 4
    if attacker.get("active_buff") == "sword":
        dmg += ITEMS["sword"]["value"]

    crit_chance = 0.30 if attacker["soul"] == "jus" else 0.10
    is_crit = random.random() < crit_chance
    if is_crit:
        dmg = int(dmg * 1.5)

    if attacker["soul"] == "per" and attacker["hp"] <= attacker["max_hp"] * 0.3:
        dmg = int(dmg * 1.3)

    dodge_chance = 0.0
    if defender["soul"] == "pat":
        dodge_chance += 0.25
    if defender.get("active_buff") == "feather":
        dodge_chance += ITEMS["feather"]["value"]

    dodged = False
    # Искренность (int) бьёт прямолинейно и игнорирует чужое уклонение.
    if attacker["soul"] != "int" and dodge_chance > 0 and random.random() < dodge_chance:
        dmg = dmg // 2
        dodged = True

    if defender.get("active_buff") == "shield":
        dmg = int(dmg * (1 - ITEMS["shield"]["value"]))

    dmg = max(1, dmg)

    healed = 0
    if attacker["soul"] == "det" and random.random() < 0.15:
        healed = random.randint(5, 10)

    return dmg, is_crit, dodged, healed


# ---------- команды: душа ----------

async def start_quiz(message: Message) -> None:
    ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    key = (message.chat.id, message.from_user.id)
    quiz_sessions[key] = {"scores": new_scores(), "q": 0}
    q = QUIZ_QUESTIONS[0]
    await message.answer(
        f"🧪 Тест на душу — вопрос 1/{len(QUIZ_QUESTIONS)}:\n\n{q['text']}",
        reply_markup=quiz_keyboard(0),
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    profile = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if profile["soul"] is None:
        await message.answer(
            "Привет! Я слежу за душами, HP, боями, браками и питомцами в этом флуде.\n"
            "Сейчас определим твою душу — ответь на несколько вопросов о характере."
        )
        await start_quiz(message)
    else:
        await message.answer(
            f"Ты уже {soul_label(profile['soul'])}. Команда /help покажет все команды."
        )


@router.message(Command("soul"))
async def cmd_soul(message: Message):
    await start_quiz(message)


@router.callback_query(F.data.startswith("quiz:"))
async def on_quiz_answer(callback: CallbackQuery):
    _, qindex_str, optindex_str = callback.data.split(":")
    qindex, optindex = int(qindex_str), int(optindex_str)

    key = (callback.message.chat.id, callback.from_user.id)
    session = quiz_sessions.get(key)
    if session is None or session["q"] != qindex:
        # чужой/устаревший тест (например, бота перезапустили) — просим начать заново
        await callback.answer("Тест устарел, начни заново: /soul", show_alert=True)
        return

    _, weights = QUIZ_QUESTIONS[qindex]["options"][optindex]
    for soul_key, w in weights.items():
        session["scores"][soul_key] += w
    session["q"] += 1

    if session["q"] < len(QUIZ_QUESTIONS):
        next_q = QUIZ_QUESTIONS[session["q"]]
        await callback.message.edit_text(
            f"Вопрос {session['q'] + 1}/{len(QUIZ_QUESTIONS)}:\n\n{next_q['text']}",
            reply_markup=quiz_keyboard(session["q"]),
        )
        await callback.answer()
        return

    result = determine_soul(session["scores"])
    del quiz_sessions[key]

    profile = ensure_profile(callback.message.chat.id, callback.from_user.id,
                              callback.from_user.first_name or "Персонаж")
    profile["soul"] = result
    save_user(callback.message.chat.id, callback.from_user.id, profile)

    await callback.message.edit_text(
        f"Тест завершён!\n\nТвоя душа: {soul_label(result)}\n"
        f"Способность в бою: {soul_ability_text(result)}\n\n"
        f"Пройти тест заново можно командой /soul."
    )
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    soul_txt = soul_label(p["soul"]) if p["soul"] else "не выбрана (/soul)"
    lines = [
        f"👤 {p['name']}",
        f"Душа: {soul_txt}",
        f"HP: {p['hp']} / {p['max_hp']}",
        f"Сообщений отправлено: {p['msg_count']}",
        f"Побед/поражений/ничьих: {p.get('wins', 0)}/{p.get('losses', 0)}/{p.get('draws', 0)}",
    ]
    if p.get("active_buff"):
        lines.append(f"🔋 Готов к бою эффект: {item_label(p['active_buff'])}")
    owned_count = sum(c for c in p.get("items", {}).values() if c > 0)
    lines.append(f"🎒 Предметов в инвентаре: {owned_count} (/inventory)")
    if p["married_to"]:
        spouse = get_user(message.chat.id, p["married_to"])
        if spouse:
            lines.append(f"💍 В браке с {spouse['name']} ({p['marry_score']}%)")
        if p["pet_name"]:
            lines.append(f"🐾 Питомец: {p['pet_name']} (сытость {p.get('hunger', 100)}/100, /pet)")
    await message.answer("\n".join(lines))


@router.message(Command("compat"))
async def cmd_compat(message: Message):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    target = target_from_reply(message)
    if not target:
        await message.answer("Ответь этой командой на сообщение того, с кем сверяешь совместимость.")
        return
    _, other = target
    if not me["soul"] or not other["soul"]:
        await message.answer("У обоих должна быть выбрана душа (/soul).")
        return
    score, text = compat(me["soul"], other["soul"])
    await message.answer(
        f"{soul_label(me['soul'])} × {soul_label(other['soul'])} — {score}%\n{text}"
    )


# ---------- команды: брак и питомец ----------

@router.message(Command("propose"))
async def cmd_propose(message: Message):
    ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    target = target_from_reply(message)
    if not target:
        await message.answer("Ответь этой командой на сообщение того, кому делаешь предложение.")
        return
    target_id, target_profile = target
    if target_profile.get("married_to"):
        await message.answer(f"{target_profile['name']} уже в браке.")
        return
    target_profile["pending_proposal_from"] = message.from_user.id
    save_user(message.chat.id, target_id, target_profile)
    await message.answer(
        f"💌 {display_name(message)} сделал(а) предложение {target_profile['name']}!\n"
        f"{target_profile['name']}, набери /accept, чтобы согласиться."
    )


@router.message(Command("accept"))
async def cmd_accept(message: Message):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    proposer_id = me.get("pending_proposal_from")
    if not proposer_id:
        await message.answer("Тебе никто не делал предложение.")
        return
    proposer = get_user(message.chat.id, proposer_id)
    if not proposer or not me["soul"] or not proposer["soul"]:
        await message.answer("У обоих должна быть выбрана душа (/soul), чтобы пожениться.")
        return
    score, _ = compat(me["soul"], proposer["soul"])
    for who in (me, proposer):
        who["marry_score"] = score
        who["pet_name"] = None
        who["hunger"] = 100
        who["bond"] = 0
        who["last_feed_ts"] = 0.0
        who["last_play_ts"] = 0.0
    me["married_to"] = proposer_id
    me["marry_msg_at"] = me["msg_count"]
    me["pending_proposal_from"] = None
    proposer["married_to"] = message.from_user.id
    proposer["marry_msg_at"] = proposer["msg_count"]
    save_user(message.chat.id, message.from_user.id, me)
    save_user(message.chat.id, proposer_id, proposer)
    await message.answer(
        f"💍 {proposer['name']} и {me['name']} теперь официально женаты! "
        f"Совместимость душ: {score}%."
    )


@router.message(Command("divorce"))
async def cmd_divorce(message: Message):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not me["married_to"]:
        await message.answer("Ты не в браке.")
        return
    spouse_id = me["married_to"]
    spouse = get_user(message.chat.id, spouse_id)
    me.update(married_to=None, marry_score=0, marry_msg_at=0, pet_name=None,
              hunger=100, bond=0, last_feed_ts=0.0, last_play_ts=0.0)
    save_user(message.chat.id, message.from_user.id, me)
    if spouse:
        spouse.update(married_to=None, marry_score=0, marry_msg_at=0, pet_name=None,
                       hunger=100, bond=0, last_feed_ts=0.0, last_play_ts=0.0)
        save_user(message.chat.id, spouse_id, spouse)
    await message.answer(f"💔 {me['name']} и {spouse['name'] if spouse else 'партнёр'} развелись.")


@router.message(Command("namepet"))
async def cmd_namepet(message: Message, command: CommandObject):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p["married_to"]:
        await message.answer("Питомец доступен только женатым парам (/propose и /accept).")
        return
    if not command.args:
        await message.answer("Использование: /namepet Имя")
        return
    p["pet_name"] = command.args.strip()
    p["hunger"] = 100
    p["bond"] = 0
    save_user(message.chat.id, message.from_user.id, p)
    await message.answer(f"🐾 Теперь у вас есть {p['pet_name']}! Корми его /feed и играй /play.")


@router.message(Command("pet"))
async def cmd_pet(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p["married_to"]:
        await message.answer("Питомец доступен только женатым парам.")
        return
    if not p["pet_name"]:
        await message.answer("Питомца ещё нет. Заведи его: /namepet Имя")
        return
    progress = max(0, p["msg_count"] - p["marry_msg_at"]) + p.get("bond", 0) * 2
    hunger = p.get("hunger", 100)
    if hunger < 30:
        progress = progress // 2  # голодный питомец растёт вдвое медленнее
    stage_idx = min(len(CHILD_STAGES) - 1, progress // 15)
    next_at = (stage_idx + 1) * 15
    stage_text = "максимальная стадия" if stage_idx == len(CHILD_STAGES) - 1 else f"{progress}/{next_at} до роста"
    if hunger >= 60:
        hunger_note = "😋"
    elif hunger >= 30:
        hunger_note = "😐"
    else:
        hunger_note = "😫 голоден! /feed"
    await message.answer(
        f"{PET_STAGE_EMOJIS[stage_idx]} {p['pet_name']} — стадия: {CHILD_STAGES[stage_idx]}\n"
        f"{stage_text}\n"
        f"Сытость: {hunger}/100 {hunger_note}\n"
        f"Привязанность: {p.get('bond', 0)} (/play)"
    )


@router.message(Command("feed"))
async def cmd_feed(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p["married_to"] or not p["pet_name"]:
        await message.answer("Питомец доступен только женатым парам, у которых он уже назван (/namepet).")
        return
    now = time.time()
    remaining = FEED_COOLDOWN - (now - p.get("last_feed_ts", 0))
    if remaining > 0:
        await message.answer(f"{p['pet_name']} ещё сыт(а). Попробуй покормить через {int(remaining // 60) + 1} мин.")
        return
    p["hunger"] = min(100, p.get("hunger", 100) + 25)
    p["last_feed_ts"] = now
    save_user(message.chat.id, message.from_user.id, p)
    await message.answer(f"🍽️ {p['pet_name']} покормлен(а)! Сытость: {p['hunger']}/100.")


@router.message(Command("play"))
async def cmd_play(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p["married_to"] or not p["pet_name"]:
        await message.answer("Питомец доступен только женатым парам, у которых он уже назван (/namepet).")
        return
    now = time.time()
    remaining = PLAY_COOLDOWN - (now - p.get("last_play_ts", 0))
    if remaining > 0:
        await message.answer(f"{p['pet_name']} устал(а) играть. Попробуй через {int(remaining // 60) + 1} мин.")
        return
    p["bond"] = p.get("bond", 0) + 1
    p["last_play_ts"] = now
    found_text = ""
    if random.random() < PLAY_DROP_CHANCE:
        drop = random.choice(DROP_POOL)
        p.setdefault("items", {})
        p["items"][drop] = p["items"].get(drop, 0) + 1
        found_text = f"\n🎁 {p['pet_name']} что-то принёс(ла): {item_label(drop)}!"
    save_user(message.chat.id, message.from_user.id, p)
    await message.answer(f"🎾 Вы поиграли с {p['pet_name']}! Привязанность: {p['bond']}.{found_text}")


# ---------- команды: предметы ----------

@router.message(Command("inventory"))
async def cmd_inventory(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    await message.answer(f"🎒 Инвентарь {p['name']}:\n{inventory_text(p.get('items', {}))}")


@router.message(Command("use"))
async def cmd_use(message: Message, command: CommandObject):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not command.args:
        keys = ", ".join(ITEMS.keys())
        await message.answer(f"Использование: /use <предмет>\nДоступные ключи: {keys}")
        return
    key = command.args.strip().lower()
    item = ITEMS.get(key)
    if not item:
        await message.answer("Нет такого предмета. Посмотри /inventory.")
        return
    have = p.get("items", {}).get(key, 0)
    if have <= 0:
        await message.answer(f"У тебя нет «{item['label']}». Побеждай в /fight, чтобы получить предметы.")
        return

    if item["kind"] == "heal":
        healed = min(item["value"], p["max_hp"] - p["hp"])
        p["hp"] = min(p["max_hp"], p["hp"] + item["value"])
        p["items"][key] -= 1
        await message.answer(f"🧪 Выпито! +{healed} HP. Сейчас: {p['hp']}/{p['max_hp']}.")
    elif item["kind"] in ("buff_dmg", "buff_def", "buff_dodge"):
        p["active_buff"] = key
        p["items"][key] -= 1
        await message.answer(f"{item['label']} активирован — эффект сработает в следующем бою /fight.")
    elif item["kind"] == "pet_food":
        if not p["married_to"] or not p["pet_name"]:
            await message.answer("У тебя нет питомца — вкусняшка не пригодится.")
            return
        p["hunger"] = min(100, p.get("hunger", 100) + item["value"])
        p["items"][key] -= 1
        await message.answer(f"🍖 {p['pet_name']} доволен! Сытость: {p['hunger']}/100.")
    save_user(message.chat.id, message.from_user.id, p)


# ---------- команды: бой и рейтинг ----------

@router.message(Command("fight"))
async def cmd_fight(message: Message):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    target = target_from_reply(message)
    if not target:
        await message.answer("Ответь этой командой на сообщение того, с кем хочешь драться.")
        return
    foe_id, foe = target
    if foe_id == message.from_user.id:
        await message.answer("С самим собой не подраться — выбери другого противника.")
        return
    if not me["soul"] or not foe["soul"]:
        await message.answer("У обоих должна быть выбрана душа (/soul).")
        return

    now = time.time()
    remaining = FIGHT_COOLDOWN - (now - me.get("last_fight_ts", 0))
    if remaining > 0:
        await message.answer(f"⏳ Отдохни перед следующим боем: ещё {int(remaining)} сек.")
        return

    my_hp, foe_hp = me["hp"], foe["hp"]
    lines = [f"⚔️ {me['name']} ({soul_label(me['soul'])}) против {foe['name']} ({soul_label(foe['soul'])})"]
    rnd = 1
    while my_hp > 0 and foe_hp > 0 and rnd <= 6:
        if me["soul"] == "kin":
            my_hp = min(me["max_hp"], my_hp + 5)
        if foe["soul"] == "kin":
            foe_hp = min(foe["max_hp"], foe_hp + 5)

        my_dmg, my_crit, foe_dodged, my_heal = compute_damage(
            {**me, "hp": my_hp}, {**foe, "hp": foe_hp}
        )
        foe_hp = max(0, foe_hp - my_dmg)
        my_hp = min(me["max_hp"], my_hp + my_heal)
        note = f"Раунд {rnd}: {me['name']} наносит {my_dmg}"
        if my_crit:
            note += " 💥крит!"
        if foe_dodged:
            note += " (частично уклонился)"
        if my_heal:
            note += f", лечится на {my_heal}"
        note += f". HP {foe['name']}: {foe_hp}"
        lines.append(note)
        if foe_hp <= 0:
            break

        foe_dmg, foe_crit, my_dodged, foe_heal = compute_damage(
            {**foe, "hp": foe_hp}, {**me, "hp": my_hp}
        )
        my_hp = max(0, my_hp - foe_dmg)
        foe_hp = min(foe["max_hp"], foe_hp + foe_heal)
        note2 = f"Раунд {rnd}: {foe['name']} наносит {foe_dmg}"
        if foe_crit:
            note2 += " 💥крит!"
        if my_dodged:
            note2 += " (частично уклонился)"
        if foe_heal:
            note2 += f", лечится на {foe_heal}"
        note2 += f". HP {me['name']}: {my_hp}"
        lines.append(note2)
        rnd += 1

    me["active_buff"] = None
    foe["active_buff"] = None
    me["hp"], foe["hp"] = my_hp, foe_hp
    me["last_fight_ts"] = now

    if foe_hp <= 0 and my_hp > 0:
        me["wins"] = me.get("wins", 0) + 1
        foe["losses"] = foe.get("losses", 0) + 1
        lines.append(f"🏆 Победа за {me['name']}!")
        if random.random() < ITEM_DROP_CHANCE:
            drop = random.choice(DROP_POOL)
            me.setdefault("items", {})
            me["items"][drop] = me["items"].get(drop, 0) + 1
            lines.append(f"🎁 Трофей: {item_label(drop)}!")
    elif my_hp <= 0 and foe_hp > 0:
        me["losses"] = me.get("losses", 0) + 1
        foe["wins"] = foe.get("wins", 0) + 1
        lines.append(f"💀 {foe['name']} побеждает в этой стычке.")
    else:
        me["draws"] = me.get("draws", 0) + 1
        foe["draws"] = foe.get("draws", 0) + 1
        lines.append("Бой прерван — оба ещё стоят на ногах.")

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
    lines = ["🏆 Топ бойцов флуда:"]
    for i, u in enumerate(ranked):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} {u['name']} — {u.get('wins', 0)}W / {u.get('losses', 0)}L")
    await message.answer("\n".join(lines))


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Душа:\n"
        "/soul — пройти тест и узнать свою душу (можно пройти заново)\n"
        "/profile — твоя карточка\n"
        "/compat (ответом на сообщение) — совместимость душ\n\n"
        "Брак и питомец:\n"
        "/propose (ответом на сообщение) — сделать предложение\n"
        "/accept — принять предложение\n"
        "/divorce — развестись\n"
        "/namepet Имя — завести питомца (после свадьбы)\n"
        "/pet — карточка питомца\n"
        "/feed — покормить питомца (раз в 10 мин)\n"
        "/play — поиграть с питомцем (раз в 10 мин, шанс найти предмет)\n\n"
        "Бой и предметы:\n"
        "/fight (ответом на сообщение) — бой, раз в 3 мин\n"
        "/inventory — твои предметы\n"
        "/use <предмет> — использовать/активировать предмет\n"
        "/top — рейтинг по победам\n\n"
        "HP восстанавливается автоматически: +10 HP за каждые 5 сообщений во флуде."
    )


# ---------- авто-подсчёт сообщений ----------

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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
