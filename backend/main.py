#backend/main.py
import io
import json
import time
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError, validator
from backend.document_parser import (
    extract_text, extract_bibliography_section, split_references_to_list
)
from backend.reference_validator import validate_references
from backend.gost_formatter import format_references
from backend.apa_formatter import format_apa
from backend.mla_formatter import format_mla
from backend.gost_ai_formatter import format_gost
from backend.apa_ai_formatter import format_apa_ai
from backend.mla_ai_formatter import format_mla_ai
from backend.text_parser import split_references_from_text
from backend.converter import convert_reference
from backend.web_scraper import extract_bibliographic_data, compose_reference
from backend.tex_bibliography_formatter import format_reference_to_tex
from backend.csv_bibliography_formatter import format_reference_to_csv
from backend.reference_converter import convert_to_format
from backend.tavily_search import search_reference  # Новый импорт
import logging

import asyncio

# Логирование
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="🎓 Cyber-Referent API",
    description="Сервис автоматической проверки библиографии по ГОСТ, APA, MLA",
    version="1.1"
)

# Pydantic model
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
    style: str = Form("GOST"),
    subformat: str = Form(...)
):
    logger.info("Received file check request: style=%s, subformat=%s", style, subformat)

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
        style_upper = style.upper()
        valid_refs, invalid_refs = validate_references(references, style_upper, subformat)

        # Асинхронный генератор
        async def stream_response():
            for ref_tpl in valid_refs:
                ref_text = ref_tpl[0]
                chunk = json.dumps(
                    {"type": "valid", "reference": ref_text},
                    ensure_ascii=False
                ) + "\n"
                logger.info("Sending valid chunk: %s", chunk)
                yield chunk.encode("utf-8")
                await asyncio.sleep(0.05)  # Асинхронная задержка

            for ref in invalid_refs:
                logger.info("Processing invalid ref: %s", ref['original'])
                if style_upper == "GOST":
                    analysis = format_gost(ref['original'], subformat)
                elif style_upper == "APA":
                    analysis = format_apa_ai(ref['original'], subformat)
                elif style_upper == "MLA":
                    analysis = format_mla_ai(ref['original'], subformat)

                # Асинхронные вызовы
                search_query = ref['original']
                url = await search_reference(search_query)
                corrected_ref = None
                if url:
                    try:
                        data = await extract_bibliographic_data(url)
                        corrected_ref = compose_reference(data, style_upper, subformat)
                        logger.info("Найден и отформатирован источник через Tavily: %s", corrected_ref)
                    except Exception as e:
                        logger.error("Ошибка веб-скрапинга для URL %s: %s", url, e)

                chunk = json.dumps({
                    "type": "invalid",
                    "original": ref['original'],
                    "errors_and_corrections": analysis,
                    "detected_type": ref['type'],
                    "initial_errors": ref['errors'],
                    "corrected_reference": corrected_ref if corrected_ref else "Не удалось найти источник"
                }, ensure_ascii=False) + "\n"
                logger.info("Sending invalid chunk: %s", chunk)
                yield chunk.encode("utf-8")
                await asyncio.sleep(0.05)  # Асинхронная задержка

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "text/event-stream; charset=utf-8"
            }
        )

    except Exception as e:
        logger.exception("File processing error")
        return JSONResponse({"error": f"Ошибка обработки файла: {e}"}, status_code=500)

@app.post("/check-text/")
async def check_text_references(
    bibliography_text: str = Form(...),
    style: str = Form("GOST"),
    subformat: str = Form(...)
):
    logger.info("Received text check request: style=%s, subformat=%s, text=%s",
                style, subformat, bibliography_text)

    try:
        bib_input = BibliographyInput(bibliography_text=bibliography_text)
    except ValidationError as e:
        logger.error("Validation error: %s", e.errors())
        return JSONResponse({"error": e.errors()}, status_code=400)

    try:
        references = split_references_from_text(bib_input.bibliography_text)
        style_upper = style.upper()
        valid_refs, invalid_refs = validate_references(references, style_upper, subformat)

        # Асинхронный генератор
        async def stream_response():
            for ref_tpl in valid_refs:
                ref_text = ref_tpl[0]
                chunk = json.dumps(
                    {"type": "valid", "reference": ref_text},
                    ensure_ascii=False
                ) + "\n"
                logger.info("Sending valid chunk: %s", chunk)
                yield chunk.encode("utf-8")
                await asyncio.sleep(0.05)  # Асинхронная задержка

            for ref in invalid_refs:
                logger.info("Processing invalid ref: %s", ref['original'])
                if style_upper == "GOST":
                    analysis = format_gost(ref['original'], subformat)
                elif style_upper == "APA":
                    analysis = format_apa_ai(ref['original'], subformat)
                elif style_upper == "MLA":
                    analysis = format_mla_ai(ref['original'], subformat)

                # Асинхронные вызовы
                search_query = ref['original']
                url = await search_reference(search_query)
                corrected_ref = None
                if url:
                    try:
                        data = await extract_bibliographic_data(url)
                        corrected_ref = compose_reference(data, style_upper, subformat)
                        logger.info("Найден и отформатирован источник через Tavily: %s", corrected_ref)
                    except Exception as e:
                        logger.error("Ошибка веб-скрапинга для URL %s: %s", url, e)

                chunk = json.dumps({
                    "type": "invalid",
                    "original": ref['original'],
                    "errors_and_corrections": analysis,
                    "detected_type": ref['type'],
                    "initial_errors": ref['errors'],
                    "corrected_reference": corrected_ref if corrected_ref else "Не удалось найти источник"
                }, ensure_ascii=False) + "\n"
                logger.info("Sending invalid chunk: %s", chunk)
                yield chunk.encode("utf-8")
                await asyncio.sleep(0.05)  # Асинхронная задержка

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "text/event-stream; charset=utf-8"
            }
        )

    except Exception as e:
        logger.exception("Text processing error")
        return JSONResponse({"error": f"Ошибка обработки текста: {e}"}, status_code=500)

