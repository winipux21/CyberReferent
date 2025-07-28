# backend/mla_ai_converter.py
import os
import openai
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY не найден в переменных окружения.")

MODEL = "deepseek-chat"

def convert_to_mla(reference: str) -> str:
    prompt = f"""
Ты — эксперт по оформлению библиографических ссылок согласно стандарту MLA (русская версия).
Преобразуй данную библиографическую запись в корректное оформление по стандарту MLA, используя следующий точный шаблон (все данные на русском языке):
Фамилия, Имя. «Название статьи.» Название журнала, том, №, год, pp. страницы. [DOI/URL]
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
