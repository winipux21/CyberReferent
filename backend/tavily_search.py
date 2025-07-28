#backend/tavily_search
import os
from tavily import TavilyClient
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY не найден в переменных окружения.")

client = TavilyClient(api_key=TAVILY_API_KEY)

async def search_reference(query: str) -> str:
    """
    Выполняет поиск через Tavily по заданному запросу и возвращает первый релевантный URL.
    """
    try:
        response = client.search(query=query, search_depth="basic", max_results=1)
        if response.get("results") and len(response["results"]) > 0:
            url = response["results"][0]["url"]
            logger.info(f"Найден URL через Tavily: {url}")
            return url
        else:
            logger.warning(f"Результаты поиска для '{query}' не найдены.")
            return None
    except Exception as e:
        logger.error(f"Ошибка при поиске через Tavily: {e}")
        return None