import streamlit as st
import requests
import json

st.set_page_config(page_title="Cyber-Referent")
st.title("🎓 Cyber-Referent")

# Выбор формата оформления: GOST, APA, MLA
style = st.selectbox("Выберите формат оформления:", ["GOST", "APA", "MLA"])

# Выбор способа проверки
mode = st.radio("Выберите способ проверки:", ["📄 Файл PDF/DOCX", "📝 Текст списка литературы"])

if mode == "📄 Файл PDF/DOCX":
    uploaded_file = st.file_uploader("Выберите файл:", ['pdf', 'docx'])
    
    if st.button("Проверить файл"):
        if uploaded_file:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            # Передаем выбранный формат в параметре style
            data = {"style": style}
            response = requests.post("http://localhost:8000/check-file/", files=files, data=data, stream=True)
            
            valid_container = st.empty()
            invalid_container = st.empty()
            
            valid_results = []
            invalid_results = []
            
            # Читаем поток ответа по строкам
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data_line = json.loads(line)
                        if data_line["type"] == "valid":
                            valid_results.append(data_line["reference"])
                        elif data_line["type"] == "invalid":
                            invalid_results.append(data_line)
                        # Обновляем отображение валидных ссылок
                        with valid_container.container():
                            st.markdown("### ✅ Валидные ссылки:")
                            for ref in valid_results:
                                st.success(ref)
                        # Обновляем отображение ошибок и рекомендаций
                        with invalid_container.container():
                            st.markdown("### ⚠️ Ошибки и рекомендации:")
                            for item in invalid_results:
                                st.error(item["original"])
                                st.info(item["errors_and_corrections"])
                                rec = item["recommendation"]
                                st.info(f"📗 Рекомендуемый аналог: {rec['journal']} (ISSN: {rec['ISSN']})")
                    except Exception as e:
                        st.error(f"Ошибка декодирования: {e}")

elif mode == "📝 Текст списка литературы":
    bibliography_text = st.text_area("Вставьте список литературы:")
    
    if st.button("Проверить текст"):
        # Передаем выбранный формат вместе с текстом библиографии
        data = {"bibliography_text": bibliography_text, "style": style}
        response = requests.post("http://127.0.0.1:8000/check-text/", data=data, stream=True)
        
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

