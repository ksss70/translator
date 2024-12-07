import unittest
import subprocess
import tempfile
import os
import shutil

class TestMain(unittest.TestCase):
    def setUp(self):
        # Создаём временную директорию для тестов
        self.test_dir = tempfile.mkdtemp()
        # Предполагается, что main.py находится в той же директории, что и test_main.py
        self.main_script = os.path.join(os.getcwd(), 'main.py')  # Путь к вашему скрипту main.py

    def tearDown(self):
        # Удаляем временную директорию после теста
        shutil.rmtree(self.test_dir)

    def remove_comments(self, text):
        """
        Удаляет строки, начинающиеся с '\' (комментарии).
        """
        return '\n'.join(line for line in text.splitlines() if not line.strip().startswith('\\'))

    def run_main(self, input_toml, expected_output_conf):
        """
        Запускает скрипт main.py с заданным входным TOML и проверяет выходной конфигурационный файл.
        """
        # Создаём временные файлы для входных и выходных данных
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, dir=self.test_dir, suffix='.toml') as input_file:
            input_file.write(input_toml)
            input_file_path = input_file.name

        output_file_path = os.path.join(self.test_dir, 'output.conf')

        try:
            # Запускаем скрипт main.py
            with open(input_file_path, 'r') as infile:
                result = subprocess.run(['python', self.main_script, '--output', output_file_path],
                                        stdin=infile,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        check=True)
        except subprocess.CalledProcessError as e:
            self.fail(f"Script failed with error: {e.stderr.decode()}")

        # Читаем выходной файл
        with open(output_file_path, 'r') as outfile:
            output_conf = outfile.read()

        # Удаляем комментарии из output_conf
        output_conf_no_comments = self.remove_comments(output_conf)

        # Удаляем комментарии из expected_output_conf (хотя expected_output_conf не содержит комментариев)
        expected_output_conf_no_comments = self.remove_comments(expected_output_conf)

        # Сравниваем с ожидаемым результатом без комментариев
        self.assertEqual(output_conf_no_comments.strip(), expected_output_conf_no_comments.strip())

    def test_simple_section_with_constants(self):
        input_toml = """
# Это основной сервер
[server]
host = "localhost"  # Адрес хоста
port = 8080
constants = { MAX_CONNECTIONS = 100, TIMEOUT = 30 }
"""
        expected_output_conf = """
def MAX_CONNECTIONS := 100;
def TIMEOUT := 30;

	server = $[
		host = "localhost"
		port = 8080
	]
"""
        self.run_main(input_toml, expected_output_conf)

    def test_multiple_sections_with_nested_tables(self):
        input_toml = """
# Настройки веб-сервера
[server]
host = "localhost"
port = 8080
constants = { MAX_CONNECTIONS = 100, TIMEOUT = 30 }

# Настройки базы данных
[database]
type = "postgresql"
credentials = { user = "admin", password = "secret" }
ports = [5432, 5433, 5434]
constants = { DEFAULT_PORT = 5432 }
"""
        expected_output_conf = """
def MAX_CONNECTIONS := 100;
def TIMEOUT := 30;
def DEFAULT_PORT := 5432;

	server = $[
		host = "localhost"
		port = 8080
	]

	database = $[
		type = "postgresql"
		credentials = $[
			user = "admin"
			password = "secret"
		]
		ports = #( 5432, 5433, 5434 )
	]
"""
        self.run_main(input_toml, expected_output_conf)

    def test_comments_in_sections_and_keys(self):
        input_toml = """
# Главная секция
[MainSection]
key1 = "value1"  # Комментарий к key1
key2 = 42  # Комментарий к key2
constants = { CONST1 = 100, CONST2 = 200 }
"""
        expected_output_conf = """
def CONST1 := 100;
def CONST2 := 200;

	MainSection = $[
		key1 = "value1"
		key2 = 42
	]
"""
        self.run_main(input_toml, expected_output_conf)

    def test_arrays_and_inline_tables(self):
        input_toml = """
# Настройки приложения
[app]
name = "MyApp"
version = "1.0.0"
constants = { VERSION_MAJOR = 1, VERSION_MINOR = 0, VERSION_PATCH = 0 }

[app.logging]
level = "INFO"
file = "/var/log/myapp.log"

[app.database]
type = "sqlite"
settings = { path = "/data/app.db", timeout = 30 }
"""
        expected_output_conf = """
def VERSION_MAJOR := 1;
def VERSION_MINOR := 0;
def VERSION_PATCH := 0;

	app = $[
		name = "MyApp"
		version = "1.0.0"
	]

	app.logging = $[
		level = "INFO"
		file = "/var/log/myapp.log"
	]

	app.database = $[
		type = "sqlite"
		settings = $[
			path = "/data/app.db"
			timeout = 30
		]
	]
"""
        self.run_main(input_toml, expected_output_conf)

    def test_invalid_section_name(self):
        input_toml = """
# Некорректная секция
[invalid-section]
key = "value"
constants = { CONST1 = 10 }
"""
        # Ожидаем, что скрипт завершится с ошибкой
        # Создаём временные файлы для входных и выходных данных
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, dir=self.test_dir, suffix='.toml') as input_file:
            input_file.write(input_toml)
            input_file_path = input_file.name

        output_file_path = os.path.join(self.test_dir, 'output.conf')

        # Запускаем скрипт и ожидаем ошибку
        with self.assertRaises(subprocess.CalledProcessError) as context:
            with open(input_file_path, 'r') as infile:
                subprocess.run(['python', self.main_script, '--output', output_file_path],
                               stdin=infile,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               check=True)

        # Проверяем, что ошибка содержит ожидаемое сообщение
        self.assertIn("Unsupported section name: 'invalid-section'", context.exception.stderr.decode())

    def test_duplicate_constants(self):
        input_toml = """
# Секция с дублирующими константами
[section]
constants = { CONST1 = 10, CONST1 = 20 }
"""
        # Ожидаем, что скрипт завершится с ошибкой
        # Создаём временные файлы для входных и выходных данных
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, dir=self.test_dir, suffix='.toml') as input_file:
            input_file.write(input_toml)
            input_file_path = input_file.name

        output_file_path = os.path.join(self.test_dir, 'output.conf')

        # Запускаем скрипт и ожидаем ошибку
        with self.assertRaises(subprocess.CalledProcessError) as context:
            with open(input_file_path, 'r') as infile:
                subprocess.run(['python', self.main_script, '--output', output_file_path],
                               stdin=infile,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               check=True)

        # Проверяем, что ошибка содержит ожидаемое сообщение
        self.assertIn("Duplicate constant: 'CONST1'", context.exception.stderr.decode())

if __name__ == '__main__':
    unittest.main()
