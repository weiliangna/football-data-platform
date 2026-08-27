import re


def decode_pass_code(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) == 3 and text.startswith("5") and text.isdigit():
        count = int(text) - 500
        if count == 1:
            return "单关"
        if count > 1:
            return f"{count}串1"
    return text


def normalize_pass_summary(value):
    text = str(value or "").strip()
    if not text:
        return ""
    parts = [
        part.strip()
        for part in re.split(r"[/,，、|+]+", text)
        if part.strip()
    ]
    normalized = []
    for part in parts or [text]:
        item = decode_pass_code(part)
        if item and item not in normalized:
            normalized.append(item)
    return "/".join(normalized)
