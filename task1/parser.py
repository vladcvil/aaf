import re
from typing import Dict, Any

IDENT_RE = r"[a-zA-Z][a-zA-Z0-9_]*"

def parse_create(body: str) -> Dict[str, Any]:
    match = re.match(rf"^\s*({IDENT_RE})\s*\((.*)\)\s*$", body, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Некоректний синтаксис команди CREATE")

    table_name = match.group(1)
    raw_columns = [col.strip() for col in match.group(2).split(",") if col.strip()]

    if not raw_columns:
        raise ValueError("Таблиця повинна містити хоча б один стовпець")

    columns = []
    seen = set()

    for col_str in raw_columns:
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
    raw_values = [v.strip() for v in match.group(2).split(",") if v.strip()]

    if not raw_values:
        raise ValueError("В команді INSERT відсутні значення")

    values = []
    for val_str in raw_values:
        val_match = re.match(r'^"(.*)"$', val_str, re.DOTALL)
        if not val_match:
            raise ValueError(f"Значення має бути рядком у подвійних лапках: {val_str}")
        values.append(val_match.group(1))

    return {
        "type": "INSERT",
        "table_name": table_name,
        "values": values
    }


def parse_select(body: str) -> Dict[str, Any]:
    # \bFROM\b гарантує коректне відокремлення ключового слова FROM
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

    # Валідація GROUP_BY та функцій у SELECT
    group_by_cols = None
    aggregations = []

    if group_by_clause is not None:
        group_by_cols = [c.strip() for c in group_by_clause.split(",") if c.strip()]
        for c in group_by_cols:
            if not re.match(rf"^{IDENT_RE}$", c):
                raise ValueError(f"Некоректне ім'я стовпця в GROUP_BY: '{c}'")

        if select_clause:
            raw_aggs = [a.strip() for a in select_clause.split(",") if a.strip()]
            for agg in raw_aggs:
                agg_match = re.match(rf"^(COUNT|MAX|LONGEST)\s*\(\s*({IDENT_RE})\s*\)$", agg, re.IGNORECASE)
                if not agg_match:
                    raise ValueError(f"Невідома або некоректна агрегатна функція: '{agg}'")
                aggregations.append({
                    "function": agg_match.group(1).upper(),
                    "column": agg_match.group(2)
                })
    else:
        if select_clause != "":
            raise ValueError("Без GROUP_BY вираз після SELECT повинен бути порожнім: 'SELECT FROM ...'")

    # Обробка WHERE
    where_cond = None
    if where_clause is not None:
        where_match = re.match(
            rf"^({IDENT_RE})\s*<\s*({IDENT_RE}|\".*\")$",
            where_clause.strip(),
            re.DOTALL
        )
        if not where_match:
            raise ValueError(f"Некоректна умова WHERE: '{where_clause}'")

        col1 = where_match.group(1)
        right = where_match.group(2)

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
    match = re.match(r"^\s*([a-zA-Z]+)\s*(.*)$", cmd, re.DOTALL)
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