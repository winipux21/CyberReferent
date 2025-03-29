import pandas as pd
import re

def load_vak_list(path='data/VAK_journals.csv'):
    """
    Загружает список журналов ВАК из CSV-файла.
    """
    return pd.read_csv(path)

def find_journal_name(reference):
    """
    Пытается найти название журнала или издательства в библиографической записи.
    """
    patterns = [
        r'//\s*(.*?)\.\s*–\s*\d{4}',    # Для ГОСТа: после "//" до ". – год"
        r':\s*([^:]+)\.\s*ISBN',         # Для APA: после ":" до ". ISBN"
        r'\.\s*([^\.]+)\.\s*\d{4}'        # Для MLA: после точки до ". год"
    ]
    for pattern in patterns:
        match = re.search(pattern, reference, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    return ""

def validate_format(reference: str, style: str) -> (bool, list):
    """
    Проверяет, соответствует ли библиографическая запись базовым требованиям выбранного стиля.
    Основное внимание уделяется наличию и порядку ключевых элементов:
      — Для APA: должна быть последовательность "Авторы (год). Название. Издательство [ISBN]".
      — Для ГОСТ: должна быть последовательность "Авторы. Название — Издательство, год" (с элементами тома/номера, если применимо).
      — Для MLA: должна быть последовательность "Авторы. 'Название.' Издательство, год, ..." 
    Возвращает (is_valid, список_ошибок). Ошибки – это критичные замечания о пропущенных элементам.
    """
    errors = []
    # Удаляем начальный порядковый номер
    ref_clean = re.sub(r'^\d+\.\s*', '', reference.strip())

    if style.upper() == "APA":
        # 1. Авторы: Проверяем, что до первой открывающей скобки присутствует текст (авторы)
        if not re.match(r'.+?\(\d{4}\)', ref_clean):
            errors.append("Отсутствуют авторы или год. Ожидается последовательность: 'Авторы (год)'.")
        # 2. Год: Проверяем наличие (YYYY)
        if not re.search(r'\(\d{4}\)', ref_clean):
            errors.append("Отсутствует год издания в круглых скобках, например, '(2020)'.")
        # 3. Название работы: После года должна идти часть с названием
        if not re.search(r'\(\d{4}\)\. ', ref_clean):
            errors.append("Отсутствует разделитель после года, ожидается точка после скобок.")
        elif not re.search(r'\(\d{4}\)\.\s+.+\.', ref_clean):
            errors.append("Отсутствует название работы или оно не заканчивается точкой.")
        # 4. Издательство: Должен присутствовать блок с двоеточием (например, "Город: Издательство")
        if not re.search(r':\s*.+\.', ref_clean):
            errors.append("Отсутствует информация об издательстве. Ожидается формат 'Город: Издательство.'")
        # 5. ISBN (если указан): Проверяем, что если присутствует слово ISBN, то далее 13 цифр (с или без дефисов)
        isbn_match = re.search(r'ISBN\s+([\d-]+)', ref_clean)
        if isbn_match:
            isbn = isbn_match.group(1).strip()
            isbn_digits = isbn.replace('-', '')
            if len(isbn_digits) != 13 or not isbn_digits.isdigit():
                errors.append("ISBN должен содержать 13 цифр (с дефисами или без).")
        # Если ISBN не указан – можно рекомендовать его добавить для книг.
    
    elif style.upper() == "GOST":
        # Для ГОСТ: последовательность "Авторы. Название — Издательство, год"
        if not re.match(r'.+?\.\s+.+? —', ref_clean):
            errors.append("Отсутствуют авторы или название. Ожидается последовательность: 'Авторы. Название —'.")
        if not re.search(r'—\s*.+?,\s*\d{4}', ref_clean):
            errors.append("Отсутствует информация об издательстве или год после '—'.")
    
    elif style.upper() == "MLA":
        # Для MLA: последовательность "Авторы. 'Название.' Издательство, год, ..."
        if not re.match(r'.+?\.\s+', ref_clean):
            errors.append("Отсутствуют авторы. Ожидается, что запись начинается с авторов, оканчивающихся точкой.")
        if not re.search(r'"\S.+?"', ref_clean):
            errors.append("Отсутствует название работы в кавычках.")
        if not re.search(r',\s*\d{4}', ref_clean):
            errors.append("Отсутствует год издания, ожидается, что он указан после издательства через запятую.")
    
    else:
        errors.append("Неизвестный стиль оформления. Поддерживаются: APA, GOST, MLA.")
    
    is_valid = len(errors) == 0
    return is_valid, errors

def validate_references(references, vak_df, style="APA"):
    """
    Проходит по списку записей, проверяет их базовое соответствие выбранному стилю и пытается найти журнал
    в списке ВАК. Если журнал не найден – для книг возвращает (reference, None, None).
    
    Возвращает:
      valid – список кортежей (reference, journal, ISSN)
      invalid – список кортежей (reference, [список ошибок])
    """
    valid = []
    invalid = []
    vak_journals_lower = vak_df['journal'].str.lower().tolist()
    
    for ref in references:
        ref_clean = re.sub(r'^\d+\.\s*', '', ref.strip())
        is_valid, messages = validate_format(ref_clean, style)
        if is_valid:
            journal_name = find_journal_name(ref_clean)
            if journal_name:
                found = [j for j in vak_journals_lower if journal_name in j or j in journal_name]
                if found:
                    matched_journal = vak_df[vak_df['journal'].str.lower() == found[0]].iloc[0]
                    valid.append((ref_clean, matched_journal['journal'], matched_journal['ISSN']))
                else:
                    valid.append((ref_clean, None, None))  # Для книг или источников без журнала
            else:
                valid.append((ref_clean, None, None))
        else:
            invalid.append((ref_clean, messages))
    return valid, invalid
