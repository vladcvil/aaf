import re
from typing import Dict, Any, List

IDENT_RE = r"[a-zA-Z][a-zA-Z0-9_]*"

def split_comma_separated_strings(raw: str) -> List[str]:
    """Коректно розбиває список значень у лапках через кому."""
    tokens = []
    pattern = re.compile(r'\s*("[^"]*")\s*(?:,\s*|$)')
    pos = 0
    raw = raw.strip()
    if not raw:
        return []

    while pos < len(raw):
        m = pattern.match(raw, pos)
        if not m:
            raise ValueError(f"Некоректний синтаксис списку значень біля: '{raw[pos:]}'")
        tokens.append(m.group(1)[1:-1])  # прибираємо лапки
        pos = m.end()

    return tokens


def parse_create(body: str) -> Dict[str, Any]:
    match = re.match(rf"^\s*({IDENT_RE})\s*\((.*)\)\s*$", body, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Некоректний синтаксис команди CREATE")

    table_name = match.group(1)
    inner = match.group(2).strip()
    if not inner:
        raise ValueError("Таблиця повинна містити хоча б один стовпець")

    raw_columns = [col.strip() for col in inner.split(",")]

    columns = []
    seen = set()

    for col_str in raw_columns:
        if not col_str:
            raise ValueError("Знайдено порожнє визначення стовпця (зайва кома)")

        col_match = re.match(rf"^({IDENT_RE})(?:\s+(INDEXED))?$", col_str, re.IGNORECASE)
        if not col_match:
            raise ValueError(f"Некоректне визначення стовпця: '{col_str}'")

        col_name = col_match.group(1)
        if col_name in seen:
            raise ValueError(f"Дублювання імені стовпця: '{col_name}'")
        seen.add(col_name)

        is_indexed = col_match.group(2) is not None
        columns.append({"name": col_name, "indexed": is_indexed})

    return {
        "type": "CREATE",
        "table_name": table_name,
        "columns": columns
    }


def parse_insert(body: str) -> Dict[str, Any]:
    match = re.match(rf"^\s*(?:INTO\s+)?({IDENT_RE})\s*\((.*)\)\s*$", body, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Некоректний синтаксис команди INSERT")

    table_name = match.group(1)
    values_str = match.group(2).strip()

    if not values_str:
        raise ValueError("В команді INSERT відсутні значення")

    values = split_comma_separated_strings(values_str)

    return {
        "type": "INSERT",
        "table_name": table_name,
        "values": values
    }


def parse_select(body: str) -> Dict[str, Any]:
    pattern = (
        r"^\s*(.*?)\s*"
        r"\bFROM\s+(" + IDENT_RE + r")"
        r"(?:\s+WHERE\s+(.*?))?"
        r"(?:\s+GROUP_BY\s+(.*?))?$"
    )
    match = re.match(pattern, body.strip(), re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Некоректний синтаксис команди SELECT")

    select_clause = match.group(1).strip()
    table_name = match.group(2)
    where_clause = match.group(3)
    group_by_clause = match.group(4)

    group_by_cols = None
    aggregations = []

    if group_by_clause is not None:
        raw_cols = [c.strip() for c in group_by_clause.split(",")]
        group_by_cols = []
        for c in raw_cols:
            if not c or not re.match(rf"^{IDENT_RE}$", c):
                raise ValueError(f"Некоректне ім'я стовпця в GROUP_BY: '{c}'")
            group_by_cols.append(c)

        if select_clause:
            raw_aggs = [a.strip() for a in select_clause.split(",")]
            for agg in raw_aggs:
                if not agg:
                    raise ValueError("Порожній вираз у списку агрегацій")
                agg_match = re.match(rf"^(COUNT|MAX|LONGEST)\s*\(\s*({IDENT_RE})\s*\)$", agg, re.IGNORECASE)
                if not agg_match:
                    raise ValueError(f"Невідома або некоректна агрегатна функція: '{agg}'")
                aggregations.append({
                    "function": agg_match.group(1).upper(),
                    "column": agg_match.group(2)
                })
    else:
        if select_clause != "":
            raise ValueError("Без GROUP_BY вираз після SELECT повинен бути порожнім (використовуйте: 'SELECT FROM ...')")

    where_cond = None
    if where_clause is not None:
        where_match = re.match(
            rf"^\s*({IDENT_RE})\s*<\s*({IDENT_RE}|\"[^\"]*\")\s*$",
            where_clause,
            re.DOTALL
        )
        if not where_match:
            raise ValueError(f"Некоректна умова WHERE (очікується col < val або col < col2): '{where_clause}'")

        col1 = where_match.group(1)
        right = where_match.group(2).strip()

        if right.startswith('"') and right.endswith('"'):
            where_cond = {"left": col1, "operator": "<", "right": right[1:-1], "is_literal": True}
        else:
            where_cond = {"left": col1, "operator": "<", "right": right, "is_literal": False}

    return {
        "type": "SELECT",
        "table_name": table_name,
        "aggregations": aggregations,
        "where": where_cond,
        "group_by": group_by_cols
    }


def parse_query(command: str) -> Dict[str, Any]:
    cmd = command.strip()
    match = re.match(r"^\s*([a-zA-Z_]+)\s*(.*)$", cmd, re.DOTALL)
    if not match:
        raise ValueError("Порожня команда або невірний синтаксис")

    keyword = match.group(1).upper()
    body = match.group(2).strip()

    if keyword == "CREATE":
        return parse_create(body)
    elif keyword == "INSERT":
        return parse_insert(body)
    elif keyword == "SELECT":
        return parse_select(body)
    else:
        raise ValueError(f"Невідома команда: '{keyword}'")