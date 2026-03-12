import os
import json
from datetime import datetime
import time
import telebot
from telebot.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)




# ================= НАСТРОЙКИ =================
TOKEN ="8041557006:AAFllrymA5ijLwqgRgQnOqlH9KINHq21AU0"
bot = telebot.TeleBot(TOKEN)



FILE = "movies.json"

# ---------- ЖАНРЫ ----------
GENRES = ["Ужасы", "Комедия", "Фантастика", "Боевик", "Драма", "Детектив", "Триллер"]
GENRE_ALIASES = {
    "ужасы": "Ужасы",
    "комедия": "Комедия",
    "фантастика": "Фантастика",
    "боевик": "Боевик",
    "драма": "Драма",
    "детектив": "Детектив",
    "триллер": "Триллер"
}


# ---------- ЗАГРУЗКА ----------
def load_movies():
    if os.path.exists(FILE):
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {g: [] for g in GENRES}


def save_movies():
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=4)

movies = load_movies()


# ---------- СОСТОЯНИЯ ----------
user_state = {}
user_answers = {}
adding_movie = {}
show_state = {}
active_users = set()  # для рассылки


# ---------- КЛАВИАТУРЫ ----------
def kb_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Начать опрос")
    kb.add("Показать фильмы")
    kb.add("Добавить фильм")
    kb.add("Удалить фильм")
    return kb


def kb_start():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Старт")
    return kb


def kb_yes_no():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Да", "Нет")
    kb.add("Главное меню")
    return kb


def kb_genres():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Ужасы", "Комедия")
    kb.add("Фантастика", "Боевик")
    kb.add("Драма", "Детектив")
    kb.add("Триллер")
    kb.add("Главное меню")
    return kb


def kb_show_movies():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Все фильмы")
    kb.add("Фильмы по году")
    kb.add("Последние 20 фильмов")
    kb.add("Главное меню")
    return kb


# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(message):
    active_users.add(message.chat.id)
    bot.send_message(message.chat.id, "Главное меню 👇", reply_markup=kb_menu())


@bot.message_handler(func=lambda m: m.text == "Старт")
def restart(message):
    start(message)


@bot.message_handler(func=lambda m: m.text == "Главное меню")
def back_to_menu(message):
    uid = message.chat.id
    user_state.pop(uid, None)
    user_answers.pop(uid, None)
    adding_movie.pop(uid, None)
    show_state.pop(uid, None)
    bot.send_message(uid, "Главное меню 👇", reply_markup=kb_menu())


# ---------- ОПРОС ----------
questions = [
    ("Нравятся ли тебе ужасы?", "Ужасы"),
    ("Нравится ли тебе комедия?", "Комедия"),
    ("Нравится ли тебе фантастика?", "Фантастика"),
    ("Нравятся ли тебе боевики?", "Боевик"),
    ("Нравится ли тебе драма?", "Драма"),
    ("Нравятся ли тебе детективы?", "Детектив"),
    ("Нравятся ли тебе триллеры?", "Триллер")
]


@bot.message_handler(func=lambda m: m.text == "Начать опрос")
def start_quiz(message):
    uid = message.chat.id
    # Очистка состояния добавления фильма
    adding_movie.pop(uid, None)

    user_state[uid] = 0
    user_answers[uid] = []
    bot.send_message(uid, questions[0][0], reply_markup=kb_yes_no())


@bot.message_handler(func=lambda m: m.text in ["Да", "Нет"])
def answer(message):
    uid = message.chat.id
    if uid not in user_state:
        return
    index = user_state[uid]
    genre = questions[index][1]
    user_answers[uid].append((genre, message.text))
    user_state[uid] += 1

    if user_state[uid] >= len(questions):
        liked = [g for g, a in user_answers[uid] if a == "Да"]
        text = "🎬 Рекомендации:\n\n"
        for genre in liked:
            for f in movies.get(genre, []):
                text += (
                    f"🎬 {f['name']}\n"
                    f"🎭 {genre}\n"
                    f"📅 Год выхода: {f['year']}\n"
                    f"👤 Добавил: {f['added_by']}\n"
                    f"🕒 Дата и время добавления: {f['added_date']}\n"
                    f"💬 Комментарий: {f['comment']}\n\n"
                )
        if not liked:
            text = "Ты не выбрал жанры 😢"
        bot.send_message(uid, text, reply_markup=kb_start())
        user_state.pop(uid)
        user_answers.pop(uid)
        return

    bot.send_message(uid, questions[user_state[uid]][0], reply_markup=kb_yes_no())


# ---------- ДОБАВИТЬ ФИЛЬМ ----------
@bot.message_handler(func=lambda m: m.text == "Добавить фильм")
def add_movie(message):
    uid = message.chat.id
    # Очистка других состояний
    user_state.pop(uid, None)
    user_answers.pop(uid, None)
    show_state.pop(uid, None)

    adding_movie[uid] = {"step": "name"}
    bot.send_message(uid, "🎬 Введи название фильма:")


