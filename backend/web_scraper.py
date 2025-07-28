# backend/web_scraper.py

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
import pyparsing as pp
from playwright.async_api import async_playwright
import openai
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY не найден в переменных окружения.")

MODEL = "deepseek-chat"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_year_with_pyparsing(text: str) -> str:
    """Извлекает год из текста с помощью pyparsing."""
    year_expr = pp.Word(pp.nums, exact=4)
    try:
        result = year_expr.searchString(text)
        if result:
            return result[0][0]
    except Exception:
        pass
    return "Не указано"

def extract_with_neural_network(full_text: str, url: str) -> dict:
    """Извлекает библиографические данные с помощью нейросети DeepSeek."""
    logger.info("Передача текста в нейросеть для обработки (первые 6000 символов)")
    prompt = f"""Ты — эксперт по извлечению библиографических данных из текста веб-страниц.
    Проанализируй текст страницы и извлеки следующие данные:
    - Название статьи (title)
    - Автор(ы) (author)
    - Редактор(ы) (editor)
    - Год публикации (year)
    - Название журнала (journal)
    - Том (volume)
    - Номер (number)
    - Страницы (pages)
    - DOI (doi)
    - URL (уже известен: {url})
    - Издатель (publisher)
    - Место издания (address)
    - Месяц публикации (month)
    - День публикации (day)
    - Примечание (note, например, дата обращения или 'в печати')

    Если каких-то данных нет, укажи "Не указано".
    Пример для Springer:
    Текст: "On an integral representation of the Neumann—Tricomi problem for the Lavrent’ev–Bitsadze equation Moiseev, E. I., Moiseev, T. E., Vafodorova, G. O. Differential Equations Volume 51, Issue 8, August 2015, Pages 1086–1091 DOI: 10.1134/S0012266115080108 Pleiades Publishing"
    Результат:
    title: On an integral representation of the Neumann—Tricomi problem for the Lavrent’ev–Bitsadze equation
    author: Moiseev, E. I., Moiseev, T. E., Vafodorova, G. O.
    editor: Не указано
    year: 2015
    journal: Differential Equations
    volume: 51
    number: 8
    pages: 1086–1091
    doi: 10.1134/S0012266115080108
    url: {url}
    publisher: Pleiades Publishing
    address: Не указано
    month: August
    day: Не указано
    note: Не указано

    Текст страницы:
    "{full_text[:20000]}" """
    
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=150
        )
        result = response.choices[0].message.content.strip()
        logger.info("Нейросеть вернула результат: %s", result)

        # Парсим результат нейросети
        data = {
            "title": "Не указано", "author": "Не указано", "editor": "Не указано",
            "year": "Не указано", "journal": "Не указано", "volume": "Не указано",
            "number": "Не указано", "pages": "Не указано", "doi": "Не указано",
            "url": url, "publisher": "Не указано", "address": "Не указано",
            "month": "Не указано", "day": "Не указано", "note": "Не указано"
        }
        lines = result.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("- **") or line.startswith("- "):
                cleaned_line = line.replace("- **", "").replace("- ", "").replace("**", "").strip()
                try:
                    key, value = cleaned_line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key in data:
                        data[key] = value
                except Exception as e:
                    logger.error("Ошибка парсинга строки '%s': %s", line, str(e))
        logger.info("Извлеченные данные нейросетью: %s", data)
        return data
    except Exception as e:
        logger.error("Ошибка при работе с нейросетью: %s", str(e))
        raise ValueError(f"Ошибка нейросети: {e}")

