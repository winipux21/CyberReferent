import streamlit as st
import requests
import json

st.set_page_config(page_title="Cyber-Referent", layout="wide")
st.title("🎓 Cyber-Referent")

# Выбор режима работы: Проверка ссылок или Конвертер ссылок
mode = st.radio("Выберите режим работы:", ["Проверка ссылок", "Конвертер ссылок"])

if mode == "Проверка ссылок":
    # Существующая логика проверки ссылок (как ранее)
    style = st.selectbox("Выберите формат оформления:", ["GOST", "APA", "MLA"])
    method = st.radio("Выберите способ проверки:", ["📄 Файл PDF/DOCX", "📝 Текст списка литературы"])
    
    if method == "📄 Файл PDF/DOCX":
        uploaded_file = st.file_uploader("Выберите файл:", ['pdf', 'docx'])
        if st.button("Проверить файл"):
            if uploaded_file:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {"style": style}
                response = requests.post("https://maincyberreferent.onrender.com/check-file/", files=files, data=data, stream=True)
                valid_container = st.empty()
                invalid_container = st.empty()
                valid_results = []
                invalid_results = []
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            data_line = json.loads(line)
                            if data_line["type"] == "valid":
                                valid_results.append(data_line["reference"])
                            elif data_line["type"] == "invalid":
                                invalid_results.append(data_line)
                            with valid_container.container():
                                st.markdown("### ✅ Валидные ссылки:")
                                for ref in valid_results:
                                    st.success(ref)
                            with invalid_container.container():
                                st.markdown("### ⚠️ Ошибки и рекомендации:")
                                for item in invalid_results:
                                    st.error(item["original"])
                                    st.info(item["errors_and_corrections"])
                                    rec = item["recommendation"]
                                    st.info(f"📗 Рекомендуемый аналог: {rec['journal']} (ISSN: {rec['ISSN']})")
                        except Exception as e:
                            st.error(f"Ошибка декодирования: {e}")
    elif method == "📝 Текст списка литературы":
        bibliography_text = st.text_area("Вставьте список литературы:")
        if st.button("Проверить текст"):
            data = {"bibliography_text": bibliography_text, "style": style}
            response = requests.post("https://maincyberreferent.onrender.com/check-text/", data=data, stream=True)
            valid_container = st.empty()
            invalid_container = st.empty()
            valid_results = []
            invalid_results = []
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data_line = json.loads(line)
                        if data_line["type"] == "valid":
                            valid_results.append(data_line["reference"])
                        elif data_line["type"] == "invalid":
                            invalid_results.append(data_line)
                        with valid_container.container():
                            st.markdown("### ✅ Валидные ссылки:")
                            for ref in valid_results:
                                st.success(ref)
                        with invalid_container.container():
                            st.markdown("### ⚠️ Ошибки и рекомендации:")
                            for item in invalid_results:
                                st.error(item["original"])
                                st.info(item["errors_and_corrections"])
                                rec = item["recommendation"]
                                st.info(f"📗 Рекомендуемый аналог: {rec['journal']} (ISSN: {rec['ISSN']})")
                    except Exception as e:
                        st.error(f"Ошибка декодирования: {e}")
                        
elif mode == "Конвертер ссылок":
    st.header("Конвертер библиографической записи")
    reference = st.text_area("Введите библиографическую запись:", height=150)
    col1, col2 = st.columns(2)
    with col1:
        source_format = st.selectbox("Исходный формат:", ["APA", "GOST", "MLA"])
    with col2:
        target_format = st.selectbox("Целевой формат:", ["APA", "GOST", "MLA"])
    
    if st.button("Конвертировать"):
        data = {
            "reference": reference,
            "source_format": source_format,
            "target_format": target_format
        }
        response = requests.post("https://maincyberreferent.onrender.com/convert-reference/", data=data)
        if response.status_code == 200:
            result = response.json()
            st.success("Конвертированная запись:")
            st.code(result.get("converted", ""), language="text")
        else:
            st.error(f"Ошибка: {response.text}")

telegram_icon_html = """
<div style="position: fixed; bottom: 20px; right: 20px;">
    <a href="https://t.me/cyber_referent_bot" target="_blank" title="Открыть @cyber_referent_bot">
        <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="50">
    </a>
</div>
"""
st.markdown(telegram_icon_html, unsafe_allow_html=True)