@bot.message_handler(func=lambda m: m.chat.id in adding_movie)
def add_movie_steps(message):
    uid = message.chat.id
    data = adding_movie[uid]

    if message.text == "Главное меню":
        back_to_menu(message)
        return

    if message.text == 'Показать фильмы':
        adding_movie.pop(uid, None)
        show_movies_menu(message)
        return

    if message.text == 'Удалить фильм':
        adding_movie.pop(uid, None)
        delete_movie(message)
        return

    if message.text == 'Начать опрос':
        adding_movie.pop(uid, None)
        start_quiz(message)
        return

    if message.text == 'Добавить фильм':
        add_movie(message)
        return

    if data["step"] == "name":
        data["name"] = message.text
        data["step"] = "genre"
        bot.send_message(uid, "🎭 Выбери жанр:", reply_markup=kb_genres())
        return

    if data["step"] == "genre":
        if message.text not in GENRES:
            return
        data["genre"] = message.text
        data["step"] = "year"
        bot.send_message(uid, "📅 Год выхода:")
        return

    if data["step"] == "year":
        if not message.text.isdigit():
            bot.send_message(uid, "❌ Пожалуйста, введите год числом (например: 2020)")
            return
        data["year"] = int(message.text)
        data["step"] = "added_by"
        bot.send_message(uid, "👤 Кто добавил фильм?")
        return

    if data["step"] == "added_by":
        data["added_by"] = message.text
        data["step"] = "comment"
        bot.send_message(uid, "💬 Комментарий:")
        return

    if data["step"] == "comment":
        movies[data["genre"]].append({
            "name": data["name"],
            "year": data["year"],
            "added_by": data["added_by"],
            "comment": message.text,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_movies()
        adding_movie.pop(uid)
        bot.send_message(uid, "✅ Фильм добавлен!", reply_markup=kb_start())


# ---------- ПОКАЗ ФИЛЬМОВ ----------
@bot.message_handler(func=lambda m: m.text == "Показать фильмы")
def show_movies_menu(message):
    uid = message.chat.id
    # Очистка состояния добавления фильма
    adding_movie.pop(uid, None)
    user_state.pop(uid, None)
    user_answers.pop(uid, None)

    bot.send_message(uid, "Выбери вариант:", reply_markup=kb_show_movies())


MOVIES_PER_PAGE = 10


@bot.message_handler(func=lambda m: m.text == "Все фильмы")
def show_all_movies(message):
    uid = message.chat.id
    show_state[uid] = {"page": 0, "mode": "all"}
    send_movies_page(uid)


def send_movies_page(uid, message_id=None):
    page = show_state[uid]["page"]

    # Собираем все фильмы
    all_films = []
    for genre, films in movies.items():
        for f in films:
            item = f.copy()
            item["genre"] = genre
            all_films.append(item)

    total = len(all_films)
    start = page * MOVIES_PER_PAGE
    end = start + MOVIES_PER_PAGE
    page_films = all_films[start:end]

    if not page_films:
        bot.send_message(uid, "Фильмы не найдены 😢", reply_markup=kb_start())
        show_state.pop(uid, None)
        return

    text = f"🎬 Все фильмы (страница {page + 1}/{(total + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE}):\n\n"
    for f in page_films:
        text += (
            f"🎬 {f['name']}\n"
            f"🎭 {f['genre']}\n"
            f"📅 Год выхода: {f['year']}\n"
            f"👤 Добавил: {f['added_by']}\n"
            f"🕒 Дата и время добавления: {f['added_date']}\n"
            f"💬 Комментарий: {f['comment']}\n\n"
        )

    text += f"\n📊 Показано {start + 1}-{min(end, total)} из {total}"

    # Inline клавиатура с кнопками навигации
    kb = InlineKeyboardMarkup()
    buttons = []

    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="prev_page"))

    buttons.append(InlineKeyboardButton(f"{page + 1}/{(total + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE}",
                                        callback_data="current_page"))

    if end < total:
        buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data="next_page"))

    kb.row(*buttons)
    kb.row(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))

    # Если message_id есть - редактируем, иначе отправляем новое
    if message_id:
        try:
            bot.edit_message_text(text, uid, message_id, reply_markup=kb)
        except:
            bot.send_message(uid, text, reply_markup=kb)
    else:
        msg = bot.send_message(uid, text, reply_markup=kb)
        show_state[uid]["message_id"] = msg.message_id


# Обработчик нажатий на inline-кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id

    if call.data == "next_page":
        if uid in show_state:
            show_state[uid]["page"] += 1
            send_movies_page(uid, call.message.message_id)
            bot.answer_callback_query(call.id)

    elif call.data == "prev_page":
        if uid in show_state:
            show_state[uid]["page"] = max(0, show_state[uid]["page"] - 1)
            send_movies_page(uid, call.message.message_id)
            bot.answer_callback_query(call.id)

    elif call.data == "current_page":
        # Просто подтверждаем, что это текущая страница
        bot.answer_callback_query(call.id, "Текущая страница")

    elif call.data == "main_menu":
        show_state.pop(uid, None)
        bot.delete_message(uid, call.message.message_id)
        bot.send_message(uid, "Главное меню 👇", reply_markup=kb_menu())
        bot.answer_callback_query(call.id)


