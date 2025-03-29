# backend/converter.py

def convert_reference(reference: str, source_format: str, target_format: str) -> str:
    reference = reference.strip()
    if target_format.upper() == "APA":
        from backend.apa_ai_converter import convert_to_apa
        return convert_to_apa(reference)
    elif target_format.upper() == "GOST":
        from backend.gost_ai_converter import convert_to_gost
        return convert_to_gost(reference)
    elif target_format.upper() == "MLA":
        from backend.mla_ai_converter import convert_to_mla
        return convert_to_mla(reference)
    else:
        return "Неверный формат целевой ссылки. Допустимые значения: APA, GOST, MLA."
