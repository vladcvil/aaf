import json
from parser import parse_query

def split_by_semicolon(buffer: str):
    in_quotes = False
    for i, ch in enumerate(buffer):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ';' and not in_quotes:
            return buffer[:i], buffer[i+1:]
    return None, buffer

def main():
    buffer = ""

    while True:
        try:
            prompt = "> " if not buffer.strip() else "... "
            line = input(prompt)

            buffer += line + "\n"

            while True:
                cmd_str, remaining = split_by_semicolon(buffer)
                if cmd_str is None:
                    break
                
                buffer = remaining
                command = cmd_str.strip()
                if not command:
                    continue

                try:
                    parsed_ast = parse_query(command)
                    print("Parsed query structure:")
                    print(json.dumps(parsed_ast, indent=2, ensure_ascii=False))
                except Exception as err:
                    print(f"Error: {err}")

        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()