# ---------- ФИЛЬМЫ ПО ГОДУ ----------
@bot.message_handler(func=lambda m: m.text == "Фильмы по году")
def show_movies_by_year(message):
    bot.send_message(message.chat.id, "Введите год для фильмов (например, 2020):")
    bot.register_next_step_handler(message, send_movies_by_year)


def send_movies_by_year(message):
    # Проверяем команды меню ПЕРЕД проверкой формата года
    if message.text == 'Начать опрос':
        start_quiz(message)
        return

    if message.text == 'Последние 20 фильмов':
        show_last_20(message)
        return

    if message.text == 'Фильм по году':
        send_movies_by_year(message)
        return

    if message.text == 'Все фильмы':
        show_all_movies(message)
        return

    if message.text == 'Удалить фильм':
        delete_movie(message)
        return

    if message.text == "Главное меню":
        back_to_menu(message)
        return

    if message.text == 'Показать фильмы':
        show_movies_menu(message)
        return

    if message.text == 'Добавить фильм':
        add_movie(message)
        return

    year_text = message.text

    if not year_text.isdigit():
        bot.send_message(message.chat.id, "Неверный формат года. Попробуйте снова.", reply_markup=kb_show_movies())
        return

    year = int(year_text)
    filtered = []

    for genre, films in movies.items():
        for f in films:
            if f["year"] == year:
                item = f.copy()
                item["genre"] = genre
                filtered.append(item)

    if not filtered:
        bot.send_message(message.chat.id, f"Фильмов за {year} не найдено 😢", reply_markup=kb_start())
        return

    text = f"🎬 Фильмы за {year}:\n\n"
    for f in filtered:
        text += (
            f"🎬 {f['name']}\n"
            f"🎭 {f['genre']}\n"
            f"👤 Добавил: {f['added_by']}\n"
            f"🕒 Дата и время добавления: {f['added_date']}\n"
            f"💬 Комментарий: {f['comment']}\n\n"
        )

    bot.send_message(message.chat.id, text, reply_markup=kb_start())


# ---------- ПОСЛЕДНИЕ 20 ФИЛЬМОВ ----------
@bot.message_handler(func=lambda m: m.text == "Последние 20 фильмов")
def show_last_20(message):


    all_movies = []
    for genre, films in movies.items():
        for f in films:
            item = f.copy()
            item["genre"] = genre
            if len(item["added_date"]) == 10:
                item["added_date"] += " 00:00:00"
            all_movies.append(item)

    all_movies.sort(
        key=lambda x: datetime.strptime(x["added_date"], "%Y-%m-%d %H:%M:%S"),
        reverse=True
    )

    last_20 = all_movies[:20]

    if not last_20:
        bot.send_message(message.chat.id, "Фильмы пока не добавлены 😢", reply_markup=kb_start())
        return

    text = "🕒 Последние 20 добавленных фильмов:\n\n"
    for f in last_20:
        text += (
            f"🎬 {f['name']}\n"
            f"🎭 {f['genre']}\n"
            f"📅 Год выхода: {f['year']}\n"
            f"👤 Добавил: {f['added_by']}\n"
            f"🕒 Дата и время добавления: {f['added_date']}\n"
            f"💬 Комментарий: {f['comment']}\n\n"
        )

    bot.send_message(message.chat.id, text, reply_markup=kb_start())


# ---------- УДАЛЕНИЕ ФИЛЬМА ----------
@bot.message_handler(func=lambda m: m.text == "Удалить фильм")
def delete_movie(message):
    uid = message.chat.id
    # Очистка состояния добавления фильма
    adding_movie.pop(uid, None)
    user_state.pop(uid, None)
    user_answers.pop(uid, None)

    bot.send_message(uid, "Введите название фильма:")
    bot.register_next_step_handler(message, ask_password)


def ask_password(message):
    film_name = message.text

    if message.text == 'Удалить фильм':
        delete_movie(message)
        return

    if message.text == "Главное меню":
        back_to_menu(message)
        return

    if message.text == 'Показать фильмы':
        show_movies_menu(message)
        return

    if message.text == 'Начать опрос':
        start_quiz(message)
        return

    if message.text == 'Добавить фильм':
        add_movie(message)
        return

    bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(message, confirm_delete, film_name)


def confirm_delete(message, film_name):

    if message.text == 'Удалить фильм':
        delete_movie(message)
        return

    if message.text == "Главное меню":
        back_to_menu(message)
        return

    if message.text == 'Показать фильмы':
        show_movies_menu(message)
        return

    if message.text == 'Начать опрос':
        start_quiz(message)
        return

    if message.text == 'Добавить фильм':
        add_movie(message)
        return

    if message.text != "films":
        bot.send_message(message.chat.id, "Неверный пароль ❌", reply_markup=kb_start())
        return

    for genre in movies:
        for f in movies[genre]:
            if f["name"].lower() == film_name.lower():
                movies[genre].remove(f)
                save_movies()
                bot.send_message(message.chat.id, "Фильм удалён ✅", reply_markup=kb_start())
                return

    bot.send_message(message.chat.id, "Фильм не найден 😢", reply_markup=kb_start())

print("Бот запущен...")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(5)