# Остальные эндпоинты остаются без изменений
@app.post("/convert-reference/")
async def convert_reference_endpoint(
    reference: str = Form(...),
    source_format: str = Form(...),
    target_format: str = Form(...),
    target_subformat: str = Form(...)
):
    logger.info("Received conversion request: reference=%s", reference)
    try:
        converted = convert_to_format(reference, target_format, target_subformat)
        return JSONResponse({
            "original": reference,
            "converted": converted,
            "source_format": source_format,
            "target_format": target_format,
            "target_subformat": target_subformat
        })
    except Exception as e:
        logger.exception("Conversion error")
        return JSONResponse({"error": f"Ошибка конвертации: {e}"}, status_code=500)

@app.post("/convert-references-text/")
async def convert_references_text(
    bibliography_text: str = Form(...),
    source_format: str = Form(...),
    target_format: str = Form(...),
    target_subformat: str = Form(...)
):
    logger.info("Received multiple references conversion request via text")
    try:
        references = split_references_from_text(bibliography_text)
        if not references:
            return JSONResponse({"error": "Ссылки не найдены в тексте."}, status_code=400)
        
        converted_references = []
        for ref in references:
            try:
                converted = convert_to_format(ref, target_format, target_subformat)
                converted_references.append({"original": ref, "converted": converted})
            except Exception as e:
                converted_references.append({"original": ref, "error": str(e)})
        return JSONResponse({"converted_references": converted_references})
    except Exception as e:
        logger.exception("Multiple references conversion error")
        return JSONResponse({"error": f"Ошибка конвертации: {e}"}, status_code=500)

@app.post("/convert-references-file/")
async def convert_references_file(
    file: UploadFile = File(...),
    source_format: str = Form(...),
    target_format: str = Form(...),
    target_subformat: str = Form(...)
):
    logger.info("Received multiple references conversion request via file")
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
        converted_references = []
        for ref in references:
            try:
                converted = convert_to_format(ref, target_format, target_subformat)
                converted_references.append({"original": ref, "converted": converted})
            except Exception as e:
                converted_references.append({"original": ref, "error": str(e)})
        return JSONResponse({"converted_references": converted_references})
    except Exception as e:
        logger.exception("File conversion error")
        return JSONResponse({"error": f"Ошибка обработки файла: {e}"}, status_code=500)

@app.post("/scrape-reference/")
async def scrape_reference(
    url: str = Form(...),
    style: str = Form("APA"),
    subformat: str = Form(...)):
    logger.info("Received scrape request: url=%s", url)
    try:
        data = await extract_bibliographic_data(url)
        reference = compose_reference(data, style, subformat)
        return JSONResponse({"reference": reference})
    except Exception as e:
        logger.exception("Scrape error")
        return JSONResponse({"error": f"Ошибка: {e}"}, status_code=500)

@app.post("/convert-reference-tex/")
async def convert_reference_tex(
    reference: str = Form(...),
    target_format: str = Form(...),
    subformat: str = Form(...)):
    logger.info("Received TeX conversion request")
    formatted = format_reference_to_tex(reference, target_format, subformat)
    return JSONResponse({"converted": formatted})

@app.post("/convert-references-tex-text/")
async def convert_references_tex_text(
    bibliography_text: str = Form(...),
    target_format: str = Form(...),
    subformat: str = Form(...)
):
    logger.info("Received multiple references TeX conversion request via text")
    try:
        references = split_references_from_text(bibliography_text)
        if not references:
            return JSONResponse({"error": "Ссылки не найдены в тексте."}, status_code=400)
        
        bibtex_entries = []
        for ref in references:
            try:
                bibtex_entry = format_reference_to_tex(ref, target_format, subformat)
                bibtex_entries.append(bibtex_entry)
            except Exception as e:
                bibtex_entries.append(f"% Error for reference '{ref}': {str(e)}")
        combined_bibtex = "\n\n".join(bibtex_entries)
        return JSONResponse({"bibtex": combined_bibtex})
    except Exception as e:
        logger.exception("Multiple TeX conversion error")
        return JSONResponse({"error": f"Ошибка конвертации: {e}"}, status_code=500)

@app.post("/convert-references-tex-file/")
async def convert_references_tex_file(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    subformat: str = Form(...)
):
    logger.info("Received multiple references TeX conversion request via file")
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
        bibtex_entries = []
        for ref in references:
            try:
                bibtex_entry = format_reference_to_tex(ref, target_format, subformat)
                bibtex_entries.append(bibtex_entry)
            except Exception as e:
                bibtex_entries.append(f"% Error for reference '{ref}': {str(e)}")
        combined_bibtex = "\n\n".join(bibtex_entries)
        return JSONResponse({"bibtex": combined_bibtex})
    except Exception as e:
        logger.exception("File TeX conversion error")
        return JSONResponse({"error": f"Ошибка обработки файла: {e}"}, status_code=500)

@app.post("/convert-reference-csv/")
async def convert_reference_csv(
    reference: str = Form(...),
    target_format: str = Form(...),
    subformat: str = Form(...)
):
    logger.info("CSV‑convert request")
    try:
        csv_str = format_reference_to_csv(reference)
        return JSONResponse({"csv": csv_str})
    except Exception as e:
        logger.exception("CSV convert error")
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)