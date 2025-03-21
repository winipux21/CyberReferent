import pdfplumber
import docx
import re
import os
import io

def extract_text_from_pdf(file_obj):
    text = ""
    file_obj.seek(0)  # сбрасываем указатель!
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_from_docx(file_obj):
    file_obj.seek(0)
    doc = docx.Document(file_obj)
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

def extract_text(file_obj, filename):
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_obj)
    elif ext == ".docx":
        return extract_text_from_docx(file_obj)
    else:
        raise ValueError("Поддерживаются только .pdf и .docx файлы.")

def extract_bibliography_section(text):
    patterns = [
        r"(Список литературы|Литература|Библиография|References)\s*\n(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(2).strip()
    return ""

def clean_multiline_refs(ref):
    ref = re.sub(r'-\n\s*', '', ref)
    ref = re.sub(r'(?<=[a-zа-яё])(?=[A-ZА-ЯЁ])', ' ', ref)
    ref = re.sub(r'\n+', ' ', ref)
    ref = re.sub(r'\s+', ' ', ref)
    return ref.strip()

def split_references_to_list(bibliography_text):
    references = re.split(r'\n\d+\.\s', bibliography_text)
    references = [clean_multiline_refs(ref) for ref in references if len(ref.strip()) > 5]
    return references

