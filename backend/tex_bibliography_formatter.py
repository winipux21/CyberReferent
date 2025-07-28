# backend/tex_bibliography_formatter.py

import openai
import logging
import re
from dotenv import load_dotenv
import os
# Загрузка переменных окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY не найден в переменных окружения.")

MODEL = "deepseek-chat"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Универсальный промпт для fallback (на случай непредвиденных ошибок)
GENERIC_PROMPT = """Ты — эксперт по библиографии и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
journal: ...
volume: ...
number: ...
year: ...
pages: ...
doi: ...
url: ...
publisher: ...
address: ...
month: ...
day: ...
note: ...
Если какого-то поля нет, пропусти его.
Запись: "{reference}" """

def format_reference_to_bibtex_with_ai(reference: str, target_format: str, subformat: str) -> str:
    """
    Формирует библиографическую запись в BibTeX-формате с помощью нейросети.
    Извлекает любые доступные данные и строит запись динамически, даже если данные неполные.
    """

    # Ожидаемые структуры для подсказок
    expected_structures = {
        "APA": {
            "Журнальная статья": "Фамилия, И. О., & Фамилия, И. О. (Год). Название статьи. Название журнала, том(номер), страницы. DOI",
            "Онлайн-журнал": "Фамилия, И. О. (Год). Название статьи. Название журнала, (номер), страницы. Retrieved from URL",
            "Сетевое издание": "Фамилия, И. О. (Год, Month Day). Название статьи. Название сайта. Retrieved from URL",
            "Книга": "Фамилия, И. О. (Год). Название книги. Город: Издательство"
        },
        "GOST": {
            "Статья в журнале": "Фамилия И.О. Название статьи // Журнал. Год. Т. X. № Y. С. Z–Z. DOI/URL",
            "Книга": "Фамилия И.О. Название. Место: Издательство, Год. Кол-во страниц",
            "Материалы конференций": "Название / под ред. Фамилия И.О. Место: Издательство, Год. Кол-во страниц",
            "Статья в печати": "Фамилия И.О. Название // Журнал. Год. Т. X. № Y (в печати)",
            "Онлайн-статья": "Фамилия И.О. Название // Журнал. Год. URL: ... (дата обращения: ДД.ММ.ГГГГ)"
        },
        "MLA": {
            "Журнальная статья": 'Фамилия, Имя и Имя Фамилия. "Название статьи." Название журнала, т. X, № Y, Год, с. Z–Z. DOI/URL',
            "Интернет-журнал": 'Фамилия, Имя. "Название статьи." Название журнала, т. X, Год, с. Z–Z. URL',
            "Статья в онлайн-СМИ": 'Фамилия, Имя. "Название статьи." Название сайта, День Месяц Год, URL',
            "Монография": "Фамилия, Имя. Название книги. Место, Издательство, Год"
        }
    }

    # Промпты для извлечения данных
    prompt_templates = {
        "APA": {
            "Журнальная статья": """Ты — эксперт по APA и BibTeX. Извлеки любые доступные данные из библиографической записи и верни их в формате:
author: ...
title: ...
journal: ...
volume: ...
number: ...
year: ...
pages: ...
doi: ...
Если какого-то поля нет, просто пропусти его.
Пример:
Вход: "Экономика и управление: Учебник / Под ред. А. А. Смирнова. — М.: Просвещение, 2018. — 400 с."
Выход:
editor: Смирнов, А. А.
title: Экономика и управление: Учебник
year: 2018
publisher: Просвещение
address: М.
pages: 400
Запись: "{reference}" """,
            "Онлайн-журнал": """Ты — эксперт по APA и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
journal: ...
number: ...
year: ...
pages: ...
url: ...
Если какого-то поля нет, пропусти его.
Запись: "{reference}" """,
            "Сетевое издание": """Ты — эксперт по APA и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
year: ...
month: ...
day: ...
publisher: ...
url: ...
note: ...
Если какого-то поля нет, пропусти его.
Запись: "{reference}" """,
            "Книга": """Ты — эксперт по APA и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ... (или editor: ..., если есть "Под ред.")
title: ...
year: ...
publisher: ...
address: ...
pages: ...
Если какого-то поля нет, пропусти его.
Запись: "{reference}" """
        },
        "GOST": {
            "Статья в журнале": """Ты — эксперт по ГОСТ и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
journal: ...
volume: ...
number: ...
year: ...
pages: ...
doi: ...
url: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Пакшина С.М. Передвижение солей в почве // Почвоведение. 1980. Т. 5. № 3. С. 45–50."
Выход:
author: Пакшина С.М.
title: Передвижение солей в почве
journal: Почвоведение
volume: 5
number: 3
year: 1980
pages: 45–50
Запись: "{reference}" """,
            "Книга": """Ты — эксперт по ГОСТ и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
year: ...
publisher: ...
address: ...
pages: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Пакшина С.М. Передвижение солей в почве. М.: Наука, 1980. 120 с."
Выход:
author: Пакшина С.М.
title: Передвижение солей в почве
year: 1980
publisher: Наука
address: М.
pages: 120
Запись: "{reference}" """,
            "Материалы конференций": """Ты — эксперт по ГОСТ и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
editor: ...
title: ...
year: ...
publisher: ...
address: ...
pages: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Современные проблемы почвоведения / под ред. С.М. Пакшиной. М.: Наука, 1980. 200 с."
Выход:
editor: Пакшина С.М.
title: Современные проблемы почвоведения
year: 1980
publisher: Наука
address: М.
pages: 200
Запись: "{reference}" """,
            "Статья в печати": """Ты — эксперт по ГОСТ и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
journal: ...
volume: ...
number: ...
year: ...
note: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Пакшина С.М. Передвижение солей в почве // Почвоведение. 1980. Т. 5. № 3 (в печати)."
Выход:
author: Пакшина С.М.
title: Передвижение солей в почве
journal: Почвоведение
volume: 5
number: 3
year: 1980
note: в печати
Запись: "{reference}" """,
            "Онлайн-статья": """Ты — эксперт по ГОСТ и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
journal: ...
year: ...
url: ...
note: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Пакшина С.М. Передвижение солей в почве // Почвоведение. 1980. URL: http://example.com (дата обращения: 01.01.2025)."
Выход:
author: Пакшина С.М.
title: Передвижение солей в почве
journal: Почвоведение
year: 1980
url: http://example.com
note: дата обращения: 01.01.2025
Запись: "{reference}" """,
        },
        "MLA": {
            "Журнальная статья": """Ты — эксперт по MLA и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
journal: ...
volume: ...
number: ...
year: ...
pages: ...
doi: ...
url: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Пакшина, Светлана Михайловна. \"Передвижение солей в почве.\" Почвоведение, т. 5, № 3, 1980, с. 45–50."
Выход:
author: Пакшина, Светлана Михайловна
title: Передвижение солей в почве
journal: Почвоведение
volume: 5
number: 3
year: 1980
pages: 45–50
Запись: "{reference}" """,
            "Интернет-журнал": """Ты — эксперт по MLA и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
journal: ...
volume: ...
year: ...
pages: ...
url: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Пакшина, Светлана Михайловна. \"Передвижение солей в почве.\" Почвоведение, т. 5, 1980, с. 45–50. URL: http://example.com."
Выход:
author: Пакшина, Светлана Михайловна
title: Передвижение солей в почве
journal: Почвоведение
volume: 5
year: 1980
pages: 45–50
url: http://example.com
Запись: "{reference}" """,
            "Статья в онлайн-СМИ": """Ты — эксперт по MLA и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
publisher: ...
year: ...
month: ...
day: ...
url: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Пакшина, Светлана Михайловна. \"Передвижение солей в почве.\" Наука Сегодня, 1 января 1980, http://example.com."
Выход:
author: Пакшина, Светлана Михайловна
title: Передвижение солей в почве
publisher: Наука Сегодня
year: 1980
month: января
day: 1
url: http://example.com
Запись: "{reference}" """,
            "Монография": """Ты — эксперт по MLA и BibTeX. Извлеки любые доступные данные из записи и верни их в формате:
author: ...
title: ...
publisher: ...
address: ...
year: ...
Если какого-то поля нет, пропусти его.
Пример:
Вход: "Пакшина, Светлана Михайловна. Передвижение солей в почве. Москва, Наука, 1980."
Выход:
author: Пакшина, Светлана Михайловна
title: Передвижение солей в почве
publisher: Наука
address: Москва
year: 1980
Запись: "{reference}" """,
        }
    }

    # BibTeX-типы для каждого подформата
    bibtex_types = {
        "APA": {
            "Журнальная статья": "article",
            "Онлайн-журнал": "article",
            "Сетевое издание": "misc",
            "Книга": "book"
        },
        "GOST": {
            "Статья в журнале": "article",
            "Книга": "book",
            "Материалы конференций": "inproceedings",
            "Статья в печати": "article",
            "Онлайн-статья": "article"
        },
        "MLA": {
            "Журнальная статья": "article",
            "Интернет-журнал": "article",
            "Статья в онлайн-СМИ": "misc",
            "Монография": "book"
        }
    }

    # Поля для каждого типа BibTeX-записи
    # Полностью покрывает все подформаты APA, GOST, MLA согласно спецификации
    bibtex_fields = {
        "article": [
            "author", "title", "journal", "volume", "number", "year", "pages", "doi", "url", "note"
        ],  # Для APA: Журнальная статья, Онлайн-журнал; GOST: Статья в журнале, Статья в печати, Онлайн-статья; MLA: Журнальная статья, Интернет-журнал
        "book": [
            "author", "editor", "title", "year", "publisher", "address", "pages"
        ],  # Для APA: Книга; GOST: Книга; MLA: Монография
        "misc": [
            "author", "title", "year", "month", "day", "publisher", "url", "note"
        ],  # Для APA: Сетевое издание; MLA: Статья в онлайн-СМИ
        "inproceedings": [
            "editor", "title", "year", "publisher", "address", "pages"
        ]  # Для GOST: Материалы конференций
    }

    target_format = target_format.upper()

    # Подготовка промпта
    if target_format not in prompt_templates:
        prompt_templates[target_format] = {}
    if subformat not in prompt_templates[target_format]:
        prompt_templates[target_format][subformat] = GENERIC_PROMPT

    prompt = prompt_templates[target_format][subformat].format(reference=reference)

    bibtex_type = bibtex_types.get(target_format, {}).get(subformat)
    if not bibtex_type:
        return f"Ошибка: тип BibTeX для {target_format} {subformat} не найден."

    possible_fields = bibtex_fields.get(bibtex_type, [])

    # Инициализация клиента OpenAI
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=300
        )
        raw_response = response.choices[0].message.content.strip()
        logger.info("Полный ответ нейросети: %s", raw_response)

        # Парсинг ответа в словарь
        data = {}
        for line in raw_response.splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
                data[key.strip()] = value.strip()

        if not data:
            return f"Ошибка: не удалось извлечь данные из записи.\nОжидаемая структура для {target_format} ({subformat}):\n{expected_structures[target_format][subformat]}"

        # Генерация ключа
        key = generate_bibtex_key(data)

        # Динамическое построение BibTeX
        bibtex_lines = [f"@{bibtex_type}{{{key},"]
        for field in possible_fields:
            if field in data and data[field]:
                bibtex_lines.append(f"  {field} = \"{{{data[field]}}}\",")
        bibtex_lines[-1] = bibtex_lines[-1].rstrip(",")  # Убираем последнюю запятую
        bibtex_lines.append("}")

        bibtex_entry = "\n".join(bibtex_lines)

        # Проверка полноты данных
        required_fields = [f for f in possible_fields if f not in {"doi", "url", "note", "month", "day"}]
        missing_fields = [f for f in required_fields if f not in data or not data[f]]
        if missing_fields:
            warning = (
                f"Предупреждение: неполные данные. Отсутствуют поля: {', '.join(missing_fields)}.\n"
                f"Ожидаемая структура для {target_format} ({subformat}):\n{expected_structures[target_format][subformat]}"
            )
            bibtex_entry += f"\n% {warning}"

        logger.info("Сформированная BibTeX-запись: %s", bibtex_entry)
        return bibtex_entry

    except Exception as e:
        logger.error("Ошибка при работе с нейросетью: %s", str(e))
        return f"Ошибка AI-сервиса: {str(e)}\nОжидаемая структура для {target_format} ({subformat}):\n{expected_structures[target_format][subformat]}"

def generate_bibtex_key(data: dict) -> str:
    if "author" in data:
        author = data["author"].split(",")[0].lower().replace(" ", "")
        year = data.get("year", "nodate")
        return f"{author}{year}"
    elif "editor" in data:
        editor = data["editor"].split(",")[0].lower().replace(" ", "")
        year = data.get("year", "nodate")
        return f"{editor}{year}"
    else:
        title_words = data.get("title", "").split()[:2]
        year = data.get("year", "nodate")
        return f"{'_'.join(title_words).lower()}{year}" if title_words else f"unknown{year}"

def format_reference_to_tex(reference: str, target_format: str, subformat: str) -> str:
    return format_reference_to_bibtex_with_ai(reference, target_format, subformat)