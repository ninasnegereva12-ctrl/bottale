import asyncio
import itertools
import json
import logging
import os
import random
import threading
import time

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН")

router = Router()

# --- ДУШИ И СПОСОБНОСТИ ---

SOULS = {
    "det": {"name": "Решимость", "emoji": "❤️"},
    "bra": {"name": "Храбрость", "emoji": "🧡"},
    "jus": {"name": "Справедливость", "emoji": "💛"},
    "pat": {"name": "Терпение", "emoji": "💙"},
    "kin": {"name": "Доброта", "emoji": "💚"},
    "int": {"name": "Искренность", "emoji": "🔷"},
    "per": {"name": "Упорство", "emoji": "💜"},
}

SOUL_ABILITIES = {
    "det": "15% шанс подлечиться при своём ударе (лайфстил).",
    "bra": "+4 к урону в каждом раунде.",
    "jus": "30% шанс критического удара (×1.5 урона) вместо обычных 10%.",
    "pat": "Больше времени среагировать и увернуться от удара.",
    "kin": "+5 HP в начале каждого своего раунда (регенерация).",
    "int": "Удар нельзя увернуть вовремя — честность бьёт без промаха.",
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
    "potion": {
        "label": "🧪 Зелье лечения",
        "desc": "Восстанавливает 30 HP сразу при использовании.",
        "kind": "heal",
        "value": 30,
    },
    "sword": {
        "label": "🗡️ Заряженный клинок",
        "desc": "В следующей дуэли: +8 к урону при каждом твоём ударе.",
        "kind": "buff_dmg",
        "value": 8,
    },
    "shield": {
        "label": "🛡️ Оберег",
        "desc": "В следующей дуэли: весь входящий урон снижен на 40%.",
        "kind": "buff_def",
        "value": 0.4,
    },
    "feather": {
        "label": "🪶 Лёгкое перо",
        "desc": "В следующей дуэли: +1 сек. на реакцию, чтобы увернуться.",
        "kind": "buff_dodge",
        "value": 1.0,
    },
    "treat": {
        "label": "🍖 Вкусняшка",
        "desc": "Мгновенно повышает сытость питомца на 40.",
        "kind": "pet_food",
        "value": 40,
    },
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
                InlineKeyboardButton(
                    text="💔 Определить душу", callback_data="btn_soul"
                ),
                InlineKeyboardButton(
                    text="📊 Мой профиль / HP", callback_data="btn_profile"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚔️ Дуэль", callback_data="btn_fight_info"
                ),
                InlineKeyboardButton(
                    text="💞 Совместимость", callback_data="btn_compat_info"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🐾 Питомец", callback_data="btn_pet"
                ),
                InlineKeyboardButton(
                    text="📜 Все команды", callback_data="btn_help"
                ),
            ],
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


def compute_attack(attacker: dict) -> tuple[int, bool, int]:
    """Считает урон атаки без учёта уклонения (оно теперь решается игроком вручную)."""
    dmg = random.randint(10, 25)

    if attacker.get("soul") == "bra":
        dmg += 4
    if attacker.get("buff") == "sword":
        dmg += ITEMS["sword"]["value"]

    crit_chance = 0.30 if attacker.get("soul") == "jus" else 0.10
    is_crit = random.random() < crit_chance
    if is_crit:
        dmg = int(dmg * 1.5)

    if attacker.get("soul") == "per" and attacker["hp"] <= attacker["max_hp"] * 0.3:
        dmg = int(dmg * 1.3)

    dmg = max(1, dmg)

    healed = 0
    if attacker.get("soul") == "det" and random.random() < 0.15:
        healed = random.randint(5, 10)

    return dmg, is_crit, healed


def dodge_window(defender_soul: str | None, defender_buff: str | None) -> float:
    """Сколько секунд даётся защищающемуся, чтобы нажать «Увернуться»."""
    window = BASE_DODGE_WINDOW
    if defender_soul == "pat":
        window += 1.0
    if defender_buff == "feather":
        window += ITEMS["feather"]["value"]
    return window


