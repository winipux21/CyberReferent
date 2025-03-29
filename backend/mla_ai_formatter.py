"""
mla_ai_formatter.py

Модуль для нейросетевого анализа и форматирования библиографической записи по стандарту MLA.
Подсказки теперь унифицированы и содержат следующие требования:
- Номер записи в начале не допускается.
- Автор должен быть указан в формате "Фамилия, Имя" (например, "Smith, John").
- Название статьи должно быть взято в кавычки.
- Название журнала или издательства должно быть указано полностью.
- Год издания указывается после названия.
- Дополнительные данные (том, номер, страницы) оформляются согласно стандарту MLA.
- Если применимо, обязательно указан DOI или URL.
Если каких-либо данных не хватает, явно укажи, что необходимо дополнить информацию.
После анализа выведи:
1. Список обнаруженных ошибок с подробным описанием.
2. Корректный вариант оформления записи по MLA согласно шаблону:
   Author. "Title of Article." Title of Periodical, vol. number, no. number, Year, pages. [DOI/URL]
   
Пример:
Ввод:
"Smith, J., Advances in AI, Journal of Modern Science, 2020, vol. 10, no. 2, pp. 123-130"
Вывод:
ОШИБКИ:
- Неправильное оформление автора (ожидается "Smith, John").
- Отсутствует DOI или URL.
MLA:
Smith, John. "Advances in AI." Journal of Modern Science, vol. 10, no. 2, 2020, pp. 123-130. [Указать DOI/URL].
   
Ссылка пользователя:
"{reference}"
"""

import openai

DEEPSEEK_API_KEY = "sk-15abeb7685c742478a7be0f4827c7cef"
MODEL = "deepseek-chat"

def format_mla_ai(reference: str) -> str:
    prompt = f"""
Ты — эксперт по оформлению библиографических ссылок согласно стандарту MLA.
Задача:
Пользователь передаёт тебе текст библиографической ссылки, которая должна соответствовать следующим требованиям:
- Номер записи (например, "3.") в начале не допускается.
- Автор должен быть указан в формате "Фамилия, Имя" (например, "Smith, John").
- Название статьи должно быть заключено в кавычки.
- Название журнала или издательства должно быть указано полностью.
- Год издания должен быть указан после названия.
- Дополнительные данные (том, номер, страницы) должны быть оформлены согласно стандарту.
- Если применимо, обязательно указан DOI или URL.
Если каких-то данных не хватает, явно укажи, что необходимо дополнить информацию.
После анализа выведи:
1. Список обнаруженных ошибок с подробным описанием.
2. Корректный вариант оформления записи по MLA согласно шаблону:
   Author. "Title of Article." Title of Periodical, vol. number, no. number, Year, pages. [DOI/URL]
   
Пример:
Ввод:
"Smith, J., Advances in AI, Journal of Modern Science, 2020, vol. 10, no. 2, pp. 123-130"
Вывод:
ОШИБКИ:
- Неправильное оформление автора (ожидается "Smith, John").
- Отсутствует DOI или URL.
MLA:
Smith, John. "Advances in AI." Journal of Modern Science, vol. 10, no. 2, 2020, pp. 123-130. [Указать DOI/URL].
   
Ссылка пользователя:
"{reference}"
"""
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка при вызове нейросетевого сервиса: {e}"

# Пример тестирования:
if __name__ == "__main__":
    test_reference = "Smith, J., Advances in AI, Journal of Modern Science, 2020, vol. 10, no. 2, pp. 123-130"
    result = format_mla_ai(test_reference)
    print("Исходная запись:")
    print(test_reference)
    print("\nРезультат нейросетевого форматирования:")
    print(result)
