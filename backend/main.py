import io
import json
import time
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError, validator
from backend.document_parser import extract_text, extract_bibliography_section, split_references_to_list
from backend.reference_validator import load_vak_list, validate_references
from backend.gost_formatter import format_references  # для ГОСТ-форматирования валидных ссылок
from backend.apa_formatter import format_apa
from backend.mla_formatter import format_mla
from backend.gost_ai_formatter import format_gost
from backend.apa_ai_formatter import format_apa_ai
from backend.mla_ai_formatter import format_mla_ai
from backend.recommendation_engine import ReferenceRecommender
from backend.text_parser import split_references_from_text

app = FastAPI(
    title="🎓 Cyber-Referent API",
    description="Сервис автоматической проверки библиографии по ГОСТ, APA, MLA и ВАК",
    version="1.1"
)

vak_df = load_vak_list('data/VAK_journals.csv')
recommender = ReferenceRecommender(vak_df)

# Pydantic-модель для валидации текстового запроса библиографии
class BibliographyInput(BaseModel):
    bibliography_text: str = Field(..., min_length=1)

    @validator("bibliography_text")
    def check_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Текст библиографии не может быть пустым.")
        return v

@app.get("/")
async def root():
    return {"message": "🎓 Cyber-Referent API успешно запущен!"}

@app.post("/check-file/")
async def check_references_from_file(
    file: UploadFile = File(...),
    style: str = Form("GOST")  # параметр выбора формата: GOST, APA, MLA
):
    if not file.filename.lower().endswith(('pdf', 'docx')):
        return JSONResponse({"error": "Файл должен быть .pdf или .docx"}, status_code=400)
    try:
        file_content = await file.read()
        file_obj = io.BytesIO(file_content)
        file_obj.seek(0)

        text = extract_text(file_obj, file.filename)
        bibliography_section = extract_bibliography_section(text)
        if not bibliography_section:
            return JSONResponse({"error": "Список литературы не найден."}, status_code=400)

        references = split_references_to_list(bibliography_section)
        valid_refs, invalid_refs = validate_references(references, vak_df)

        # Выбор форматирования валидных ссылок по выбранному стилю
        style_upper = style.upper()
        if style_upper == "GOST":
            formatted_valid_refs = format_references(valid_refs)
        elif style_upper == "APA":
            formatted_valid_refs = [format_apa(ref) for ref in valid_refs]
        elif style_upper == "MLA":
            formatted_valid_refs = [format_mla(ref) for ref in valid_refs]
        else:
            return JSONResponse({"error": "Неверно указан формат. Допустимые значения: GOST, APA, MLA."}, status_code=400)

        def stream_response():
            # Отправляем валидные ссылки по одной
            for ref in formatted_valid_refs:
                chunk = json.dumps({"type": "valid", "reference": ref}) + "\n"
                yield chunk.encode("utf-8")
                time.sleep(0.5)  # задержка для демонстрации стриминга
            # Затем обрабатываем невалидные ссылки
            for ref in invalid_refs:
                print(f"Обрабатываю ссылку: {ref}")  # логирование на сервере
                if style_upper == "GOST":
                    analysis = format_gost(ref)
                elif style_upper == "APA":
                    analysis = format_apa_ai(ref)
                elif style_upper == "MLA":
                    analysis = format_mla_ai(ref)
                recommendations = recommender.recommend_similar(ref, k=1)
                chunk = json.dumps({
                    "type": "invalid",
                    "original": ref,
                    "errors_and_corrections": analysis,
                    "recommendation": {
                        "journal": recommendations[0][0],
                        "ISSN": recommendations[0][1]
                    }
                }) + "\n"
                yield chunk.encode("utf-8")
                time.sleep(0.5)

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"}
        )

    except Exception as e:
        print(f"Ошибка обработки файла: {e}")
        return JSONResponse({"error": f"Ошибка обработки файла: {str(e)}"}, status_code=500)

@app.post("/check-text/")
async def check_text_references(
    bibliography_text: str = Form(...),
    style: str = Form("GOST")
):
    try:
        # Валидация входных данных через Pydantic
        bib_input = BibliographyInput(bibliography_text=bibliography_text)
    except ValidationError as e:
        return JSONResponse({"error": e.errors()}, status_code=400)
    try:
        references = split_references_from_text(bib_input.bibliography_text)
        valid_refs, invalid_refs = validate_references(references, vak_df)

        style_upper = style.upper()
        if style_upper == "GOST":
            formatted_valid_refs = format_references(valid_refs)
        elif style_upper == "APA":
            formatted_valid_refs = [format_apa(ref) for ref in valid_refs]
        elif style_upper == "MLA":
            formatted_valid_refs = [format_mla(ref) for ref in valid_refs]
        else:
            return JSONResponse({"error": "Неверно указан формат. Допустимые значения: GOST, APA, MLA."}, status_code=400)

        def stream_response():
            # Отправляем валидные ссылки
            for ref in formatted_valid_refs:
                chunk = json.dumps({"type": "valid", "reference": ref}) + "\n"
                yield chunk.encode("utf-8")
                time.sleep(0.5)
            # Затем обрабатываем невалидные ссылки
            for ref in invalid_refs:
                print(f"Обрабатываю ссылку: {ref}")
                if style_upper == "GOST":
                    analysis = format_gost(ref)
                elif style_upper == "APA":
                    analysis = format_apa_ai(ref)
                elif style_upper == "MLA":
                    analysis = format_mla_ai(ref)
                recommendations = recommender.recommend_similar(ref, k=1)
                chunk = json.dumps({
                    "type": "invalid",
                    "original": ref,
                    "errors_and_corrections": analysis,
                    "recommendation": {
                        "journal": recommendations[0][0],
                        "ISSN": recommendations[0][1]
                    }
                }) + "\n"
                yield chunk.encode("utf-8")
                time.sleep(0.5)

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"}
        )
    except Exception as e:
        print(f"Ошибка обработки текста: {e}")
        return JSONResponse({"error": f"Ошибка обработки текста: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
