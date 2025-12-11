import unittest
from proekt_onlycod_documentation import FinanceDB

class TestFinanceDB(unittest.TestCase):
    """
    Тесты для класса FinanceDB - проверяем работу с базой данных
    """

    def setUp(self):
        """
        Перед каждым тестом создаем новую базу в памяти при помощи memory:
        """
        self.db = FinanceDB(":memory:")

    # Тесты для set_balance

    def test_1_set_balance_normal(self):
        """
        Тест 1 для set_balance: Проверка, что метод работает с обычными положительными числами
        Это первый стандартный тест
        """
        user_id = 1001
        test_amount = 1500.50

        result = self.db.set_balance(user_id, test_amount)

        self.assertTrue(result, "False, если не получилось поставить баланс, что странно")

        saved_balance = self.db.get_balance(user_id)
        self.assertEqual(saved_balance, test_amount, f"Баланс должен быть {test_amount}, а получили {saved_balance}")

    def test_2_set_balance_zero(self):
        """
        Тест 2 для set_balance: Проверяем можно ли установить нулевой баланс
        Это первый граничный случай
        """
        user_id = 1002
        test_amount = 0.0

        result = self.db.set_balance(user_id, test_amount)

        self.assertTrue(result, "Ноль возможно написать")

        balance = self.db.get_balance(user_id)
        self.assertEqual(balance, 0.0, "Баланс должен быть 0.0")

    def test_3_set_balance_invalid_type(self):
        """
        Тест 3 для set_balance: Передача строки вместо числа
        Это второй граничный случай
        """
        user_id = 1004
        invalid_amount = "bebe"
        result = self.db.set_balance(user_id, invalid_amount)

        self.assertFalse(result, "Неверный тип данных")

        balance = self.db.get_balance(user_id)

        self.assertIsNone(balance,"При неверном типе данных запись не должна добавиться")

    def test_4_set_balance_update_existing(self):
        """
        Тест 4 для set_balance: Проверяем что метод заменяет старый баланс на новый
        Достаточно интересный первый тест на мой взгляд
        """
        user_id = 1004

        self.db.set_balance(user_id, 500.0)
        first_read = self.db.get_balance(user_id)

        self.db.set_balance(user_id, 1200.0)
        second_read = self.db.get_balance(user_id)

        self.assertEqual(first_read, 500.0, "Первый баланс должен быть 500")
        self.assertEqual(second_read, 1200.0, "Второй баланс должен быть 1200")

        # Проверяем что в базе только одна запись для этого пользователя
        self.db.cursor.execute("SELECT COUNT(*) FROM users WHERE user_id=?", (user_id,))
        count = self.db.cursor.fetchone()[0]
        self.assertEqual(count, 1, "Должна быть только одна запись на одного пользователя, тк мы сделали замену")

    # Тесты для add_expense

    def test_1_add_expense_normal(self):
        """
        Тест 1 для add_expense: Проверяем стандартное добавление расхода при достаточном балансе
        Это первый обычный тест
        """
        user_id = 2001

        self.db.set_balance(user_id, 1000.0)

        result = self.db.add_expense(user_id, "Еда", 300.0)

        self.assertTrue(result, "Должен вернуть True при успешной трате")

        new_balance = self.db.get_balance(user_id)
        self.assertEqual(new_balance, 700.0,f"Должно остаться 700, а осталось {new_balance}")

        self.db.cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?", (user_id,))
        count = self.db.cursor.fetchone()[0]
        self.assertEqual(count, 1, "Должна быть одна запись о расходе")

    def test_2_add_expense_insufficient_funds(self):
        """
        Тест 2 для add_expense: Проверка, что нельзя потратить больше, чем есть на балансе
        Это первый граничный случай
        """
        user_id = 2002

        self.db.set_balance(user_id, 100.0)

        result = self.db.add_expense(user_id, "Жилье", 50000000.0)

        self.assertFalse(result, "Должен вернуть False при недостатке средств")

        balance = self.db.get_balance(user_id)
        self.assertEqual(balance, 100.0, "Баланс не должен измениться")

        self.db.cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?", (user_id,))
        count = self.db.cursor.fetchone()[0]
        self.assertEqual(count, 0, "Не должно быть записей о расходах")

    def test_3_add_expense_spend_all_money(self):
        """
        Тест 3 для add_expense: Проверяем можно ли потратить всё в ноль
        Это второй граничный случай
        """
        user_id = 2003
        exact_amount = 753.21

        self.db.set_balance(user_id, exact_amount)

        result = self.db.add_expense(user_id, "Еда", exact_amount)

        self.assertTrue(result, "Должен разрешить потратить все деньги")

        balance = self.db.get_balance(user_id)
        self.assertEqual(balance, 0.0, f"Баланс должен быть 0, а не {balance}")

    def test_4_add_expense_multiple_in_same_category(self):
        """
        Тест 4 для add_expense: Проверяем работу метода при нескольких вызовах подряд(несколько трат подряд)
        Достаточно интересный первый тест на мой взгляд
        """
        user_id = 2004

        self.db.set_balance(user_id, 2000.0)

        amounts = [100.0, 200.0, 150.0, 50.0]
        for amount in amounts:
            result = self.db.add_expense(user_id, "Продукты", amount)
            self.assertTrue(result, f"Не удалось добавить расход {amount}")

        total_spent = sum(amounts)

        final_balance = self.db.get_balance(user_id)
        expected_balance = 2000.0 - total_spent
        self.assertEqual(final_balance, expected_balance, f"Должно быть {expected_balance}, а есть {final_balance}")

        self.db.cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?", (user_id,))
        count = self.db.cursor.fetchone()[0]
        self.assertEqual(count, len(amounts),f"Должно быть {len(amounts)} записей, а есть {count}")

    # Тесты для get_stats

    def test_1_get_stats_normal(self):
        """
        Тест 1 для get_stats: Проверяем подсчет статистики когда есть расходы в разных категориях
        Это первый обычный тест
        """
        user_id = 3001

        self.db.set_balance(user_id, 5000.0)

        test_data = [
            ("Еда", 500.0),
            ("Еда", 300.0),
            ("Транспорт", 200.0),
            ("Развлечения", 1000.0),
            ("Транспорт", 300.0)
        ]

        for category, amount in test_data:
            self.db.add_expense(user_id, category, amount)

        stats = self.db.get_stats(user_id)

        self.assertEqual(stats["Еда"], 800.0, "В категории еда должно быть 800.0")
        self.assertEqual(stats["Транспорт"], 500.0, "В категории транспорт должно быть 500.0")
        self.assertEqual(stats["Развлечения"], 1000.0, "В категории развлечения должно быть 1000.0")

    def test_2_get_stats_empty(self):
        """
        Тест 2 для get_stats: Проверяем, что возвращает метод когда у пользователя нет расходов
        Это первый граничный случай
        """
        user_id = 3002

        self.db.set_balance(user_id, 1000.0)

        stats = self.db.get_stats(user_id)

        self.assertEqual(stats, {}, "Должен быть пустой словарь")

    def test_3_get_stats_one_expense_only(self):
        """
        Тест 3 для get_stats: Проверяем статистику когда есть всего одна запись о расходе
        Это второй граничный случай
        """
        user_id = 3003

        self.db.set_balance(user_id, 800.0)

        self.db.add_expense(user_id, "Развлечения", 250.0)

        stats = self.db.get_stats(user_id)

        self.assertEqual(len(stats), 1, "Должна быть одна категория")
        self.assertEqual(stats["Развлечения"], 250.0, "Развлечения должны быть 250.0")

    def test_4_get_stats_with_long_category_names(self):
        """
        Тест 4 для get_stats: Проверяем работу с категориями у которых длинные и сложные названия
        Достаточно интересный первый тест на мой взгляд
        """
        user_id = 3004

        self.db.set_balance(user_id, 3000.0)

        categories = [
            "Продукты питания и алкоголь",
            "Общественный транспорт и такси",
            "Развлечения, кино и отдых",
            "Коммунальные услуги и квартплата"
        ]

        for i, category in enumerate(categories):
            amount = 100.0 * (i + 1)
            self.db.add_expense(user_id, category, amount)

        stats = self.db.get_stats(user_id)

        for category in categories:
            self.assertIn(category, stats, f"Категория '{category}' должна быть в статистике")

        self.assertEqual(stats["Продукты питания и алкоголь"], 100.0)
        self.assertEqual(stats["Общественный транспорт и такси"], 200.0)
        self.assertEqual(stats["Развлечения, кино и отдых"], 300.0)
        self.assertEqual(stats["Коммунальные услуги и квартплата"], 400.0)

if __name__ == "__main__":
    unittest.main()