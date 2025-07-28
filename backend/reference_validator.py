import re
from typing import Tuple, List, Dict
import logging
import os
# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def basic_validation(reference: str) -> Tuple[bool, List[str]]:
    """
    Базовая проверка ссылки: наличие текста и года.
    Возвращает кортеж (валидность, список ошибок).
    """
    errors = []
    if not reference.strip():
        errors.append("Ссылка пуста")
        return False, errors
    if not re.search(r'\b\d{4}\b', reference):
        errors.append("Отсутствует год (ожидается 4-значное число, например, 2020)")
    return len(errors) == 0, errors

# Словарь требований для ГОСТ
GOST_REQUIREMENTS = {
    "Книга": {
        "required": ["author", "title", "publisher"],
        "optional": ["isbn", "city", "year", "pages"]
    },
    "Статья в журнале": {
        "required": [ "author","title","journal" ],
        "optional": ["doi", "url", "year", "volume", "issue", "pages"]
    },
    "Материалы конференций": {
        "required": ["title", "city", "publisher"],
        "optional": ["editor", "year", "pages"]
    },
    "Статья в печати": {
        "required": ["author", "title", "journal"],
        "optional": ["year", "volume", "issue"]
    },
    "Онлайн-статья": {
        "required": ["author", "title", "journal"],
        "optional": ["volume", "issue", "pages", "year", "url", "access_date"]
    }
}

# Сокращения городов
CITY_ABBREVIATIONS = {
    "М.": "Москва",
    "СПб.": "Санкт-Петербург",
    "Н.": "Новгород",
    "К.": "Казань"
}

def extract_gost_fields(reference: str, ref_type: str) -> Dict[str, str]:
    """
    Извлечение полей из ссылки для ГОСТ в зависимости от типа записи.
    Возвращает словарь с найденными полями.
    """
    # Очистка ссылки от лишних пробелов
    reference = re.sub(r'\s+', ' ', reference.strip())
    fields = {}
    patterns = {
        "author": r'^([А-Яа-яA-Za-zЁё]+(?:\s+[А-Яа-яA-Za-zЁё]\.\s*[А-Яа-яA-Za-zЁё]?\.?)?(?:,\s*[А-Яа-яA-Za-zЁё]+(?:\s+[А-Яа-яA-Za-zЁё]\.\s*[А-Яа-яA-Za-zЁё]?\.?)?)*(?:\s*,\s*\.\.\.,\s*(?:и\s*др\.|et\s*al\.))?)',
        "title": r'(?:[А-Яа-яA-Za-zЁё]\.\s+)(.+?)(?=\.\s*(?:[А-Яа-яA-Za-zЁё]*:|\d{4}|//))',
        "city": r'(?:\.|//)\s*([А-Яа-яA-Za-zЁё\.]+(?:\s+[А-Яа-яA-Za-zЁё]+)?)\s*:',
        "publisher": r':\s*([А-Яа-яA-Za-zЁё\s\-]+)(?=,\s*\d{4})',
        "year": r',\s*(\d{4})(?=\.|$)',
        "pages": r'(\d+\s*с\.?\s*)',
        "journal": r'//\s*(.+?)\.(?=\s*\d{4})',
        "volume": r'(?:Т\.|Vol\.)\s*(\d+)',
        "issue": r'№\s*(\d+)',
        "doi": r'(DOI|doi):\s*([^\s]+)',
        "url": r'URL:\s*(https?://[^\s]+)',
        "access_date": r'\(дата\s*обращения:\s*(\d{2}\.\d{2}\.\d{4})\)',
        "isbn": r'ISBN\s*(\d{13}|\d{10})',
        "editor": r'под\s*ред\.\s*([А-Яа-яA-Za-zЁё]+(?:\s+[А-Яа-яA-Za-zЁё]\.\s*[А-Яа-яA-Za-zЁё]?\.?)?)'
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, reference, re.UNICODE)
        if match:
            fields[field] = match.group(1).strip()
            # Обработка сокращений городов
            if field == "city" and fields[field] in CITY_ABBREVIATIONS:
                fields[field] = CITY_ABBREVIATIONS[fields[field]]

    # Специфичные проверки
    if ref_type == "Статья в печати" and "(в печати)" in reference:
        fields["in_press"] = "(в печати)"

    logger.info(f"Fields extracted for '{reference}': {fields}")
    return fields