async def extract_bibliographic_data(url: str) -> dict:
    """Извлекает библиографические данные из веб-страницы асинхронно."""
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/108.0.0.0 Safari/537.36")
    }

    # Проверяем, является ли URL страницей авторизации с redirect_uri
    parsed_url = urlparse(url)
    if "idp.springer.com/authorize" in url:
        query_params = parse_qs(parsed_url.query)
        redirect_uri = query_params.get("redirect_uri", [None])[0]
        if redirect_uri:
            url = unquote(redirect_uri)
            logger.info("Извлечен redirect_uri: %s", url)
        else:
            logger.error("redirect_uri не найден в URL: %s", url)
            raise ValueError("Ошибка: redirect_uri не найден в URL авторизации")

    # Сначала пытаемся через Playwright + нейросеть
    logger.info("Попытка извлечения данных с помощью Playwright и нейросети для URL: %s", url)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            # Следим за редиректами
            response = await page.goto(url, timeout=40000, wait_until="domcontentloaded")
            final_url = response.url if response else url
            await page.wait_for_timeout(2000)  # Ожидание загрузки динамического контента
            full_text = await page.content()
            await browser.close()
            logger.info("Страница успешно загружена через Playwright, final URL: %s", final_url)

        neural_data = extract_with_neural_network(BeautifulSoup(full_text, "html.parser").get_text(separator=" ", strip=True), url)
        if any(neural_data[key] != "Не указано" for key in ["title", "author", "year", "journal", "publisher"]):
            logger.info("Нейросеть успешно извлекла данные: %s", neural_data)
            return neural_data
        else:
            logger.warning("Нейросеть вернула пустые данные, переход к классическому парсеру")
    except Exception as e:
        logger.error("Ошибка в блоке Playwright/нейросети: %s", str(e))

    # Fallback: классический парсер
    logger.info("Переход к классическому парсеру для URL: %s", url)
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except Exception as e:
        logger.error("Ошибка при загрузке страницы через requests: %s", str(e))
        raise ValueError(f"Ошибка при получении страницы: {e}")

    soup = BeautifulSoup(response.text, "html.parser")
    full_text = soup.get_text(separator=" ", strip=True)

    # Специфичная обработка для eLibrary
    if "elibrary.ru" in url:
        logger.info("Обработка данных для eLibrary")
        title_tag = soup.select_one("h1[itemprop='name']") or soup.find("h1") or soup.select_one("div#thepage > h1")
        title = title_tag.text.strip() if title_tag else "Не указано"
        if title == "Не указано":
            meta_title = soup.find("meta", property="og:title")
            title = meta_title["content"].strip() if meta_title and meta_title.get("content") else "Не указано"
            if title == "Не указано":
                title_match = re.search(r"^[А-ЯЁ\s\d\w\-\(\):]+(?=\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.)", full_text)
                title = title_match.group(0).strip() if title_match else "Не указано"
        logger.info("Название статьи: %s", title)

        author_tag = soup.find("div", class_="bibrec-authors")
        author = ", ".join([a.text.strip() for a in author_tag.find_all("a") if a.text.strip()]) if author_tag else "Не указано"
        if author == "Не указано":
            author_match = re.search(r"([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\..*?)(?=\d\s+|$)", full_text)
            author = author_match.group(1).strip() if author_match else "Не указано"
        logger.info("Авторы: %s", author)

        editor = "Не указано"  # eLibrary не предоставляет данные о редакторах
        logger.info("Редактор: %s", editor)

        year_match = re.search(r"Год:\s*(\d{4})", full_text)
        year = year_match.group(1) if year_match else extract_year_with_pyparsing(full_text)
        logger.info("Год: %s", year)

        journal_tag = soup.find("a", href=re.compile(r"/title_about\.asp\?id=\d+"))
        journal = journal_tag.text.strip() if journal_tag else "Не указано"
        logger.info("Журнал: %s", journal)

        volume_match = re.search(r"Т\.?\s*(\d+)", full_text)
        volume = volume_match.group(1) if volume_match else "Не указано"
        logger.info("Том: %s", volume)

        number_match = re.search(r"№\s*(\d+)", full_text)
        number = number_match.group(1) if number_match else "Не указано"
        logger.info("Номер: %s", number)

        pages_match = re.search(r"С\.?\s*(\d+\s*[-–]\s*\d+)", full_text)
        pages = pages_match.group(1) if pages_match else "Не указано"
        logger.info("Страницы: %s", pages)

        doi_match = re.search(r"DOI:\s*([^\s]+)", full_text)
        doi = doi_match.group(1) if doi_match else "Не указано"
        logger.info("DOI: %s", doi)

        publisher = urlparse(url).netloc if journal == "Не указано" else "Не указано"
        logger.info("Издатель: %s", publisher)

        address = "Не указано"  # eLibrary не предоставляет данные о месте издания
        month = "Не указано"
        day = "Не указано"
        note = "Не указано"
        logger.info("Место: %s, Месяц: %s, День: %s, Примечание: %s", address, month, day, note)

        return {
            "title": title, "author": author, "editor": editor, "year": year, "journal": journal,
            "volume": volume, "number": number, "pages": pages, "doi": doi, "url": url,
            "publisher": publisher, "address": address, "month": month, "day": day, "note": note
        }

    # Специфичная обработка для Springer
    if "springer.com" in url:
        logger.info("Обработка данных для Springer")
        title = (soup.find("meta", attrs={"name": "citation_title"})["content"].strip() if soup.find("meta", attrs={"name": "citation_title"}) and soup.find("meta", attrs={"name": "citation_title"}).get("content") else
                 soup.find("meta", property="og:title")["content"].strip() if soup.find("meta", property="og:title") and soup.find("meta", property="og:title").get("content") else
                 soup.title.string.strip() if soup.title and soup.title.string else "Не указано")
        logger.info("Название статьи: %s", title)

        author_tags = soup.find_all("meta", attrs={"name": "citation_author"})
        author = (", ".join([tag["content"].strip() for tag in author_tags if tag.get("content")]) if author_tags else
                  soup.find("meta", attrs={"name": "author"})["content"].strip() if soup.find("meta", attrs={"name": "author"}) and soup.find("meta", attrs={"name": "author"}).get("content") else
                  "Не указано")
        logger.info("Авторы: %s", author)

        editor = "Не указано"
        logger.info("Редактор: %s", editor)

        year = "Не указано"
        date_tag = soup.find("meta", attrs={"name": "citation_publication_date"})
        if date_tag and date_tag.get("content"):
            date_content = date_tag["content"].strip()
            year = date_content[:4] if re.match(r'\d{4}', date_content) else date_content
        else:
            date_tag = soup.find("meta", property="article:published_time")
            if date_tag and date_tag.get("content"):
                try:
                    pub_date = datetime.fromisoformat(date_tag["content"].strip())
                    year = str(pub_date.year)
                except Exception:
                    year = extract_year_with_pyparsing(full_text)
        logger.info("Год: %s", year)

        journal = (soup.find("meta", attrs={"name": "citation_journal_title"})["content"].strip() if soup.find("meta", attrs={"name": "citation_journal_title"}) and soup.find("meta", attrs={"name": "citation_journal_title"}).get("content") else
                   "Не указано")
        logger.info("Журнал: %s", journal)

        volume = (soup.find("meta", attrs={"name": "citation_volume"})["content"].strip() if soup.find("meta", attrs={"name": "citation_volume"}) and soup.find("meta", attrs={"name": "citation_volume"}).get("content") else
                  "Не указано")
        logger.info("Том: %s", volume)

        number = (soup.find("meta", attrs={"name": "citation_issue"})["content"].strip() if soup.find("meta", attrs={"name": "citation_issue"}) and soup.find("meta", attrs={"name": "citation_issue"}).get("content") else
                  "Не указано")
        logger.info("Номер: %s", number)

        # Поиск страниц в тексте страницы
        pages = "Не указано"
        pages_tag = soup.find("meta", attrs={"name": "citation_pages"})
        if pages_tag and pages_tag.get("content"):
            pages = pages_tag["content"].strip()
        else:
            # Поиск в тексте (например, в <div class="c-bibliographic-information__value">)
            pages_elem = soup.select_one("div.c-bibliographic-information__value")
            if pages_elem:
                pages_text = pages_elem.text.strip()
                pages_match = re.search(r"(\d+\s*[-–]\s*\d+)", pages_text)
                pages = pages_match.group(1) if pages_match else "Не указано"
            else:
                # Поиск через регулярное выражение в полном тексте
                pages_match = re.search(r"Pages\s*(\d+\s*[-–]\s*\d+)", full_text, re.IGNORECASE)
                pages = pages_match.group(1) if pages_match else "Не указано"
        logger.info("Страницы: %s", pages)

        doi = (soup.find("meta", attrs={"name": "citation_doi"})["content"].strip() if soup.find("meta", attrs={"name": "citation_doi"}) and soup.find("meta", attrs={"name": "citation_doi"}).get("content") else
               "Не указано")
        logger.info("DOI: %s", doi)

        publisher = (soup.find("meta", attrs={"name": "citation_publisher"})["content"].strip() if soup.find("meta", attrs={"name": "citation_publisher"}) and soup.find("meta", attrs={"name": "citation_publisher"}).get("content") else
                     soup.find("meta", property="og:site_name")["content"].strip() if soup.find("meta", property="og:site_name") and soup.find("meta", property="og:site_name").get("content") else
                     urlparse(url).netloc)
        logger.info("Издатель: %s", publisher)

        address = "Не указано"
        month = "Не указано"
        day = "Не указано"
        try:
            if date_tag and date_tag.get("content"):
                pub_date = datetime.fromisoformat(date_tag["content"].strip())
                month = pub_date.strftime("%B")
                day = str(pub_date.day)
        except Exception:
            pass
        logger.info("Месяц: %s, День: %s", month, day)

        note = "Не указано"
        logger.info("Примечание: %s", note)

        return {
            "title": title, "author": author, "editor": editor, "year": year, "journal": journal,
            "volume": volume, "number": number, "pages": pages, "doi": doi, "url": url,
            "publisher": publisher, "address": address, "month": month, "day": day, "note": note
        }

    # Общий парсер для других сайтов
    logger.info("Обработка данных через общий парсер")
    citation_title = soup.find("meta", attrs={"name": "citation_title"})
    title = (citation_title["content"].strip() if citation_title and citation_title.get("content") else
             soup.find("meta", property="og:title")["content"].strip() if soup.find("meta", property="og:title") and soup.find("meta", property="og:title").get("content") else
             soup.title.string.strip() if soup.title and soup.title.string else "Не указано")
    logger.info("Название статьи: %s", title)

    author_tags = soup.find_all("meta", attrs={"name": "citation_author"})
    author = (", ".join([tag["content"].strip() for tag in author_tags if tag.get("content")]) if author_tags else
              soup.find("meta", attrs={"name": "author"})["content"].strip() if soup.find("meta", attrs={"name": "author"}) and soup.find("meta", attrs={"name": "author"}).get("content") else
              "Не указано")
    logger.info("Авторы: %s", author)

    editor = "Не указано"
    logger.info("Редактор: %s", editor)

    year = "Не указано"
    date_tag = soup.find("meta", attrs={"name": "citation_publication_date"})
    if date_tag and date_tag.get("content"):
        date_content = date_tag["content"].strip()
        year = date_content[:4] if re.match(r'\d{4}', date_content) else date_content
    else:
        date_tag = soup.find("meta", property="article:published_time")
        if date_tag and date_tag.get("content"):
            try:
                pub_date = datetime.fromisoformat(date_tag["content"].strip())
                year = str(pub_date.year)
            except Exception:
                year = extract_year_with_pyparsing(full_text)
    logger.info("Год: %s", year)

    journal = (soup.find("meta", attrs={"name": "citation_journal_title"})["content"].strip() if soup.find("meta", attrs={"name": "citation_journal_title"}) and soup.find("meta", attrs={"name": "citation_journal_title"}).get("content") else
               "Не указано")
    logger.info("Журнал: %s", journal)

    volume = (soup.find("meta", attrs={"name": "citation_volume"})["content"].strip() if soup.find("meta", attrs={"name": "citation_volume"}) and soup.find("meta", attrs={"name": "citation_volume"}).get("content") else
              "Не указано")
    logger.info("Том: %s", volume)

    number = (soup.find("meta", attrs={"name": "citation_issue"})["content"].strip() if soup.find("meta", attrs={"name": "citation_issue"}) and soup.find("meta", attrs={"name": "citation_issue"}).get("content") else
              "Не указано")
    logger.info("Номер: %s", number)

    pages = (soup.find("meta", attrs={"name": "citation_pages"})["content"].strip() if soup.find("meta", attrs={"name": "citation_pages"}) and soup.find("meta", attrs={"name": "citation_pages"}).get("content") else
             "Не указано")
    logger.info("Страницы: %s", pages)

    doi = (soup.find("meta", attrs={"name": "citation_doi"})["content"].strip() if soup.find("meta", attrs={"name": "citation_doi"}) and soup.find("meta", attrs={"name": "citation_doi"}).get("content") else
           "Не указано")
    logger.info("DOI: %s", doi)

    publisher = (soup.find("meta", attrs={"name": "citation_publisher"})["content"].strip() if soup.find("meta", attrs={"name": "citation_publisher"}) and soup.find("meta", attrs={"name": "citation_publisher"}).get("content") else
                 soup.find("meta", property="og:site_name")["content"].strip() if soup.find("meta", property="og:site_name") and soup.find("meta", property="og:site_name").get("content") else
                 urlparse(url).netloc)
    logger.info("Издатель: %s", publisher)

    address = "Не указано"
    month = "Не указано"
    day = "Не указано"
    try:
        if date_tag and date_tag.get("content"):
            pub_date = datetime.fromisoformat(date_tag["content"].strip())
            month = pub_date.strftime("%B")
            day = str(pub_date.day)
    except Exception:
        pass
    logger.info("Месяц: %s, День: %s", month, day)

    note = "Не указано"
    logger.info("Примечание: %s", note)

    return {
        "title": title, "author": author, "editor": editor, "year": year, "journal": journal,
        "volume": volume, "number": number, "pages": pages, "doi": doi, "url": url,
        "publisher": publisher, "address": address, "month": month, "day": day, "note": note
    }

