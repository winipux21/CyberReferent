# backend/gost_formatter.py

import re  # обязательно!

def format_gost(author, title, journal, year, issn):
    return f"{author}. {title} // {journal}. – {year}. – ISSN {issn}."

def format_references(valid_refs):
    formatted = []
    for ref, journal, issn in valid_refs:
        match = re.match(r'(.*?)\s?\((\d{4})\)', ref)
        if match:
            author, year = match.groups()
            title = "Название статьи"  # название статьи нужно будет парсить дополнительно или запрашивать отдельно
            formatted.append(format_gost(author, title, journal, year, issn))
    return formatted
