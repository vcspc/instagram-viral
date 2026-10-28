"""Utilitários para análise e filtragem por período de tempo (timeframe)."""
import re
from datetime import datetime, timedelta, timezone


def parse_timeframe(timeframe: str | None) -> tuple[datetime | None, str]:
    """Analisa a string de período e retorna (data_minima, descricao_legivel).

    Formatos suportados:
      - Semanas: '1w', '2w', '1semana', '2semanas'
      - Meses: '1m', '2m', '3m', '6m', '1mes', '3meses'
      - Anos: '1y', '2y', '1ano', '2anos'
      - Dias: '7d', '15d', '30d' ou número inteiro direto '7', '30'
      - 'all', None ou vazio: sem restrição
    """
    if not timeframe:
        return None, "Todo o período"

    tf = timeframe.strip().lower()
    if tf in ("all", "tudo", "todos", "none", "0"):
        return None, "Todo o período"

    now = datetime.now(timezone.utc)

    # 1. Padrão semanas (ex: 1w, 2w, 1semana, 2semanas)
    match_w = re.match(r"^(\d+)\s*(?:w|sem|semana|semanas)$", tf)
    if match_w:
        qty = int(match_w.group(1))
        days = qty * 7
        min_date = now - timedelta(days=days)
        desc = f"Última semana ({days} dias)" if qty == 1 else f"Últimas {qty} semanas ({days} dias)"
        return min_date, desc

    # 2. Padrão meses (ex: 1m, 3m, 6m, 1mes, 3meses)
    match_m = re.match(r"^(\d+)\s*(?:m|mes|meses|month|months)$", tf)
    if match_m:
        qty = int(match_m.group(1))
        days = qty * 30
        min_date = now - timedelta(days=days)
        desc = f"Último mês ({days} dias)" if qty == 1 else f"Últimos {qty} meses ({days} dias)"
        return min_date, desc

    # 3. Padrão anos (ex: 1y, 2y, 1ano, 2anos, 1year)
    match_y = re.match(r"^(\d+)\s*(?:y|a|ano|anos|year|years)$", tf)
    if match_y:
        qty = int(match_y.group(1))
        days = qty * 365
        min_date = now - timedelta(days=days)
        desc = f"Último ano ({days} dias)" if qty == 1 else f"Últimos {qty} anos ({days} dias)"
        return min_date, desc

    # 4. Padrão dias (ex: 7d, 15d, ou apenas número)
    match_d = re.match(r"^(\d+)\s*(?:d|dia|dias|day|days)?$", tf)
    if match_d:
        qty = int(match_d.group(1))
        if qty <= 0:
            return None, "Todo o período"
        min_date = now - timedelta(days=qty)
        desc = f"Último dia ({qty} dia)" if qty == 1 else f"Últimos {qty} dias"
        return min_date, desc

    raise ValueError(
        f"Formato de período '{timeframe}' inválido. "
        "Use formatos como '1w' (1 semana), '1m' (1 mês), '3m' (3 meses), '1y' (1 ano) ou dias como '7d'."
    )


def is_within_timeframe(
    taken_at: datetime | int | float | None,
    min_datetime: datetime | None,
) -> bool:
    """Verifica se a data de publicação é igual ou posterior à data mínima limite."""
    if min_datetime is None or taken_at is None:
        return True

    if isinstance(taken_at, (int, float)):
        taken_dt = datetime.fromtimestamp(taken_at, tz=timezone.utc)
    elif isinstance(taken_at, datetime):
        taken_dt = taken_at if taken_at.tzinfo is not None else taken_at.replace(tzinfo=timezone.utc)
    else:
        return True

    min_dt = min_datetime if min_datetime.tzinfo is not None else min_datetime.replace(tzinfo=timezone.utc)
    return taken_dt >= min_dt