def format_reference_with_ai(data: dict, style: str, subformat: str) -> str:
    """Формирует библиографическую запись с помощью нейросети в указанном стиле и подтипе, возвращая только чистую ссылку."""
    prompt_templates = {
        "APA": {
            "Журнальная статья": """Ты — эксперт по оформлению ссылок по APA (7th edition). Отформатируй данные в Журнальная статья по стандарту APA. Верни только готовую ссылку без пояснений и примечаний. Название журнала должно быть в курсиве, том и номер — в обычном шрифте. Если страницы отсутствуют, не включай их. Если есть DOI, используй его; иначе используй URL, если он есть.
            Данные: {data}
            Пример: Moiseev, E. I., Moiseev, T. E., & Vafodorova, G. O. (2015). On an integral representation of the Neumann—Tricomi problem for the Lavrent’ev–Bitsadze equation. *Differential Equations*, 51(8), 1086–1091. https://doi.org/10.1134/S0012266115080108""",
            "Онлайн-журнал": """Ты — эксперт по оформлению ссылок по APA. Отформатируй данные в Онлайн-журнал по стандарту APA. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев, С. В. (2015). Почти контактные метрические структуры. *Математические заметки СВФУ*, (1), 45–50. Retrieved from http://example.com""",
            "Сетевое издание": """Ты — эксперт по оформлению ссылок по APA. Отформатируй данные в Сетевое издание по стандарту APA. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев, С. В. (2015, January 1). Почти контактные метрические структуры. *Наука Сегодня*. Retrieved from http://example.com""",
            "Книга": """Ты — эксперт по оформлению ссылок по APA. Отформатируй данные в Книга по стандарту APA. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев, С. В. (2015). Почти контактные метрические структуры. Москва: Наука"""
        },
        "GOST": {
            "Статья в журнале": """Ты — эксперт по ГОСТ Р 7.0.100-2018. Отформатируй данные в Статья в журнале по ГОСТ. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев С.В. Почти контактные метрические структуры, определяемые N-продолженной связностью // Математические заметки СВФУ. 2015. Т. 2. № 1. С. 45–50. DOI: 10.1234/example""",
            "Книга": """Ты — эксперт по ГОСТ Р 7.0.100-2018. Отформатируй данные в Книга по ГОСТ. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев С.В. Почти контактные метрические структуры. М.: Наука, 2015. 200 с.""",
            "Материалы конференций": """Ты — эксперт по ГОСТ Р 7.0.100-2018. Отформатируй данные в Материалы конференций по ГОСТ. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Почти контактные метрические структуры / под ред. С.В. Галаева. М.: Наука, 2015. 200 с.""",
            "Статья в печати": """Ты — эксперт по ГОСТ Р 7.0.100-2018. Отформатируй данные в Статья в печати по ГОСТ. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев С.В. Почти контактные метрические структуры // Математические заметки СВФУ. 2015. Т. 2. № 1 (в печати)""",
            "Онлайн-статья": """Ты — эксперт по ГОСТ Р 7.0.100-2018. Отформатируй данные в Онлайн-статья по ГОСТ. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев С.В. Почти контактные метрические структуры // Математические заметки СВФУ. 2015. URL: http://example.com (дата обращения: 01.01.2025)"""
        },
        "MLA": {
            "Журнальная статья": """Ты — эксперт по MLA. Отформатируй данные в Журнальная статья по стандарту MLA. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев, Сергей Васильевич. "Почти контактные метрические структуры, определяемые N-продолженной связностью." *Математические заметки СВФУ*, т. 2, № 1, 2015, с. 45–50. doi:10.1234/example""",
            "Интернет-журнал": """Ты — эксперт по MLA. Отформатируй данные в Интернет-журнал по стандарту MLA. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев, Сергей Васильевич. "Почти контактные метрические структуры." *Математические заметки СВФУ*, т. 2, 2015, с. 45–50. http://example.com""",
            "Статья в онлайн-СМИ": """Ты — эксперт по MLA. Отформатируй данные в Статья в онлайн-СМИ по стандарту MLA. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев, Сергей Васильевич. "Почти контактные метрические структуры." *Наука Сегодня*, 1 января 2015, http://example.com""",
            "Монография": """Ты — эксперт по MLA. Отформатируй данные в Монография по стандарту MLA. Верни только готовую ссылку без пояснений и примечаний.
            Данные: {data}
            Пример: Галаев, Сергей Васильевич. *Почти контактные метрические структуры*. Москва, Наука, 2015"""
        }
    }

    style = style.upper()
    format_dict = prompt_templates.get(style)
    if not format_dict:
        logger.error("Неверный стиль: %s", style)
        return "Ошибка: неверный стиль (допустимые: APA, GOST, MLA)."

    prompt = format_dict.get(subformat)
    if not prompt:
        logger.error("Неверный подтип для стиля %s: %s", style, subformat)
        return f"Ошибка: неверный подтип для {style}."

    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt.format(data=data)}],
            temperature=0.1,
            timeout=150
        )
        formatted_reference = response.choices[0].message.content.strip()
        logger.info("Сформированная запись в стиле %s, подтип %s: %s", style, subformat, formatted_reference)
        return formatted_reference
    except Exception as e:
        logger.error("Ошибка при работе с нейросетью: %s", str(e))
        return f"Ошибка AI-сервиса: {e}"

def compose_reference(data: dict, style: str = "APA", subformat: str = None) -> str:
    """Формирует библиографическую запись в указанном стиле и подтипе."""
    if not subformat:
        logger.error("Подтип не указан, требуется выбор подформата")
        return "Ошибка: подтип не указан (например, Журнальная статья, Книга и т.д.)."
    
    return format_reference_with_ai(data, style, subformat)