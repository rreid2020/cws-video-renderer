import json
import re
from pathlib import Path

def main():
    picked_log = Path("out/picked.log")
    out_file = Path("out/row.json")
    github_output = Path(Path.cwd() / Path.getenv("GITHUB_OUTPUT", ""))  # may not exist in local runs

    log = picked_log.read_text(encoding="utf-8")
    m = re.search(r"(\{[\s\S]*\})", log)

    # Write outputs in the format Actions expects
    def write_output(key: str, value: str):
        if not str(github_output):
            return
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")

    if not m:
        print("No NEW topic found.")
        write_output("found", "false")
        return

    data = json.loads(m.group(1))
    out_file.write_text(json.dumps(data), encoding="utf-8")

    write_output("found", "true")
    write_output("row", str(data["sheet_row"]))
    write_output("topic", data["topic"])

    print(f"Picked row: {data['sheet_row']}")
    print(f"Topic: {data['topic']}")

if __name__ == "__main__":
    # avoid importing os at top; keep it explicit
    import os
    from os import getenv as Path_getenv
    Path.getenv = staticmethod(lambda k, d="": os.getenv(k, d))
    main()
