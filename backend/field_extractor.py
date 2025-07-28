# backend/field_extractor.py

import openai
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY не найден в переменных окружения.")

MODEL = "deepseek-chat"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_fields(reference: str, target_format: str = None, target_subformat: str = None) -> dict:
    """
    Извлекает поля библиографической записи с помощью нейросети DeepSeek.
    Возвращает словарь с полями, фильтрованными в зависимости от целевого формата и подтипа.
    """
    # Определяем допустимые поля для каждого формата и подтипа
    allowed_fields = {
        "APA": {
            "Журнальная статья": ["author", "title", "journal", "volume", "number", "year", "pages", "doi"],
            "Онлайн-журнал": ["author", "title", "journal", "number", "year", "pages", "url"],
            "Сетевое издание": ["author", "title", "year", "month", "day", "publisher", "url"],
            "Книга": ["author", "editor", "title", "year", "publisher", "address", "pages"]
        },
        "GOST": {
            "Статья в журнале": ["author", "title", "journal", "volume", "number", "year", "pages", "doi", "url"],
            "Книга": ["author", "title", "year", "publisher", "address", "pages"],
            "Материалы конференций": ["editor", "title", "year", "publisher", "address", "pages"],
            "Статья в печати": ["author", "title", "journal", "volume", "number", "year", "note"],
            "Онлайн-статья": ["author", "title", "journal", "year", "url", "note"]
        },
        "MLA": {
            "Журнальная статья": ["author", "title", "journal", "volume", "number", "year", "pages", "doi", "url"],
            "Интернет-журнал": ["author", "title", "journal", "volume", "year", "pages", "url"],
            "Статья в онлайн-СМИ": ["author", "title", "publisher", "year", "month", "day", "url"],
            "Монография": ["author", "title", "publisher", "address", "year"]
        }
    }

    # Промпт для нейросети
    prompt = f"""Ты — эксперт по библиографии. Извлеки из библиографической записи все доступные поля и верни их в формате:
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
Если какое-то поле отсутствует, пропусти его. Каждое поле должно быть на новой строке. Для MLA (Журнальная статья)

Примеры:
Вход: Ким С. Ю. Искусственный интеллект и право. — Казань: Университетская книга, 2024. 280 с.
Выход:
author: Ким С. Ю.
title: Искусственный интеллект и право
year: 2024
publisher: Университетская книга
address: Казань
pages: 280

Вход: Пакшина С.М. Передвижение солей в почве // Почвоведение. 1980. Т. 5. № 3. С. 45–50. DOI: 10.1234/example
Выход:
author: Пакшина С.М.
title: Передвижение солей в почве
journal: Почвоведение
volume: 5
number: 3
year: 1980
pages: 45–50
doi: 10.1234/example

Вход: Жукова Т. А. "Кросс-культурные коммуникации." Коммуникационные исследования, т. 6, № 1, 2025
Выход:
author: Жукова Т. А.
title: Кросс-культурные коммуникации
journal: Коммуникационные исследования
volume: 6
number: 1
year: 2025

Вход: Жукова Т. А. Кросс‑культурные коммуникации // Коммуникационные исследования. 2025. Т. 6. № 1 (в печати)
Выход:
author: Жукова Т. А.
title: Кросс-культурные коммуникации
journal: Коммуникационные исследования
volume: 6
number: 1
year: 2025
note: в печати

Запись: "{reference}"
"""

    # Инициализация клиента OpenAI
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=150
        )
        raw_response = response.choices[0].message.content.strip()
        logger.info("Ответ нейросети для извлечения полей: %s", raw_response)

        # Парсинг ответа в словарь
        fields = {}
        for line in raw_response.splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
                fields[key.strip()] = value.strip()

        if not fields:
            logger.warning("Не удалось извлечь поля из записи: %s", reference)
            return {}

        # Фильтрация полей в зависимости от target_format и target_subformat
        if target_format and target_subformat:
            target_format = target_format.upper()
            allowed = allowed_fields.get(target_format, {}).get(target_subformat, [])
            filtered_fields = {k: v for k, v in fields.items() if k in allowed}
            logger.info("Фильтрованные поля для %s (%s): %s", target_format, target_subformat, filtered_fields)
            return filtered_fields

        logger.info("Извлеченные поля: %s", fields)
        return fields

    except Exception as e:
        logger.error("Ошибка при работе с нейросетью: %s", str(e))
        return {}