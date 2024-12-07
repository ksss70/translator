import sys
import argparse
import re
from tomlkit import parse, items

# Регулярное выражение для проверки имен
# Разрешает имена, начинающиеся с буквы (заглавной или маленькой) или подчёркивания,
# а далее могут содержать буквы, цифры или подчёркивания
name_pattern = re.compile(r'^[_A-Za-z][_a-zA-Z0-9]*$')

# Множество для хранения констант
consts = set()


def process_array(arr, d, toml_doc):
    """
    Обрабатывает массив и возвращает строку в нужном формате.
    """
    result = "#( "
    items_list = [process_value(item, d, toml_doc) for item in arr]
    result += ", ".join(items_list)
    result += " )"
    return result


def process_dict(obj, d, toml_doc):
    """
    Обрабатывает словарь и возвращает строку в нужном формате.
    """
    result = "$[\n"
    indent = '\t' * d
    entries = []
    for key, value in obj.items():
        if not name_pattern.match(key):
            raise ValueError(f"Unsupported identifier name: '{key}'")
        processed_value = process_value(value, d + 1, toml_doc)
        entries.append(f"{indent}{key} = {processed_value}")
    result += ",\n".join(entries)

    # Добавляем закрывающую скобку с правильной табуляцией
    indent_end = '\t' * (d - 1)
    result += "\n" + indent_end + "]"

    return result


def process_comments(comments, d):
    """
    Обрабатывает комментарии и возвращает строку с комментариями.
    """
    result = ""
    indent = '\t' * d
    for comment in comments:
        # Конкатенируем строки для добавления комментариев
        result += indent + "\\ " + comment + "\n"
    return result


def process_value(value, d, toml_doc):
    """
    Обрабатывает значение и возвращает строку в нужном формате.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Замена констант внутри строк
        value = replace_constants_in_string(value, toml_doc)
        return f'"{value}"'
    elif isinstance(value, list):
        return process_array(value, d, toml_doc)
    elif isinstance(value, dict):
        return process_dict(value, d, toml_doc)
    else:
        raise ValueError(f"Unsupported type: {type(value)}")


def collect_constants(obj):
    """
    Собирает все константы из секций 'constants'.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() == "constants":
                if not isinstance(value, dict):
                    raise ValueError("Constants should be a dictionary.")
                for const_name, const_value in value.items():
                    if not name_pattern.match(const_name):
                        raise ValueError(f"Invalid constant name: '{const_name}'")
                    if const_name in consts:
                        raise ValueError(f"Duplicate constant: '{const_name}'")
                    consts.add(const_name)
            else:
                collect_constants(value)
    elif isinstance(obj, list):
        for item in obj:
            collect_constants(item)


def replace_constants_in_string(value, toml_doc):
    """
    Заменяет шаблоны .{CONSTANT}. на значения констант.
    """
    # Поиск шаблонов .{CONSTANT}.
    matches = re.findall(r'\.\{([_A-Za-z][_a-zA-Z0-9]*)\}.', value)
    for match in matches:
        if match not in consts:
            raise ValueError(f"Undefined constant: '{match}'")
        # Получаем значение константы
        const_value = get_constant_value(toml_doc, match)
        # Заменяем шаблон на значение константы
        value = value.replace(f".{{{match}}}.", str(const_value))
    return value


def replace_constants(obj, toml_doc):
    """
    Рекурсивно заменяет константы в объекте.
    """
    if isinstance(obj, str):
        return replace_constants_in_string(obj, toml_doc)
    elif isinstance(obj, dict):
        return {k: replace_constants(v, toml_doc) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_constants(item, toml_doc) for item in obj]
    else:
        return obj


def process_constants(obj):
    """
    Генерирует объявления констант.
    """
    declarations = []
    for const_name in consts:
        # Получаем значение константы из объекта
        const_value = get_constant_value(obj, const_name)
        processed_value = process_value(const_value, 1, obj)
        declarations.append(f"def {const_name} := {processed_value};")
    return "\n".join(declarations)


def get_constant_value(obj, const_name):
    """
    Рекурсивно ищет значение константы в объекте.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() == "constants" and const_name in value:
                return value[const_name]
            else:
                found = get_constant_value(value, const_name)
                if found is not None:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = get_constant_value(item, const_name)
            if found is not None:
                return found
    return None


def process_object(toml_doc, d):
    """
    Обрабатывает секции и возвращает строку в нужном формате.
    """
    result = ""
    indent = '\t' * d
    for section_name, section in toml_doc.items():
        if isinstance(section, items.Table):
            # Проверка корректности имени секции
            if not name_pattern.match(section_name):
                raise ValueError(f"Unsupported section name: '{section_name}'")
            result += f"{indent}{section_name} = $[\n"
            for key, value in section.items():
                if key.lower() == "constants":
                    continue  # Константы уже обработаны
                elif key.lower() == "comments":
                    continue  # Комментарии обрабатываются отдельно
                else:
                    if not name_pattern.match(key):
                        raise ValueError(f"Unsupported identifier name: '{key}'")
                    processed_value = process_value(value, d + 1, toml_doc)
                    # Конкатенация строк для корректного добавления табуляции
                    result += ('\t' * (d + 1)) + f"{key} = {processed_value}\n"
            result += f"{indent}]"
            # Добавление комментариев, связанных с секцией
            comments = section.trivia.comment
            if comments:
                for comment in comments.split('\n'):
                    # Конкатенация строк для добавления комментариев
                    result += "\n" + ('\t' * d) + "\\ " + comment.strip('# ').strip()
            result += "\n"
        elif isinstance(section, items.InlineTable):
            # Обработка встроенных таблиц при необходимости
            pass
        elif isinstance(section, items.Comment):
            # Обработка комментариев
            comment_text = section.value.lstrip('# ').rstrip()
            # Конкатенация строк для добавления комментария
            result += ('\t' * d) + "\\ " + comment_text + "\n"
    return result


def main(input_data, output_file):
    try:
        # Парсинг TOML с использованием tomlkit
        toml_doc = parse(input_data)

        # Сбор констант
        collect_constants(toml_doc)

        # Генерация объявлений констант
        const_declarations = process_constants(toml_doc)

        # Замена констант в данных
        data = replace_constants(toml_doc, toml_doc)

        # Генерация выходного текста
        output_lines = []

        if const_declarations:
            output_lines.append(const_declarations)
            output_lines.append("")  # Пустая строка для разделения

        # Обработка основных данных и комментариев
        config = process_object(toml_doc, 1)
        output_lines.append(config)

        result = "\n".join(output_lines)

        # Запись в файл
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print("Translation completed successfully.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TOML to Educational Config Language Translator")
    parser.add_argument('--output', '-o', required=True, help="Path to the output file")
    args = parser.parse_args()

    output_file = args.output

    # Чтение из стандартного ввода
    input_data = sys.stdin.read()

    main(input_data, output_file)
