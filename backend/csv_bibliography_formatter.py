# csv_bibliography_formatter.py — формирование компактного CSV
# ────────────────────────────────────────────────────────────
#  Никаких «пустых запятых»: выводятся только заполненные поля.
# ────────────────────────────────────────────────────────────
import openai
import csv
import io
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY не найден в переменных окружения.")

MODEL = "deepseek-chat"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)



PROMPT = (
    "Ты — эксперт по библиографии. Извлеки максимум данных из записи и "
    "верни их в формате «ключ: значение» (каждая пара — с новой строки). "
    "Ключи: author, editor, title, journal, volume, number, year, pages, "
    "publisher, address, url, doi, month, day, note. "
    "Пропусти пары без значения.\n"
    "Запись: \"{reference}\""
)

# исходный порядок столбцов
CSV_FIELDS = ["author", "editor", "title", "journal", "volume", "number",
              "year", "pages", "publisher", "address", "url", "doi",
              "month", "day", "note"]


def _llm_extract(reference: str) -> dict:
    """Запрашиваем LLM → получаем словарь заполненных полей."""
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY,
                           base_url="https://api.deepseek.com/v1")
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT.format(reference=reference)}],
        temperature=0.1,
        timeout=180
    )
    raw = resp.choices[0].message.content.strip()
    logger.info("LLM raw:\n%s", raw)

    data = {}
    for line in raw.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            data[k.strip()] = v.strip()
    return data


def format_reference_to_csv(reference: str) -> str:
    """Возвращает CSV‑строку (UTF‑8, без пустых ячеек)."""
    data = _llm_extract(reference)
    filled_fields = [f for f in CSV_FIELDS if data.get(f)]

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(filled_fields)
    writer.writerow([data[f] for f in filled_fields])

    csv_str = output.getvalue()
    logger.info("CSV ready:\n%s", csv_str)
    return csv_str
