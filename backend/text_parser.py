# backend/text_parser.py
import re

def clean_multiline_refs(ref):

    ref = re.sub(r'-\n\s*', '', ref)
    ref = re.sub(r'(?<=[a-zа-яё])(?=[A-ZА-ЯЁ])', ' ', ref)
    ref = re.sub(r'\n+', ' ', ref)
    ref = re.sub(r'\s+', ' ', ref)
    return ref.strip()

def split_references_from_text(bibliography_text):

    # Попытка разделить текст по шаблону "Пример оформления..."
    references = re.split(r'Пример оформления.*?:\s*\d+\s*', bibliography_text)
    
    # Если разделение по шаблону "Пример оформления" не дало результата, пробуем по нумерации
    if len(references) <= 1:
        references = re.split(r'\n\d+\.\s', bibliography_text)
    
    # Фильтрация пустых элементов и очистка каждой записи
    references = [clean_multiline_refs(ref) for ref in references if len(ref.strip()) > 5]
    return references

