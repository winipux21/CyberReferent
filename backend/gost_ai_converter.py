"""
gost_ai_converter.py

Модуль для преобразования библиографической ссылки в корректное оформление по стандарту ГОСТ Р 7.0.100-2018 в виде одной строки.
Структура результата:
Автор И.О. Название статьи // Название журнала. – Год. – Т. X. – № Y. – С. Z–Z. – ISSN/ISBN XXXX-XXXX.
"""

import openai

DEEPSEEK_API_KEY = "sk-15abeb7685c742478a7be0f4827c7cef"
MODEL = "deepseek-chat"

def convert_to_gost(reference: str) -> str:
    prompt = f"""
Ты — эксперт по оформлению библиографических ссылок согласно стандарту ГОСТ Р 7.0.100-2018.
Преобразуй данную библиографическую ссылку в корректное оформление по ГОСТ в одном предложении, используя следующий точный шаблон:
Автор И.О. Название статьи // Название журнала. – Год. – Т. X. – № Y. – С. Z–Z. – ISSN/ISBN XXXX-XXXX.
Выведи только окончательный результат в виде одной строки без дополнительных пояснений.
Ссылка пользователя:
"{reference}"
"""
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка при вызове нейросетевого сервиса: {e}"

if __name__ == "__main__":
    test_reference = "Петров 2020, стр. 15"
    result = convert_to_gost(test_reference)
    print("Результат конвертации в ГОСТ:")
    print(result)
