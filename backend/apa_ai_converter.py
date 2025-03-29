"""
apa_ai_converter.py

Модуль для преобразования библиографической ссылки в корректное оформление по стандарту APA в виде одной строки.
Структура результата (для книг): 
Автор, И. О. (ред.). (Год). Название работы. Город: Издательство. (Количество страниц pp.). ISBN XXXXXXXXXXXXX.
"""

import openai

DEEPSEEK_API_KEY = "sk-15abeb7685c742478a7be0f4827c7cef"
MODEL = "deepseek-chat"

def convert_to_apa(reference: str) -> str:
    prompt = f"""
Ты — эксперт по оформлению библиографических ссылок согласно стандарту APA.
Преобразуй данную библиографическую ссылку в корректное оформление по APA в одном предложении, используя следующий точный шаблон:
Автор, И. О. (ред.). (Год). Название работы. Город: Издательство. (Количество страниц pp.). ISBN XXXXXXXXXXXXX.
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
    test_reference = "3. Экономика и управление: Учебник / Под ред. А. А. Смирнова. — М.: Просвещение, 2018. — 400 с. ISBN 9781231234213"
    result = convert_to_apa(test_reference)
    print("Результат конвертации в APA:")
    print(result)
