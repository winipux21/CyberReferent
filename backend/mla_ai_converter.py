"""
mla_ai_converter.py

Модуль для преобразования библиографической ссылки в корректное оформление по стандарту MLA в виде одной строки.
Структура результата:
Author. "Title of Article." Title of Periodical, vol. number, no. number, Year, pp. pages. [DOI/URL]
"""

import openai

DEEPSEEK_API_KEY = "sk-15abeb7685c742478a7be0f4827c7cef"
MODEL = "deepseek-chat"

def convert_to_mla(reference: str) -> str:
    prompt = f"""
Ты — эксперт по оформлению библиографических ссылок согласно стандарту MLA.
Преобразуй данную библиографическую ссылку в корректное оформление по MLA в одном предложении, используя следующий точный шаблон:
Author. "Title of Article." Title of Periodical, vol. number, no. number, Year, pp. pages. [DOI/URL]
Выведи только окончательный результат в виде одной строки без дополнительных пояснений.
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

if __name__ == "__main__":
    test_reference = "Smith, J., Advances in AI, Journal of Modern Science, 2020, vol. 10, no. 2, pp. 123-130"
    result = convert_to_mla(test_reference)
    print("Результат конвертации в MLA:")
    print(result)
