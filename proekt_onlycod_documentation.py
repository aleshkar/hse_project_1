import sqlite3
import logging
from datetime import datetime
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
"""Логгер для записи событий, ошибок и диагностики работы бота Регистрирует
системные события в заданном формате для мониторинга и отладки.

:type: logging.Logger
"""

bot = telebot.TeleBot("7974227359:AAHRj6bwFtOS1-UlxAQOpLMWH9CeFjtUjg4")

"""
Основной экземпляр телеграм-бота, инициализированный с уникальным токеном API.
Отвечает за взаимодействие с Telegram API, прием и отправку сообщений,
управление всеми хендлерами и обработку событий от пользователей.

:param bot: Объект класса TeleBot
:type bot: telebot.TeleBot
"""

user_temp = {}

"""
Глобальный словарь для хранения временных данных пользователей
во время использования, Используется как прослойка для многошаговых
операций, типо добавления расходов, является переменной с типом dict
"""


class FinanceDB:
    """Класс для управления базой данных финансового Telegram-бота Обеспечивает
    все операции с SQLite базой данных: создание таблиц, управление балансом
    пользователей, работу с расходами и статистикой.

    :ivar conn: Активное соединение с базой данных
    :vartype conn: sqlite3.Connection

    :ivar cursor: Курсор для выполнения SQL-запросов
    :vartype cursor: sqlite3.Cursor

    Основные методы:
    - create_tables(): Создает структуру базы данных
    - set_balance(): Устанавливает/обновляет баланс пользователя
    - get_balance(): Получает текущий баланс пользователя
    - add_expense(): Добавляет расход с проверкой средств
    - get_stats(): Возвращает статистику по категориям
    - get_history(): Возвращает историю расходов
    - clear_data(): Полностью удаляет данные пользователя
    """

    def __init__(self, db_name="finance.db"):
        """
        Инициализирует подключение к базе данных и
        создает таблицы при необходимости

        :param db_name: Имя файла базы данных
        :type db_name: str

        :raises sqlite3.Error: Если не удалось подключиться к базе данных
        """
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Создает необходимые таблицы в базе данных SQLite.

        Метод выполняет создание двух таблиц:
        1. Таблица 'users' для хранения информации о пользователях и их балансе
        2. Таблица 'expenses' для хранения записей о расходах пользователей

        :raises sqlite3.Error: Если возникает ошибка при работе с базой данных
        :return: None
        :rtype: None
        """
        try:
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0)"""
            )
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                amount REAL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            raise e

    def set_balance(self, user_id, amount):
        """Устанавливает или обновляет баланс пользователя при вводе
        :param user_id: Идентификатор пользователя
        :type user_id: int
        :param amount: Баланс пользователя.
        :type amount: float
        :return: True - при успешном выполнении, False в ином случае
        :rtype: bool
        :raises: Возвращает False неявно
        """
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO users VALUES (?, ?)",
                (user_id, float(amount))
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка установки баланса: {e}")
            return False

    def get_balance(self, user_id):
        """Получает текущий баланс пользователя.

        :param user_id: Идентификатор пользователя
        :type user_id: int
        :return: Вовзаращет баланс при запросе пользователя или None
            если пользователь не найден в базе данных
        :rtype: float или None
        :raises: Неявно обрабатывает исключения, возвращая None
        """
        try:
            self.cursor.execute(
                "SELECT balance FROM users WHERE user_id=?", (user_id,)
            )
            result = self.cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return None

    def add_expense(self, user_id, category, amount):
        """Добавляет трату в конкретную категорию.

        :param user_id: Идентификатор пользователя
        :type user_id: int
        :param category: Категория трат
        :type category: str
        :param amount: Сумма траты
        :type amount: float
        :return: Возвращает False если текущий баланс меньше суммы
            траты, либо если пользователя нет, а ещё возвращает True в
            других случаях
        :raises: Неявно обрабатывает исключения базы данных, возвращая
            False
        """
        try:
            balance = self.get_balance(user_id)
            if balance is None or balance < amount:
                return False

            self.cursor.execute(
                """INSERT INTO expenses (user_id, category, amount)
                                VALUES (?, ?, ?)""",
                (user_id, category, amount),
            )
            self.cursor.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id=?",
                (amount, user_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления расхода: {e}")
            return False

    def get_stats(self, user_id):
        """Получает статистику расходов пользователя по каким-либо категориям.

        :param user_id: Идентификатор пользователя
        :type user_id: int
        :return: Возвращает словарь в которых ключи - категории расходов,
        а значения - общая сумма по категориям
        :rtype: dict[str, float]
        :raises: Неявно обрабатывает исключения базы данных,
        возвращая пустой словарь
        """
        try:
            self.cursor.execute(
                """SELECT category, SUM(amount) FROM expenses
                                WHERE user_id=? GROUP BY category""",
                (user_id,),
            )
            return dict(self.cursor.fetchall())
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}

    def get_history(self, user_id, limit=5):
        """Получает историю расходов.

        :param user_id: Идентификатор пользователя
        :type user_id: int
        :param limit: Сколько последних записей вернуть сделали 5
        :type limit: int
        :return: Список последних расходов
        :rtype: list[tuple]
        :raises: Неявно обрабатывает исключения базы данных, возвращая
            пустой массив
        """
        try:
            self.cursor.execute(
                """SELECT category, amount, date FROM expenses
                                WHERE user_id=? ORDER BY date DESC LIMIT ?""",
                (user_id, limit),
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            return []

    def clear_data(self, user_id):
        """Полностью удаляет все данные из базы данных.

        :param user_id: Идентификатор пользователя
        :type user_id: int
        :return: True если удаление успешно, False если выодит ошибка
        :rtype: bool
        :raises: Неявно обрабатывает исключения, возвращая False
        """
        try:
            self.cursor.execute(
                "DELETE FROM expenses WHERE user_id=?", (user_id,)
            )
            self.cursor.execute(
                "DELETE FROM users WHERE user_id=?", (user_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки данных: {e}")
            return False


db = FinanceDB()
"""
Экземпляр подключения к базе данных для управления финансовыми операциями
Основной интерфейс для работы с хранением данных пользователей
:type: class
"""


def main_menu():
    """Создает и возвращает основное меню бота для управления финансами.

    :return: Объект клавиатуры ReplyKeyboardMarkup с основными командами
        бота
    :rtype: ReplyKeyboardMarkup
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ Добавить расход", "📊 Статистика")
    markup.add("📋 История", "💰 Баланс")
    markup.add("🗑️ Очистить все", "ℹ️ Помощь")
    return markup


@bot.message_handler(commands=["start"])
def start_command(message):
    """Обработчик команды старт.

    :param message: Сообщение от пользователя
    :type message: telebot.types.message
    :return: None
    """
    user_id = message.from_user.id
    balance = db.get_balance(user_id)

    if balance is None:
        msg = bot.send_message(message.chat.id, "💰 Введите начальный баланс:")
        bot.register_next_step_handler(msg, process_balance)
    else:
        bot.send_message(
            message.chat.id,
            f"💰 Ваш баланс: {balance:.2f}",
            reply_markup=main_menu(),
        )


def process_balance(message):
    """Обрабатывает ввод начального баланса для нового пользователя.

    :param message: Сообщение с введённым балансом от пользователя
    :type message: telebot.types.Message
    :return: None
    Связанные функции:
        - start_command(): Инициирует процесс ввода баланса
        - db.set_balance(): Сохраняет баланс в базе данных
        - main_menu(): Возвращает главное меню бота
    """
    try:
        user_id = message.from_user.id
        amount = float(message.text)

        if amount <= 0:
            raise ValueError("Баланс должен быть больше 0!")

        if db.set_balance(user_id, amount):
            bot.send_message(
                message.chat.id,
                f"✅ Баланс {amount:.2f} установлен!",
                reply_markup=main_menu(),
            )
        else:
            bot.send_message(message.chat.id, "❌ Ошибка!")
    except ValueError as e:
        bot.send_message(message.chat.id, f"❌ {e}")
        bot.register_next_step_handler(message, process_balance)
    except Exception as e:
        logger.error(f"Ошибка в process_balance: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка!")
        bot.register_next_step_handler(message, process_balance)


@bot.message_handler(func=lambda msg: msg.text == "➕ Добавить расход")
def add_expense_start(message):
    """Начинает процесс добавления нового расхода.

    :param message: Сообщение от пользователя
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    """
    user_id = message.from_user.id
    if db.get_balance(user_id) is None:
        bot.send_message(message.chat.id, "Сначала установите баланс!")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🍔 Еда", "🚗 Транспорт")
    markup.add("🎬 Развлечения", "👕 Одежда")
    markup.add("🏠 Жилье", "📱 Связь")
    markup.add("⬅️ Назад")

    user_temp[user_id] = {"step": "category"}
    bot.send_message(
        message.chat.id, "📁 Выберите категорию:", reply_markup=markup
    )


@bot.message_handler(
    func=lambda msg: msg.text
    in [
        "🍔 Еда",
        "🚗 Транспорт",
        "🎬 Развлечения",
        "👕 Одежда",
        "🏠 Жилье",
        "📱 Связь",
    ]
)
def process_category(message):
    """Обрабатывает выбор категории расхода и переходит к вводу суммы.

    Этот хендлер сохраняет выбранную пользователем категорию расходов
    и инициирует следующий шаг - ввод суммы расхода.

    :param message: Сообщение с выбранной категорией
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    """
    user_id = message.from_user.id
    category = message.text[2:]

    if user_id not in user_temp:
        user_temp[user_id] = {}
    user_temp[user_id]["category"] = category
    user_temp[user_id]["step"] = "amount"
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "💵 Введите сумму:", reply_markup=markup)
    bot.register_next_step_handler(message, process_amount)


def process_amount(message):
    """Обрабатывает ввод суммы расхода и сохраняет запись в базу данных.

    :param message: Сообщение с введённой суммой расхода
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    :raises ValueError: Если message.text не может быть преобразован в
        float или amount <= 0
    :raises sqlite3.Error: При ошибках SQLite в методах db.add_expense()
        или db.get_balance()
    :raises Exception: При любых других ошибках
    """
    try:
        user_id = message.from_user.id

        if user_id not in user_temp or "category" not in user_temp[user_id]:
            bot.send_message(
                message.chat.id,
                "❌ Ошибка! Начните заново.",
                reply_markup=main_menu(),
            )
            return

        amount = float(message.text)

        if amount <= 0:
            raise ValueError("Сумма должна быть больше 0!")

        category = user_temp[user_id]["category"]

        if db.add_expense(user_id, category, amount):
            balance = db.get_balance(user_id)
            bot.send_message(
                message.chat.id,
                f"✅ Добавлено!\n📁 {category}: {amount:.2f}\n"
                f"💰 Остаток: {balance:.2f}",
                reply_markup=main_menu(),
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Недостаточно средств!",
                reply_markup=main_menu(),
            )

        user_temp.pop(user_id, None)

    except ValueError:
        bot.send_message(
            message.chat.id, "❌ Введите число!", reply_markup=main_menu()
        )
        user_temp.pop(user_id, None)
    except Exception as e:
        logger.error(f"Ошибка в process_amount: {e}")
        bot.send_message(
            message.chat.id, "❌ Ошибка!", reply_markup=main_menu()
        )
        user_temp.pop(user_id, None)


@bot.message_handler(func=lambda msg: msg.text == "📊 Статистика")
def show_stats(message):
    """Отображает статистику расходов пользователя по категориям.

    Показывает упорядоченные данные о всех расходах пользователя,
    сгруппированные по категориям с суммой трат по каждой категории.

    :param message: Сообщение от пользователя
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    :raises: Неявно обрабатывает исключения через db.get_stats(),
    возвращающую пустой словарь при ошибках
    Связанные функции:
        - db.get_stats(): SQL-запрос: SELECT category... и тд
        - main_menu(): Возврат к главному меню после показа статистики
    """
    user_id = message.from_user.id
    stats = db.get_stats(user_id)

    if not stats:
        bot.send_message(
            message.chat.id, "📊 Нет расходов", reply_markup=main_menu()
        )
        return
    text = "📊 Статистика:\n"
    for category, total in stats.items():
        text += f"{category}: {total:.2f}\n"

    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(func=lambda msg: msg.text == "📋 История")
def show_history(message):
    """Отображает историю последних расходов пользователя Показывает последние
    5 записей о расходах пользователя в обратном хронологическом порядке с
    датой.

    :param message: Сообщение от пользователя
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    :raises: Неявно обрабатывает исключения через db.get_history(),
        возвращающую пустой список при ошибках
    :raises ValueError: Если дата из БД имеет некорректный формат
    """
    user_id = message.from_user.id
    history = db.get_history(user_id)

    if not history:
        bot.send_message(
            message.chat.id, "📋 Нет расходов", reply_markup=main_menu()
        )
        return
    text = "📋 История:\n"
    for category, amount, date in history:
        date_str = datetime.strptime(date[:10], "%Y-%m-%d").strftime("%d.%m")
        text += f"{date_str}: {category} - {amount:.2f}\n"

    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(func=lambda msg: msg.text == "💰 Баланс")
def show_balance(message):
    """Отображает текущий баланс пользователя Показывает актуальный остаток
    средств пользователя, полученный из базы данных Если баланс не установлен,
    предлагает установить его через команду /start.

    :param message: Сообщение от пользователя
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    :raises: Неявно обрабатывает исключения через db.get_balance(),
        возвращающую None при ошибках
    """
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    if balance is None:
        bot.send_message(message.chat.id, "Сначала установите баланс!")
    else:
        bot.send_message(
            message.chat.id,
            f"💰 Баланс: {balance:.2f}",
            reply_markup=main_menu(),
        )


@bot.message_handler(func=lambda msg: msg.text == "🗑️ Очистить все")
def clear_start(message):
    """Инициирует процесс полного удаления всех данных пользователя Показывает
    подтверждающее меню с двумя вариантами ответа перед выполнением опасной
    операции полного удаления данных пользователя из базы данных.

    :param message: Сообщение от пользователя
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✅ Да, очистить", "❌ Нет, отмена")

    bot.send_message(
        message.chat.id, "⚠️ Удалить ВСЕ данные?", reply_markup=markup
    )


@bot.message_handler(func=lambda msg: msg.text == "✅ Да, очистить")
def clear_confirm(message):
    """Выполняет полное удаление всех данных пользователя после подтверждения
    Финальный шаг в цепочке удаления данных. Вызывает db.clear_data(), которая
    полностью удаляет пользователя из системы, включая баланс и всю историю
    расходов.

    :param message: Сообщение подтверждения от пользователя
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    :raises: Неявно обрабатывает исключения через db.clear_data(),
        возвращающую False при ошибках
    """
    user_id = message.from_user.id

    if db.clear_data(user_id):
        bot.send_message(
            message.chat.id, "✅ Данные удалены!", reply_markup=main_menu()
        )
    else:
        bot.send_message(
            message.chat.id, "❌ Ошибка!", reply_markup=main_menu()
        )


@bot.message_handler(
    func=lambda msg: msg.text in ["❌ Нет, отмена", "⬅️ Назад", "ℹ️ Помощь"]
)
def cancel_or_help(message):
    """
    Обрабатывает команды "Помощь" и "Назад", обеспечивая навигацию по боту
    Универсальный хендлер для двух распространённых действий:
    1. Показ справочной информации о функциях бота
    2. Возврат в главное меню из любого места

    :param message: Сообщение от пользователя
    :type message: telebot.types.Message
    :return: None
    :rtype: None
    """
    if message.text == "ℹ️ Помощь":
        text = """ℹ️ Помощь:
➕ Добавить расход - добавить новый расход
📊 Статистика - статистика по категориям
📋 История - последние расходы
💰 Баланс - текущий баланс
🗑️ Очистить все - удалить все данные

💡 Сначала установите баланс командой /start"""
        bot.send_message(message.chat.id, text, reply_markup=main_menu())
    else:
        bot.send_message(
            message.chat.id, "⬅️ Возврат в меню", reply_markup=main_menu()
        )


@bot.message_handler(func=lambda msg: True)
def unknown_message(message):
    """
    Обрабатывает неизвестные или некорректные сообщения от пользователя.
    Функция, которая перехватывает все сообщения, не обработанные
    другими хендлерами, предоставляет пользователю инструкцию по корректному
    использованию бота и возвращает его в главное меню.

    :param message: Любое сообщение от пользователя,
        не соответствующее заданным внутри моего бота
    :type message: telebot.types.Message
    :return: None
    :rtype: None

    Связанные функции:
    - main_menu(): Главное меню, куда возвращается пользователь
    - Все другие хендлеры: обрабатывают известные функции перед выводом
    """
    bot.send_message(
        message.chat.id,
        "Используйте кнопки меню или /start",
        reply_markup=main_menu(),
    )


if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
