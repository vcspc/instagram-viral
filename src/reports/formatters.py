"""Formatadores visuais de dados numéricos e textuais."""
import re


def format_number(n: int | float) -> str:
    """Converte números inteiros em strings amigáveis (ex: 1.5M, 42.1K)."""
    val = float(n)
    if val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.1f}B"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(int(val))


def slugify(text: str) -> str:
    """Gera um slug seguro para nomes de arquivos a partir de um texto."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)[:40]
