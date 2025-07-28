# backend/apa_ai_converter.py
import openai
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY не найден в переменных окружения.")

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
