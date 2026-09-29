import json
from parser import parse_query

def main():
    buffer = ""

    while True:
        try:
            prompt = "> " if not buffer.strip() else "... "
            line = input(prompt)

            if ";" in line:
                part_before_semi, _, _ = line.partition(";")
                buffer += " " + part_before_semi
                command = buffer.strip()
                buffer = ""

                if not command:
                    continue

                try:
                    parsed_ast = parse_query(command)
                    print("Parsed query structure:")
                    print(json.dumps(parsed_ast, indent=2, ensure_ascii=False))
                except Exception as err:
                    print(f"Error: {err}")
            else:
                buffer += " " + line

        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()