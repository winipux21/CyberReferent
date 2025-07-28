#frontend/app.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import requests
import json
import csv
import io
import re
import logging
from typing import List
import openpyxl
from openpyxl.styles import Font, Alignment
from backend.field_extractor import extract_fields

# Базовые константы
BACKEND_URL = "http://127.0.0.1:8000"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация session_state
defaults = {
    "conversion_result": None,
    "warnings": None,
    "reference_input": "",
    "scraped_reference": "",
    "scraped_csv": "",
    "converter_result_multi": None,
    "original_fields": {},
    "converted_fields": {}
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Настройка страницы
st.set_page_config(page_title="Cyber-Referent", layout="wide", initial_sidebar_state="collapsed")
st.title("🎓 Cyber-Referent")

# Стилизация
st.markdown(
    """
    <style>
    .main { background-color: #f5f5f5; padding: 20px; border-radius: 10px; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 5px; }
    .stTextArea textarea { border: 2px solid #4CAF50; border-radius: 5px; }
    .stSelectbox { margin-bottom: 15px; }
    .warning { color: #FF9800; font-style: italic; }
    </style>
    """,
    unsafe_allow_html=True
)

# Справочные структуры
structures_full = {
    "GOST": (
        "Статья в журнале: Фамилия И.О. Название статьи // Журнал. Год. Т. X. № Y. С. Z–Z. DOI/URL\n"
        "Книга: Фамилия И.О. Название. Место: Издательство, Год. Кол-во страниц\n"
        "Материалы конференций: Название / под ред. Фамилия И.О. Место: Издательство, Год. Кол-во страниц\n"
        "Статья в печати: Фамилия И.О. Название // Журнал. Год. Т. X. № Y (в печати)\n"
        "Онлайн-статья: Фамилия И.О. Название // Журнал. Год. URL: ... (дата обращения: ДД.ММ.ГГГГ)"
    ),
    "APA": (
        "Журнальная статья: Фамилия, И. О., & Фамилия, И. О. (Год). Название статьи. Название журнала, том(номер), страницы. DOI\n"
        "Онлайн-журнал: Фамилия, И. О., & Фамилия, И. О. (Год). Название статьи. Название журнала, (номер), страницы. Retrieved from URL\n"
        "Сетевое издание: Фамилия, И. О. (Год, Month Day). Название статьи. Название сайта. Retrieved from URL\n"
        "Книга: Фамилия, И. О., & Фамилия, И. О. (Год). Название книги. Город: Издательство"
    ),
    "MLA": (
        'Журнальная статья: Фамилия, Имя и Имя Фамилия. "Название статьи." Название журнала, т. X, № Y, Год, с. Z–Z. DOI/URL\n'
        'Интернет-журнал: Фамилия, Имя. "Название статьи." Название журнала, т. X, Год, с. Z–Z. URL\n'
        'Статья в онлайн-СМИ: Фамилия, Имя. "Название статьи." Название сайта, День Месяц Год, URL\n'
        'Монография: Фамилия, Имя. Название книги. Место, Издательство, Год'
    )
}

target_structures = {
    "APA": {
        "Журнальная статья": "Фамилия, И. О., & Фамилия, И. О. (Год). Название статьи. Название журнала, том(номер), страницы. DOI",
        "Онлайн-журнал": "Фамилия, И. О. (Год). Название статьи. Название журнала, (номер), страницы. Retrieved from URL",
        "Сетевое издание": "Фамилия, И. О. (Год, Month Day). Название статьи. Название сайта. Retrieved from URL",
        "Книга": "Фамилия, И. О. (Год). Название книги. Город: Издательство"
    },
    "GOST": {
        "Статья в журнале": "Фамилия И.О. Название статьи // Журнал. Год. Т. X. № Y. С. Z–Z. DOI/URL",
        "Книга": "Фамилия И.О. Название. Место: Издательство, Год. Кол-во страниц",
        "Материалы конференций": "Название / под ред. Фамилия И.О. Место: Издательство, Год. Кол-во страниц",
        "Статья в печати": "Фамилия И.О. Название // Журнал. Год. Т. X. № Y (в печати)",
        "Онлайн-статья": "Фамилия И.О. Название // Журнал. Год. URL: ... (дата обращения: ДД.ММ.ГГГГ)"
    },
    "MLA": {
        "Журнальная статья": 'Фамилия, Имя и Имя Фамилия. "Название статьи." Название журнала, т. X, № Y, Год, с. Z–Z. DOI/URL',
        "Интернет-журнал": 'Фамилия, Имя. "Название статьи." Название журнала, т. X, Год, с. Z–Z. URL',
        "Статья в онлайн-СМИ": 'Фамилия, Имя. "Название статьи." Название сайта, День Месяц Год, URL',
        "Монография": "Фамилия, Имя. Название книги. Место, Издательство, Год"
    }
}

subformat_opts = {
    "APA": ["Журнальная статья", "Онлайн-журнал", "Сетевое издание", "Книга"],
    "GOST": ["Статья в журнале", "Книга", "Материалы конференций", "Статья в печати", "Онлайн-статья"],
    "MLA": ["Журнальная статья", "Интернет-журнал", "Статья в онлайн-СМИ", "Монография"]
}

def create_excel_file(converted_references: List[dict], source_format: str, target_format: str, target_subformat: str) -> bytes:
    """Создает Excel-файл с результатами конвертации для нескольких ссылок."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Conversion Results"

    # Заголовки
    headers = ["Original Reference", "Converted Reference", "Source Format", "Target Format", "Target Subformat"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True)

    # Данные
    for idx, item in enumerate(converted_references, start=2):
        ws.append([
            item["original"],
            item.get("converted", item.get("error", "Ошибка")),
            source_format,
            target_format,
            target_subformat
        ])

    # Автонастройка ширины колонок
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)  # Ограничение ширины
        ws.column_dimensions[column].width = adjusted_width

    # Сохранение в байтовый поток
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

# Главный селектор режима
mode = st.radio("Выберите режим работы:",
                ["Проверка ссылок", "Конвертер ссылок", "Сбор данных по ссылке", "Конвертер в TeX формате"],
                horizontal=True)

# 1. Проверка ссылок
if mode == "Проверка ссылок":
    st.header("✔️ Проверка ссылок")

    method = st.radio("Выберите способ проверки:", ["📄 Файл PDF/DOCX", "📝 Текст списка литературы"], key="check_method")

    st.subheader("⚙️ Настройки")
    style = st.selectbox("Выберите формат оформления:", ["GOST", "APA", "MLA"], key="check_style")
    subformat = st.selectbox("Выберите тип записи:", subformat_opts[style], key="check_subformat")

    st.markdown("**Ожидаемая структура:**")
    st.code(structures_full[style], language="text")

    if method == "📄 Файл PDF/DOCX":
        uploaded_file = st.file_uploader("Выберите файл:", ['pdf', 'docx'], key="file_uploader")
        if st.button("Проверить файл", key="check_file"):
            if not uploaded_file:
                st.error("Файл не выбран.")
            else:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                payload = {"style": style, "subformat": subformat}
                valid_results: List[str] = []
                invalid_results: List[dict] = []

                with st.spinner("⏳ Обработка файла..."):
                    try:
                        resp = requests.post(f"{BACKEND_URL}/check-file/", files=files, data=payload, stream=True, timeout=180)
                        resp.raise_for_status()
                        for raw in resp.iter_lines(decode_unicode=True):
                            if not raw:
                                continue
                            event = json.loads(raw.strip())
                            if event.get("type") == "valid":
                                valid_results.append(event["reference"])
                            elif event.get("type") == "invalid":
                                invalid_results.append(event)
                    except requests.RequestException as e:
                        st.error(f"Ошибка соединения: {e}. Попробуйте снова или проверьте подключение к серверу.")

                if valid_results:
                    st.markdown("### ✅ Валидные ссылки:")
                    for ref in valid_results:
                        st.success(ref)
                else:
                    st.markdown("### ✅ Валидные ссылки:")
                    st.info("Валидные ссылки не найдены.")

                if invalid_results:
                    st.markdown("### ⚠️ Ошибки и исправления:")
                    for item in invalid_results:
                        st.error(f"Оригинал: {item['original']}")
                        st.info(f"Анализ:\n{item['errors_and_corrections']}")
                        if item.get("corrected_reference") and item["corrected_reference"] != "Не удалось найти источник":
                            st.success(f"Исправленная ссылка (Tavily): {item['corrected_reference']}")
                        else:
                            st.warning("Источник не найден через Tavily.")

    elif method == "📝 Текст списка литературы":
        bibliography_text = st.text_area("Вставьте список литературы:", height=200, key="bib_text")
        if st.button("Проверить текст", key="check_text"):
            if not bibliography_text.strip():
                st.error("Текст не введён.")
            else:
                payload = {"bibliography_text": bibliography_text, "style": style, "subformat": subformat}
                valid_results: List[str] = []
                invalid_results: List[dict] = []

                with st.spinner("⏳ Обработка текста..."):
                    try:
                        resp = requests.post(f"{BACKEND_URL}/check-text/", data=payload, stream=True, timeout=180)
                        resp.raise_for_status()
                        for raw in resp.iter_lines(decode_unicode=True):
                            if not raw:
                                continue
                            event = json.loads(raw.strip())
                            if event.get("type") == "valid":
                                valid_results.append(event["reference"])
                            elif event.get("type") == "invalid":
                                invalid_results.append(event)
                    except requests.RequestException as e:
                        st.error(f"Ошибка соединения: {e}. Попробуйте снова или проверьте подключение к серверу.")

                if valid_results:
                    st.markdown("### ✅ Валидные ссылки:")
                    for ref in valid_results:
                        st.success(ref)
                else:
                    st.markdown("### ✅ Валидные ссылки:")
                    st.info("Валидные ссылки не найдены.")

                if invalid_results:
                    st.markdown("### ⚠️ Ошибки и исправления:")
                    for item in invalid_results:
                        st.error(f"Оригинал: {item['original']}")
                        st.info(f"Анализ:\n{item['errors_and_corrections']}")
                        if item.get("corrected_reference") and item["corrected_reference"] != "Не удалось найти источник":
                            st.success(f"Исправленная ссылка (Tavily): {item['corrected_reference']}")
                        else:
                            st.warning("Источник не найден через Tavily.")

# 2. Конвертер ссылок
elif mode == "Конвертер ссылок":
    st.header("🔄 Конвертер библиографической записи")

    method = st.radio("Выберите способ ввода:", ["📝 Текст списка литературы", "📄 Файл PDF/DOCX"], key="conv_method")

    st.subheader("⚙️ Настройки")
    source_format = st.selectbox("Исходный формат:", ["APA", "GOST", "MLA"], key="conv_source")
    st.markdown("**Ожидаемая структура исходного формата:**")
    st.code(structures_full[source_format], language="text")

    target_format = st.selectbox("Целевой формат:", ["APA", "GOST", "MLA"], key="conv_target")
    target_subformat = st.selectbox("Тип записи:", subformat_opts[target_format], key="conv_subformat")
    st.markdown("**Ожидаемая структура целевого формата:**")
    st.code(target_structures[target_format][target_subformat], language="text")

    if method == "📝 Текст списка литературы":
        st.subheader("✍️ Ввод списка литературы")
        bibliography_text = st.text_area("Вставьте список литературы (каждая запись с новой строки):", height=100, key="conv_text_multi")

        if st.button("Конвертировать", key="conv_button_multi_text"):
            if not bibliography_text.strip():
                st.error("Пожалуйста, введите список литературы.")
            else:
                payload = {
                    "bibliography_text": bibliography_text,
                    "source_format": source_format,
                    "target_format": target_format,
                    "target_subformat": target_subformat
                }
                with st.spinner("⏳ Конвертируем..."):
                    try:
                        resp = requests.post(f"{BACKEND_URL}/convert-references-text/", data=payload, timeout=180)
                        resp.raise_for_status()
                        st.session_state.converter_result_multi = resp.json()["converted_references"]
                    except requests.RequestException as e:
                        st.error(f"Ошибка соединения: {e}. Попробуйте снова или проверьте подключение к серверу.")

    elif method == "📄 Файл PDF/DOCX":
        st.subheader("📄 Загрузка файла")
        uploaded_file = st.file_uploader("Выберите файл:", ['pdf', 'docx'], key="conv_file_multi")

        if st.button("Конвертировать", key="conv_button_multi_file"):
            if not uploaded_file:
                st.error("Файл не выбран.")
            else:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                payload = {
                    "source_format": source_format,
                    "target_format": target_format,
                    "target_subformat": target_subformat
                }
                with st.spinner("⏳ Обработка файла..."):
                    try:
                        resp = requests.post(f"{BACKEND_URL}/convert-references-file/", files=files, data=payload, timeout=180)
                        resp.raise_for_status()
                        st.session_state.converter_result_multi = resp.json()["converted_references"]
                    except requests.RequestException as e:
                        st.error(f"Ошибка соединения: {e}. Попробуйте снова или проверьте подключение к серверу.")

    if st.session_state.converter_result_multi:
        st.subheader("✅ Результаты конвертации")
        for item in st.session_state.converter_result_multi:
            st.markdown(f"**Оригинал:** {item['original']}")
            if "converted" in item:
                st.markdown(f"**Конвертировано:** {item['converted']}")
            else:
                st.error(f"Ошибка: {item['error']}")

        out = io.StringIO()
        writer = csv.writer(out, lineterminator='\n')
        writer.writerow(["Original Reference", "Converted Reference"])
        for item in st.session_state.converter_result_multi:
            writer.writerow([item["original"], item.get("converted", item.get("error", "Ошибка"))])
        csv_bytes = ('\ufeff' + out.getvalue()).encode('utf-8')
        st.download_button("Скачать результаты в CSV", data=csv_bytes, 
                         file_name="converted_references.csv", mime="text/csv", 
                         key="conv_download_csv_multi")

        excel_bytes = create_excel_file(
            st.session_state.converter_result_multi,
            source_format,
            target_format,
            target_subformat
        )
        st.download_button("Скачать результаты в Excel", data=excel_bytes, 
                         file_name="converted_references.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         key="conv_download_excel_multi")

# 3. Сбор данных по ссылке
elif mode == "Сбор данных по ссылке":
    st.header("🤖 Сбор данных для библиографии по ссылке")

    url_input = st.text_input("URL страницы:", placeholder="https://example.com", key="scrape_url")
    style = st.selectbox("Формат оформления:", ["APA", "GOST", "MLA"], key="scrape_style")
    subformat = st.selectbox("Тип записи:", subformat_opts[style], key="scrape_subformat")
    st.code(target_structures[style][subformat], language="text")

    if st.button("Получить библиографическую запись", key="scrape_button"):
        if not url_input:
            st.error("Введите URL.")
        elif not re.match(r'^https?://[^\s]+$', url_input):
            st.error("Некорректный URL.")
        else:
            payload = {"url": url_input, "style": style, "subformat": subformat}
            with st.spinner("⏳ Собираем данные…"):
                try:
                    resp = requests.post(f"{BACKEND_URL}/scrape-reference/", data=payload, timeout=160)
                    resp.raise_for_status()
                    st.session_state.scraped_reference = resp.json().get("reference", "")
                except requests.Timeout:
                    st.error("Ошибка: запрос превысил время ожидания. Попробуйте использовать прямую ссылку на статью или проверьте подключение.")
                except requests.RequestException as e:
                    st.error(f"Ошибка соединения: {e}. Попробуйте снова или проверьте подключение к серверу.")

    if st.session_state.scraped_reference:
        st.success("Библиографическая запись:")
        st.code(st.session_state.scraped_reference, language="text")

        if st.button("Преобразовать в CSV", key="csv_button"):
            payload = {"reference": st.session_state.scraped_reference, "target_format": style, "subformat": subformat}
            with st.spinner("⏳ Генерируем CSV…"):
                try:
                    resp = requests.post(f"{BACKEND_URL}/convert-reference-csv/", data=payload, timeout=160)
                    resp.raise_for_status()
                    st.session_state.scraped_csv = resp.json()["csv"]
                except requests.RequestException as e:
                    st.error(f"Ошибка соединения: {e}. Попробуйте снова или проверьте подключение к серверу.")

    if st.session_state.scraped_csv:
        st.markdown("**CSV-запись:**")
        st.code(st.session_state.scraped_csv, language="text")
        csv_bytes = ("\ufeff" + st.session_state.scraped_csv).encode("utf-8")
        st.download_button("💾 Скачать CSV", data=csv_bytes, file_name="reference.csv", mime="text/csv", key="csv_download")

# 4. Конвертер в TeX формате
elif mode == "Конвертер в TeX формате":
    st.header("📚 Конвертер в BibTeX")

    method = st.radio("Выберите способ ввода:", ["📝 Текст списка литературы", "📄 Файл PDF/DOCX"], key="tex_method")

    st.subheader("⚙️ Настройки")
    target_format = st.selectbox("Выберите стиль:", ["APA", "GOST", "MLA"], key="tex_target")
    target_subformat = st.selectbox("Тип записи:", subformat_opts[target_format], key="tex_subformat")
    st.markdown("**Ожидаемая структура:**")
    st.code(target_structures[target_format][target_subformat], language="text")

    if method == "📝 Текст списка литературы":
        st.subheader("✍️ Ввод списка литературы")
        bibliography_text = st.text_area("Вставьте список литературы (каждая запись с новой строки):", height=200, key="tex_text_multi")

        if st.button("🔄 Конвертировать в BibTeX", key="tex_button_multi_text"):
            if not bibliography_text.strip():
                st.error("Пожалуйста, введите список литературы.")
            else:
                payload = {
                    "bibliography_text": bibliography_text,
                    "target_format": target_format,
                    "subformat": target_subformat
                }
                with st.spinner("⏳ Конвертируем в BibTeX..."):
                    try:
                        resp = requests.post(f"{BACKEND_URL}/convert-references-tex-text/", data=payload, timeout=180)
                        resp.raise_for_status()
                        st.session_state.conversion_result = resp.json()["bibtex"]
                    except requests.RequestException as e:
                        st.error(f"Ошибка соединения: {e}. Попробуйте снова или проверьте подключение к серверу.")

    elif method == "📄 Файл PDF/DOCX":
        st.subheader("📄 Загрузка файла")
        uploaded_file = st.file_uploader("Выберите файл:", ['pdf', 'docx'], key="tex_file_multi")

        if st.button("🔄 Конвертировать в BibTeX", key="tex_button_multi_file"):
            if not uploaded_file:
                st.error("Файл не выбран.")
            else:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                payload = {
                    "target_format": target_format,
                    "subformat": target_subformat
                }
                with st.spinner("⏳ Обработка файла..."):
                    try:
                        resp = requests.post(f"{BACKEND_URL}/convert-references-tex-file/", files=files, data=payload, timeout=180)
                        resp.raise_for_status()
                        st.session_state.conversion_result = resp.json()["bibtex"]
                    except requests.RequestException as e:
                        st.error(f"Ошибка соединения: {e}. Попробуйте снова или проверьте подключение к серверу.")

    if st.session_state.conversion_result:
        st.subheader("✅ Результат:")
        st.code(st.session_state.conversion_result, language="bibtex")
        st.download_button("💾 Скачать BibTeX", data=st.session_state.conversion_result.encode('utf-8'),
                         file_name=f"references_{target_format.lower()}.bib",
                         mime="text/plain", key="tex_download_multi")

# Иконка Telegram
telegram_icon_html = """
<div style="position: fixed; bottom: 20px; right: 20px;">
    <a href="https://t.me/cyber_referent_bot" target="_blank" title="Открыть @cyber_referent_bot">
        <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="50">
    </a>
</div>
"""
st.markdown(telegram_icon_html, unsafe_allow_html=True)