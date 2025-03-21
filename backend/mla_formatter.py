"""
mla_formatter.py

Модуль для форматирования библиографической ссылки по стандарту MLA.
Пример оформления MLA для статьи:
  Author. "Title of Article." Title of Periodical, vol. number, no. number, Year, pages.

Если каких-либо данных не хватает, функция возвращает сообщение с указанием недостатка информации.
"""

def format_mla(reference: str) -> str:
    """
    Форматирует библиографическую ссылку в стиле MLA.
    
    Аргументы:
        reference (str): Исходная библиографическая запись.
    
    Возвращает:
        str: Отформатированная запись по стандарту MLA или сообщение об ошибке.
    """
    if not reference.strip():
        return "Ошибка: Пустая библиографическая запись."

    # Простейшая логика разбора записи.
    # Предполагается, что входная запись содержит основные элементы, разделённые запятыми:
    # Автор, Название статьи, Название журнала/издательства, Год, Остальные данные (например, том, номер, страницы)
    parts = [part.strip() for part in reference.split(',')]
    if len(parts) < 4:
        return "Ошибка: Недостаточно данных для формирования записи по MLA. Проверьте входную запись."

    # Извлекаем основные элементы
    author = parts[0]
    title = parts[1]
    source = parts[2]
    year = parts[3]
    rest = ', '.join(parts[4:]) if len(parts) > 4 else ""

    # Простейший пример форматирования MLA:
    # Автор. "Название статьи." Название журнала, Год, Остальные данные.
    formatted = f"{author}. \"{title}.\" {source}, {year}"
    if rest:
        formatted += f", {rest}"
    formatted += "."

    # Добавляем пометку о формате
    return f"MLA: {formatted}"


# Пример тестирования:
if __name__ == "__main__":
    test_reference = "Smith, J., Advances in AI, Journal of Modern Science, 2020, vol. 10, no. 2, pp. 123-130"
    print("Исходная запись:")
    print(test_reference)
    print("\nОтформатированная запись:")
    print(format_mla(test_reference))