# --- БОЕВАЯ СИСТЕМА: ПОШАГОВАЯ ДУЭЛЬ В СТИЛЕ UNDERTALE ---
# Меню FIGHT / ACT / ITEM / MERCY на каждый ход + ручное уклонение по таймингу.

BASE_DODGE_WINDOW = 2.5
MERCY_THRESHOLD = 5
MAX_TURNS = 24  # суммарно на двоих, чтобы не зависало навечно

battles: dict[int, dict] = {}
_battle_ids = itertools.count(1)

# ACT-реплики под тип души соперника: (текст, очки к "смягчению").
# Чем точнее бьёшь в характер — тем быстрее откроется MERCY.
ACT_OPTIONS = {
    "det": [
        ("Сказать, что уважаешь её решимость", 3),
        ("Напомнить, что сдаваться нельзя", 1),
        ("Предложить передышку", 0),
    ],
    "bra": [
        ("Признать её смелость вслух", 3),
        ("Подначить на честный бой", 1),
        ("Предложить поговорить спокойно", 0),
    ],
    "jus": [
        ("Согласиться, что она права", 3),
        ("Напомнить о правилах боя", 1),
        ("Попросить справедливости", 2),
    ],
    "pat": [
        ("Сказать, что цените её терпение", 3),
        ("Подождать её хода молча", 2),
        ("Поторопить", -1),
    ],
    "kin": [
        ("Поблагодарить за доброту", 3),
        ("Попросить о помощи", 2),
        ("Поддразнить", -1),
    ],
    "int": [
        ("Спросить её мнение честно", 3),
        ("Сказать правду в лицо", 2),
        ("Соврать, что всё нормально", -2),
    ],
    "per": [
        ("Сказать, что верите в неё", 3),
        ("Напомнить, что она не одна", 2),
        ("Сказать сдаться", -2),
    ],
}


def new_battle_state(chat_id: int, p1_id: int, p1: dict, p2_id: int, p2: dict) -> int:
    battle_id = next(_battle_ids)
    battles[battle_id] = {
        "chat_id": chat_id,
        "ids": {1: p1_id, 2: p2_id},
        "profiles": {p1_id: p1, p2_id: p2},
        "hp": {p1_id: p1["hp"], p2_id: p2["hp"]},
        "max_hp": {p1_id: p1["max_hp"], p2_id: p2["max_hp"]},
        "soul": {p1_id: p1.get("soul"), p2_id: p2.get("soul")},
        "buff": {p1_id: p1.get("active_buff"), p2_id: p2.get("active_buff")},
        "soften": {p1_id: 0, p2_id: 0},  # soften[X] = насколько X смягчился к тебе
        "turn": p1_id,
        "turns_done": 0,
        "log": [],
        "pending": None,
        "chat_msg_id": None,
    }
    return battle_id


def other(sess: dict, user_id: int) -> int:
    ids = sess["ids"]
    return ids[2] if ids[1] == user_id else ids[1]