def validate_reference_by_style(reference: str, style: str, subformat: str = None) -> Tuple[bool, List[str], str]:
    """
    Проверка ссылки на соответствие заданному стилю и типу записи.
    Если subformat указан, проверяет строго на соответствие этому типу.
    Возвращает кортеж (валидность, список ошибок, предполагаемый тип записи).
    """
    logger.info(f"Validating reference '{reference}' with style={style}, subformat={subformat}")
    # Базовая проверка
    is_valid, errors = basic_validation(reference)
    if not is_valid:
        return False, errors, "Не определён"

    style = style.upper()
    ref_type = "Не определён"

    if style == "APA":
        author_pattern = r'[А-Яа-яA-Za-zЁё]+,\s*[А-Яа-яA-Za-zЁё]\.\s*[А-Яа-яA-Za-zЁё]?\.?(?:\s*,\s*[А-Яа-яA-Za-zЁё]+,\s*[А-Яа-яA-Za-zЁё]\.\s*[А-Яа-яA-Za-zЁё]?\.?)*\s*(?:,\s*&\s*[А-Яа-яA-Za-zЁё]+,\s*[А-Яа-яA-Za-zЁё]\.\s*[А-Яа-яA-Za-zЁё]?\.)?'
        year_pattern = r'\(\d{4}(?:,\s*[A-Za-z]+\s*\d+)?\)'
        title_pattern = r'.+?\.'

        apa_pattern = rf'^(?:\d+\.\s*)?{author_pattern}\s*{year_pattern}\.\s*{title_pattern}'
        if not re.match(apa_pattern, reference):
            errors.append("Не соответствует общей структуре APA: ожидается 'Фамилия, И. О. (Год). Название...'")
            return False, errors, ref_type

        if re.search(r',\s*(?:\d+\(\d+\)|\(\d+\)),\s*\d+(?:–\d+)?', reference):
            ref_type = "Журнальная статья"
        elif re.search(r'Retrieved\s+from\s*https?://', reference):
            if re.search(r',\s*\(\d+\),', reference):
                ref_type = "Онлайн-журнал"
            else:
                ref_type = "Сетевое издание"
        elif re.search(r'[А-Яа-яA-Za-zЁё]+(?:\s*[А-Яа-яA-Za-zЁё]+)?(?::\s*[А-Яа-яA-Za-zЁё]+(?:\s*[А-Яа-яA-Za-zЁё]+)?)', reference):
            ref_type = "Книга"

        if subformat and subformat != ref_type:
            errors.append(f"Ссылка не соответствует типу '{subformat}': определённый тип — '{ref_type}'")
            return False, errors, ref_type

        return len(errors) == 0, errors, ref_type

    elif style == "MLA":
        author_pattern = r'[А-Яа-яA-Za-zЁё]+,\s*[А-Яа-яA-Za-zЁё]+(?:\s+[А-Яа-яA-Za-zЁё]+)?(?:\s+и\s+[А-Яа-яA-Za-zЁё]+\s+[А-Яа-яA-Za-zЁё]+)?(?:,\s*и\s*др\.)?'
        title_pattern = r'"[^\."]+\."'
        source_pattern = r'[А-Яа-яA-Za-zЁё]+(?:\s+[А-Яа-яA-Za-zЁё]+)*'

        mla_pattern = rf'^(?:\d+\.\s*)?{author_pattern}\s*\.\s*{title_pattern}\s*{source_pattern}'
        if not re.match(mla_pattern, reference):
            errors.append("Не соответствует общей структуре MLA: ожидается 'Фамилия, Имя. \"Название.\" Источник...'")
            return False, errors, ref_type

        if re.search(r'(?:т\.|vol\.)\s*\d+,\s*№\s*\d+', reference):
            ref_type = "Журнальная статья"
        elif re.search(r'(?:vol\.|т\.)\s*\d+,\s*\d{4},\s*(?:pp\.|с\.)\s*\d+(?:–\d+)?\.\s*https?://', reference):
            ref_type = "Интернет-журнал"
        elif re.search(r',\s*\d{1,2}\s+[А-Яа-яA-Za-zЁё]+\s+\d{4},', reference):
            ref_type = "Статья в онлайн-СМИ"
        elif re.search(r',\s*[А-Яа-яA-Za-zЁё]+(?:\s+[А-Яа-яA-Za-zЁё]+)*,\s*\d{4}$', reference):
            ref_type = "Монография"

        if subformat and subformat != ref_type:
            errors.append(f"Ссылка не соответствует типу '{subformat}': определённый тип — '{ref_type}'")
            return False, errors, ref_type

        return len(errors) == 0, errors, ref_type

    elif style == "GOST":
        # Обновлённая логика для ГОСТ
        # Определяем тип записи
        if re.search(r'//\s*.+?\.\s*\d{4}', reference):
            if re.search(r'\(в\s*печати\)', reference):
                ref_type = "Статья в печати"
            elif re.search(r'URL:\s*https?://.+?\s*\(дата\s*обращения:', reference):
                ref_type = "Онлайн-статья"
            else:
                ref_type = "Статья в журнале"
        elif re.search(r'под\s*ред\.', reference):
            ref_type = "Материалы конференций"
        else:
            ref_type = "Книга"

        if subformat and subformat != ref_type:
            errors.append(f"Ссылка не соответствует типу '{subformat}': определённый тип — '{ref_type}'")
            return False, errors, ref_type

        # Извлекаем поля
        fields = extract_gost_fields(reference, ref_type)
        logger.info(f"Validating reference '{reference}' with fields: {fields}")

        # Проверяем обязательные поля
        if ref_type in GOST_REQUIREMENTS:
            required_fields = GOST_REQUIREMENTS[ref_type]["required"]
            for field in required_fields:
                if field not in fields:
                    # Исключение для "в печати", где страницы необязательны
                    if ref_type == "Статья в печати" and field == "pages" and "in_press" in fields:
                        continue
                    errors.append(f"Отсутствует обязательное поле для '{ref_type}': {field}")

        # Дополнительные проверки формата
        if "year" in fields and not re.match(r'\d{4}', fields["year"]):
            errors.append("Год должен быть в формате четырёх цифр (например, '1980')")
        if "pages" in fields and not re.match(r'\d+\s*с\.?', fields["pages"]):
            errors.append("Страницы должны быть в формате '120 с.' или '120с.'")

        logger.info(f"Validation result: is_valid={len(errors) == 0}, errors={errors}, ref_type={ref_type}")
        return len(errors) == 0, errors, ref_type

    else:
        return True, [], "Не определён"

def validate_references(references: List[str], style: str, subformat: str = None) -> Tuple[List[Tuple[str, str, str]], List[Dict[str, str]]]:
    """
    Разделение ссылок на валидные и невалидные по заданному стилю и типу записи.
    Возвращает кортеж (валидные ссылки, невалидные ссылки).
    """
    logger.info(f"Validating references with style={style}, subformat={subformat}")
    valid = []
    invalid = []
    for ref in references:
        is_valid, errors, ref_type = validate_reference_by_style(ref, style, subformat)
        logger.info(f"Reference: {ref}, is_valid: {is_valid}, ref_type: {ref_type}, errors: {errors}")
        if is_valid:
            valid.append((ref, "", ref_type))
        else:
            invalid.append({"original": ref, "errors": errors, "type": ref_type})
    logger.info(f"Valid references: {valid}")
    logger.info(f"Invalid references: {invalid}")
    return valid, invalid