def battle_menu_keyboard(battle_id: int, show_mercy: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="⚔️ FIGHT", callback_data=f"bt:{battle_id}:fight"),
            InlineKeyboardButton(text="👁️ ACT", callback_data=f"bt:{battle_id}:act"),
        ],
        [
            InlineKeyboardButton(text="🎒 ITEM", callback_data=f"bt:{battle_id}:item"),
            InlineKeyboardButton(
                text="🤍 MERCY" + ("" if show_mercy else " 🔒"),
                callback_data=f"bt:{battle_id}:mercy",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def act_keyboard(battle_id: int, soul: str | None) -> InlineKeyboardMarkup:
    options = ACT_OPTIONS.get(soul, [("Присмотреться", 1)])
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"bt:{battle_id}:act:{i}")]
        for i, (label, _pts) in enumerate(options)
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bt:{battle_id}:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def item_keyboard(battle_id: int, owned: dict) -> InlineKeyboardMarkup:
    rows = []
    for key, count in owned.items():
        if count > 0 and ITEMS[key]["kind"] == "heal":
            rows.append([
                InlineKeyboardButton(
                    text=f"{ITEMS[key]['label']} ×{count}",
                    callback_data=f"bt:{battle_id}:item:{key}",
                )
            ])
    if not rows:
        rows.append([InlineKeyboardButton(text="Предметов для лечения нет", callback_data=f"bt:{battle_id}:menu")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bt:{battle_id}:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dodge_keyboard(battle_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛡️ УВЕРНИСЬ!", callback_data=f"bt:{battle_id}:dodge")]]
    )


def hp_bar(hp: int, max_hp: int, width: int = 10) -> str:
    hp = max(0, hp)
    filled = round(width * hp / max_hp) if max_hp else 0
    return "🟩" * filled + "⬛" * (width - filled) + f" {hp}/{max_hp}"


def battle_status_text(sess: dict) -> str:
    ids = sess["ids"]
    p1, p2 = ids[1], ids[2]
    log_tail = "\n".join(sess["log"][-6:])
    turn_name = sess["profiles"][sess["turn"]]["name"]
    return (
        f"⚔️ {sess['profiles'][p1]['name']} ({soul_label(sess['soul'][p1])})\n"
        f"{hp_bar(sess['hp'][p1], sess['max_hp'][p1])}\n\n"
        f"🆚 {sess['profiles'][p2]['name']} ({soul_label(sess['soul'][p2])})\n"
        f"{hp_bar(sess['hp'][p2], sess['max_hp'][p2])}\n\n"
        f"{log_tail}\n\n"
        f"➡️ Ход: {turn_name}"
    )


async def render_battle_menu(battle_id: int, bot: Bot) -> None:
    sess = battles.get(battle_id)
    if not sess:
        return
    target = other(sess, sess["turn"])
    show_mercy = sess["soften"][target] >= MERCY_THRESHOLD
    try:
        await bot.edit_message_text(
            chat_id=sess["chat_id"],
            message_id=sess["chat_msg_id"],
            text=battle_status_text(sess),
            reply_markup=battle_menu_keyboard(battle_id, show_mercy),
        )
    except Exception:
        pass


async def dodge_timeout(battle_id: int, bot: Bot, token: int, window: float) -> None:
    await asyncio.sleep(window)
    sess = battles.get(battle_id)
    if not sess or not sess.get("pending") or sess["pending"].get("token") != token:
        return
    await resolve_attack(battle_id, dodged=False, bot=bot)


async def resolve_attack(battle_id: int, dodged: bool, bot: Bot) -> None:
    sess = battles.get(battle_id)
    if not sess or not sess.get("pending"):
        return
    pend = sess["pending"]
    sess["pending"] = None

    attacker_id, defender_id = pend["attacker_id"], pend["defender_id"]
    dmg = pend["dmg"]
    note = f"{sess['profiles'][attacker_id]['name']} бьёт"
    if pend["crit"]:
        note += " 💥 КРИТ!"
    if dodged and not pend["ignore_dodge"]:
        dmg = max(1, dmg // 2)
        note += " — частично увёрнулся(-ась)!"
    elif pend["ignore_dodge"]:
        note += " — увернуться не вышло, бьёт точно."
    if sess["buff"].get(defender_id) == "shield":
        dmg = max(1, int(dmg * (1 - ITEMS["shield"]["value"])))

    sess["hp"][defender_id] = max(0, sess["hp"][defender_id] - dmg)
    note += f" {dmg} урона. HP {sess['profiles'][defender_id]['name']}: {sess['hp'][defender_id]}"
    if pend["heal"]:
        sess["hp"][attacker_id] = min(
            sess["max_hp"][attacker_id], sess["hp"][attacker_id] + pend["heal"]
        )
        note += f" (атакующий лечится на {pend['heal']})"
    sess["log"].append(note)

    if sess["hp"][defender_id] <= 0:
        await finish_battle(battle_id, winner_id=attacker_id, bot=bot)
        return

    sess["turn"] = defender_id
    sess["turns_done"] += 1
    if sess["turns_done"] >= MAX_TURNS:
        await finish_battle(battle_id, winner_id=None, bot=bot)
        return
    await render_battle_menu(battle_id, bot)


async def finish_battle(battle_id: int, winner_id: int | None, bot: Bot, mercy_by: int | None = None) -> None:
    sess = battles.pop(battle_id, None)
    if not sess:
        return
    ids = sess["ids"]
    p1_id, p2_id = ids[1], ids[2]
    chat_id = sess["chat_id"]
    now = time.time()

    profiles = {}
    for uid in (p1_id, p2_id):
        prof = get_user(chat_id, uid) or sess["profiles"][uid]
        prof["hp"] = sess["hp"][uid]
        prof["active_buff"] = None
        prof["last_fight_ts"] = now
        profiles[uid] = prof

    lines = [battle_status_text(sess).split("➡️")[0].strip(), ""]

    if mercy_by is not None:
        spared_id = other(sess, mercy_by)
        lines.append(
            f"🤍 {profiles[mercy_by]['name']} решает пощадить {profiles[spared_id]['name']}. "
            f"Бой окончен миром."
        )
        if random.random() < ITEM_DROP_CHANCE:
            drop = random.choice(DROP_POOL)
            profiles[mercy_by].setdefault("items", {})
            profiles[mercy_by]["items"][drop] = profiles[mercy_by]["items"].get(drop, 0) + 1
            lines.append(f"🎁 Трофей за милосердие: {item_label(drop)}!")
    elif winner_id is None:
        for uid in (p1_id, p2_id):
            profiles[uid]["draws"] = profiles[uid].get("draws", 0) + 1
        lines.append("⏳ Дуэль затянулась — оба ещё стоят на ногах. Ничья.")
    else:
        loser_id = other(sess, winner_id)
        profiles[winner_id]["wins"] = profiles[winner_id].get("wins", 0) + 1
        profiles[loser_id]["losses"] = profiles[loser_id].get("losses", 0) + 1
        lines.append(f"🏆 Победа за {profiles[winner_id]['name']}!")
        if random.random() < ITEM_DROP_CHANCE:
            drop = random.choice(DROP_POOL)
            profiles[winner_id].setdefault("items", {})
            profiles[winner_id]["items"][drop] = profiles[winner_id]["items"].get(drop, 0) + 1
            lines.append(f"🎁 Трофей: {item_label(drop)}!")

    for uid, prof in profiles.items():
        save_user(chat_id, uid, prof)

    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=sess["chat_msg_id"], text="\n".join(lines)
        )
    except Exception:
        await bot.send_message(chat_id, "\n".join(lines))


# --- ОБРАБОТЧИКИ КОМАНД И ИНТЕРФЕЙСА ---


async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="soul", description="Пройти тест на душу"),
        BotCommand(command="profile", description="Профиль и HP"),
        BotCommand(command="fight", description="Вызвать на дуэль (в ответ)"),
        BotCommand(command="compat", description="Совместимость (в ответ)"),
        BotCommand(
            command="propose", description="Сделать предложение (в ответ)"
        ),
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
    await message.answer(
        undertale_text, reply_markup=get_start_inline_keyboard()
    )


@router.message(Command("soul"))
async def cmd_soul(message: Message):
    ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    await start_quiz_session(
        message.chat.id, message.from_user.id, message.answer
    )


@router.callback_query(F.data == "btn_soul")
async def cb_start_soul(callback: CallbackQuery):
    await callback.answer()
    ensure_profile(
        callback.message.chat.id,
        callback.from_user.id,
        callback.from_user.first_name or "Персонаж",
    )
    await start_quiz_session(
        callback.message.chat.id,
        callback.from_user.id,
        callback.message.answer,
    )


@router.callback_query(F.data.startswith("quiz:"))
async def on_quiz_answer(callback: CallbackQuery):
    _, qindex_str, optindex_str = callback.data.split(":")
    qindex, optindex = int(qindex_str), int(optindex_str)

    key = (callback.message.chat.id, callback.from_user.id)
    session = quiz_sessions.get(key)
    if session is None or session["q"] != qindex:
        await callback.answer(
            "Тест устарел, начни заново нажатием /soul", show_alert=True
        )
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

    profile = ensure_profile(
        callback.message.chat.id,
        callback.from_user.id,
        callback.from_user.first_name or "Персонаж",
    )
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
        "📊 **ТВОЙ ПРОФИЛЬ:**",
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
            lines.append(
                f"💍 В браке с: {spouse['name']} ({p.get('marry_score', 0)}%)"
            )
        if p.get("pet_name"):
            lines.append(
                f"🐾 Питомец: {p['pet_name']} (сытость {p.get('hunger', 100)}/100, /pet)"
            )

    txt = "\n".join(lines)
    await message.answer(txt)


@router.callback_query(F.data == "btn_fight_info")
async def cb_fight_info(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "⚔️ Чтобы вызвать человека на дуэль, ответь командой `/fight` на его сообщение в чате!"
    )


@router.message(Command("compat"))
async def cmd_compat(message: Message):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    target = target_from_reply(message)
    if not target:
        await message.answer(
            "Ответь этой командой на сообщение того, с кем сверяешь совместимость."
        )
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
    if not target:
        await message.answer(
            "Ответь этой командой на сообщение того, кому делаешь предложение."
        )
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
    if not proposer or not me.get("soul") or not proposer.get("soul"):
        await message.answer(
            "У обоих должна быть выбрана душа (/soul), чтобы пожениться."
        )
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
    if not me.get("married_to"):
        await message.answer("Ты не в браке.")
        return
    spouse_id = me["married_to"]
    spouse = get_user(message.chat.id, spouse_id)
    me.update(
        married_to=None,
        marry_score=0,
        marry_msg_at=0,
        pet_name=None,
        hunger=100,
        bond=0,
        last_feed_ts=0.0,
        last_play_ts=0.0,
    )
    save_user(message.chat.id, message.from_user.id, me)
    if spouse:
        spouse.update(
            married_to=None,
            marry_score=0,
            marry_msg_at=0,
            pet_name=None,
            hunger=100,
            bond=0,
            last_feed_ts=0.0,
            last_play_ts=0.0,
        )
        save_user(message.chat.id, spouse_id, spouse)
    await message.answer(
        f"💔 {me['name']} и {spouse['name'] if spouse else 'партнёр'} развелись."
    ) 


@router.message(Command("namepet"))
async def cmd_namepet(message: Message, command: CommandObject):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p.get("married_to"):
        await message.answer(
            "Питомец доступен только женатым парам (/propose и /accept)."
        )
        return
    if not command.args:
        await message.answer("Использование: /namepet Имя")
        return
    p["pet_name"] = command.args.strip()
    p["hunger"] = 100
    p["bond"] = 0
    save_user(message.chat.id, message.from_user.id, p)
    await message.answer(
        f"🐾 Теперь у вас есть {p['pet_name']}! Корми его /feed и играй /play."
    ) 
    
@router.message(Command("pet"))
@router.callback_query(F.data == "btn_pet")
async def cmd_pet(event: Message | CallbackQuery):
    is_cb = isinstance(event, CallbackQuery)
    if is_cb:
        await event.answer()
        message = event.message
        user = event.from_user
    else:
        message = event
        user = event.from_user

    p = ensure_profile(message.chat.id, user.id, user.first_name or "Персонаж")
    if not p.get("married_to"):
        await message.answer("Питомец доступен только женатым парам.")
        return
    if not p.get("pet_name"):
        await message.answer("Питомца ещё нет. Заведи его: /namepet Имя")
        return
    progress = max(0, p["msg_count"] - p.get("marry_msg_at", 0)) + p.get("bond", 0) * 2
    hunger = p.get("hunger", 100)
    if hunger < 30:
        progress = progress // 2
    stage_idx = min(len(CHILD_STAGES) - 1, progress // 15)
    next_at = (stage_idx + 1) * 15
    stage_text = (
        "максимальная стадия"
        if stage_idx == len(CHILD_STAGES) - 1
        else f"{progress}/{next_at} до роста"
    )
    hunger_note = (
        "😋" if hunger >= 60 else ("😐" if hunger >= 30 else "😫 голоден! /feed")
    )

    await message.answer(
        f"{PET_STAGE_EMOJIS[stage_idx]} {p['pet_name']} — стадия: {CHILD_STAGES[stage_idx]}\n"
        f"{stage_text}\n"
        f"Сытость: {hunger}/100 {hunger_note}\n"
        f"Привязанность: {p.get('bond', 0)} (/play)"
    )
@router.message(Command("feed"))
async def cmd_feed(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p.get("married_to") or not p.get("pet_name"):
        await message.answer(
            "Питомец доступен только женатым парам, у которых он назван (/namepet)."
        )
        return
    now = time.time()
    remaining = FEED_COOLDOWN - (now - p.get("last_feed_ts", 0))
    if remaining > 0:
        await message.answer(
            f"{p['pet_name']} ещё сыт(а). Попробуй через {int(remaining // 60) + 1} мин."
        )
        return
    p["hunger"] = min(100, p.get("hunger", 100) + 25)
    p["last_feed_ts"] = now
    save_user(message.chat.id, message.from_user.id, p)
    await message.answer(
        f"🍽️ {p['pet_name']} покормлен(а)! Сытость: {p['hunger']}/100."
    )

    
@router.message(Command("play"))
async def cmd_play(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    if not p.get("married_to") or not p.get("pet_name"):
        await message.answer(
            "Питомец доступен только женатым парам, у которых он назван (/namepet)."
        )
        return
    now = time.time()
    remaining = PLAY_COOLDOWN - (now - p.get("last_play_ts", 0))
    if remaining > 0:
        await message.answer(
            f"{p['pet_name']} устал(а) играть. Попробуй через {int(remaining // 60) + 1} мин."
        )
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
    await message.answer(
        f"🎾 Вы поиграли с {p['pet_name']}! Привязанность: {p['bond']}.{found_text}"
    )


@router.message(Command("inventory"))
async def cmd_inventory(message: Message):
    p = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    await message.answer(
        f"🎒 Инвентарь {p['name']}:\n{inventory_text(p.get('items', {}))}"
    )

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
        await message.answer(
            f"У тебя нет «{item['label']}». Побеждай в /fight, чтобы получить предметы."
        )
        return

    if item["kind"] == "heal":
        healed = min(item["value"], p["max_hp"] - p["hp"])
        p["hp"] = min(p["max_hp"], p["hp"] + item["value"])
        p["items"][key] -= 1
        await message.answer(
            f"🧪 Выпито! +{healed} HP. Сейчас: {p['hp']}/{p['max_hp']}."
        )
    elif item["kind"] in ("buff_dmg", "buff_def", "buff_dodge"):
        p["active_buff"] = key
        p["items"][key] -= 1
        await message.answer(
            f"{item['label']} активирован — эффект сработает в следующем бою /fight."
        )
    elif item["kind"] == "pet_food":
        if not p.get("married_to") or not p.get("pet_name"):
            await message.answer("У тебя нет питомца — вкусняшка не пригодится.")
            return
        p["hunger"] = min(100, p.get("hunger", 100) + item["value"])
        p["items"][key] -= 1
        await message.answer(f"🍖 {p['pet_name']} доволен! Сытость: {p['hunger']}/100.")
    save_user(message.chat.id, message.from_user.id, p)

    
@router.message(Command("fight"))
async def cmd_fight(message: Message, bot: Bot):
    me = ensure_profile(message.chat.id, message.from_user.id, display_name(message))
    target = target_from_reply(message)
    if not target:
        await message.answer(
            "Ответь этой командой на сообщение того, с кем хочешь драться."
        )
        return
    foe_id, foe = target
    if foe_id == message.from_user.id:
        await message.answer(
            "С самим собой не подраться — выбери другого противника."
        )
        return
    if not me.get("soul") or not foe.get("soul"):
        await message.answer("У обоих должна быть выбрана душа (/soul).")
        return

    now = time.time()
    remaining = FIGHT_COOLDOWN - (now - me.get("last_fight_ts", 0))
    if remaining > 0:
        await message.answer(
            f"⏳ Отдохни перед следующей дуэлью: ещё {int(remaining)} сек."
        )
        return

    battle_id = new_battle_state(message.chat.id, message.from_user.id, me, foe_id, foe)
    sess = battles[battle_id]
    sent = await message.answer(
        battle_status_text(sess), reply_markup=battle_menu_keyboard(battle_id, False)
    )
    sess["chat_msg_id"] = sent.message_id


@router.callback_query(F.data.startswith("bt:"))
async def on_battle_action(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    battle_id = int(parts[1])
    action = parts[2]
    sess = battles.get(battle_id)
    if not sess:
        await callback.answer("Эта дуэль уже завершилась.", show_alert=True)
        return

    user_id = callback.from_user.id

    if action == "dodge":
        if not sess.get("pending") or sess["pending"]["defender_id"] != user_id:
            await callback.answer("Сейчас не твой момент уворачиваться!", show_alert=True)
            return
        await callback.answer("Уворачиваешься!")
        await resolve_attack(battle_id, dodged=True, bot=bot)
        return

    if user_id != sess["turn"]:
        await callback.answer("Сейчас не твой ход!", show_alert=True)
        return

    if sess.get("pending"):
        await callback.answer("Дождись исхода текущей атаки.", show_alert=True)
        return

    target = other(sess, user_id)

    if action == "menu":
        await callback.answer()
        await render_battle_menu(battle_id, bot)
        return

    if action == "fight":
        await callback.answer()
        attacker = {
            "soul": sess["soul"][user_id],
            "buff": sess["buff"][user_id],
            "hp": sess["hp"][user_id],
            "max_hp": sess["max_hp"][user_id],
        }
        dmg, crit, heal = compute_attack(attacker)
        ignore_dodge = sess["soul"][user_id] == "int"
        window = dodge_window(sess["soul"][target], sess["buff"][target])
        token = random.randint(1, 10_000_000)
        sess["pending"] = {
            "attacker_id": user_id,
            "defender_id": target,
            "dmg": dmg,
            "crit": crit,
            "heal": heal,
            "ignore_dodge": ignore_dodge,
            "token": token,
        }
        attack_text = (
            f"{sess['profiles'][user_id]['name']} идёт в атаку!\n\n"
            + battle_status_text(sess).split("➡️")[0].strip()
        )
        if ignore_dodge:
            await bot.edit_message_text(
                chat_id=sess["chat_id"],
                message_id=sess["chat_msg_id"],
                text=attack_text + "\n\n⚡ Удар искренний — его не увернуть.",
            )
            await resolve_attack(battle_id, dodged=False, bot=bot)
        else:
            await bot.edit_message_text(
                chat_id=sess["chat_id"],
                message_id=sess["chat_msg_id"],
                text=attack_text + f"\n\n🛡️ {sess['profiles'][target]['name']}, у тебя {window:.1f} сек, чтобы увернуться!",
                reply_markup=dodge_keyboard(battle_id),
            )
            asyncio.create_task(dodge_timeout(battle_id, bot, token, window))
        return

    if action == "act":
        if len(parts) == 3:
            await callback.answer()
            await bot.edit_message_text(
                chat_id=sess["chat_id"],
                message_id=sess["chat_msg_id"],
                text=battle_status_text(sess).split("➡️")[0].strip() + "\n\nВыбери действие:",
                reply_markup=act_keyboard(battle_id, sess["soul"][target]),
            )
            return
        idx = int(parts[3])
        options = ACT_OPTIONS.get(sess["soul"][target], [("Присмотреться", 1)])
        idx = max(0, min(idx, len(options) - 1))
        label, pts = options[idx]
        sess["soften"][target] = max(0, sess["soften"][target] + pts)
        note = f"{sess['profiles'][user_id]['name']}: «{label}»"
        if pts > 0:
            note += " — кажется, это подействовало."
        elif pts < 0:
            note += " — похоже, это не понравилось."
        sess["log"].append(note)
        await callback.answer()
        sess["turn"] = target
        sess["turns_done"] += 1
        if sess["turns_done"] >= MAX_TURNS:
            await finish_battle(battle_id, winner_id=None, bot=bot)
            return
        await render_battle_menu(battle_id, bot)
        return

    if action == "item":
        if len(parts) == 3:
            await callback.answer()
            owned = sess["profiles"][user_id].get("items", {})
            fresh = get_user(sess["chat_id"], user_id)
            if fresh:
                owned = fresh.get("items", {})
            await bot.edit_message_text(
                chat_id=sess["chat_id"],
                message_id=sess["chat_msg_id"],
                text=battle_status_text(sess).split("➡️")[0].strip() + "\n\nЧто использовать?",
                reply_markup=item_keyboard(battle_id, owned),
            )
            return
        key = parts[3]
        prof = get_user(sess["chat_id"], user_id) or sess["profiles"][user_id]
        have = prof.get("items", {}).get(key, 0)
        item = ITEMS.get(key)
        if not item or have <= 0 or item["kind"] != "heal":
            await callback.answer("Этого предмета больше нет.", show_alert=True)
            return
        prof["items"][key] -= 1
        healed = min(item["value"], sess["max_hp"][user_id] - sess["hp"][user_id])
        sess["hp"][user_id] = min(sess["max_hp"][user_id], sess["hp"][user_id] + item["value"])
        save_user(sess["chat_id"], user_id, prof)
        sess["log"].append(f"{sess['profiles'][user_id]['name']} использует {item['label']} (+{healed} HP).")
        await callback.answer(f"+{healed} HP")
        sess["turn"] = target
        sess["turns_done"] += 1
        if sess["turns_done"] >= MAX_TURNS:
            await finish_battle(battle_id, winner_id=None, bot=bot)
            return
        await render_battle_menu(battle_id, bot)
        return

    if action == "mercy":
        if sess["soften"][target] < MERCY_THRESHOLD:
            await callback.answer(
                "Вы ещё недостаточно понимаете друг друга — попробуй ACT.", show_alert=True
            )
            return
        await callback.answer()
        await finish_battle(battle_id, winner_id=None, bot=bot, mercy_by=user_id)
        return


@router.message(Command("top"))
async def cmd_top(message: Message):
    users = all_users(message.chat.id)
    ranked = sorted(users.values(), key=lambda u: u.get("wins", 0), reverse=True)
    ranked = [u for u in ranked if u.get("wins", 0) > 0][:10]
    if not ranked:
        await message.answer("Пока никто не побеждал в /fight.")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 Топ бойцов чата:"]
    for i, u in enumerate(ranked):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(
            f"{prefix} {u['name']} — {u.get('wins', 0)}W / {u.get('losses', 0)}L"
        )
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
        "💔 `/divorce` — развестись\n"
        "🐾 `/namepet Имя` — завести питомца\n"
        "🐾 `/pet` — карточка питомца\n"
        "🍽️ `/feed` — покормить питомца\n"
        "🎾 `/play` — поиграть с питомцем (шанс найти предмет)\n\n"
        "⚔️ `/fight` (ответом) — начать дуэль в стиле Undertale: "
        "FIGHT/ACT/ITEM/MERCY по очереди, уклонение по таймингу\n"
        "🎒 `/inventory` — твои предметы\n"
        "🧪 `/use <предмет>` — использовать предмет\n"
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
