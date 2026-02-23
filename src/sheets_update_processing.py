import argparse
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

def col_letter(n0: int) -> str:
    n0 += 1
    s = ""
    while n0:
        n0, r = divmod(n0 - 1, 26)
        s = chr(65 + r) + s
    return s

def get_service():
    info = json.loads(os.environ["GOOGLE_SHEETS_SA_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet-id", default=os.environ.get("SHEET_ID"))
    ap.add_argument("--tab", default=os.environ.get("SHEET_TAB", "Topics"))
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--json", required=True)
    args = ap.parse_args()

    data = json.loads(open(args.json, "r", encoding="utf-8").read())

    service = get_service()
    sheets = service.spreadsheets().values()

    # Read header to find column positions (case-insensitive)
    header = sheets.get(
        spreadsheetId=args.sheet_id,
        range=f"{args.tab}!A1:K1"
    ).execute().get("values", [[]])[0]

    header_map = {h.strip().lower(): i for i, h in enumerate(header) if h}

    def idx(name: str) -> int:
        if name in header_map:
            return header_map[name]
        raise SystemExit(f"Missing header '{name}' in row 1.")

    title_idx = idx("youtube_title")
    desc_idx = idx("youtube_description")
    script_idx = idx("script")

    updates = [
        {"range": f"{args.tab}!{col_letter(title_idx)}{args.row}", "values": [[data.get("youtube_title","")]]},
        {"range": f"{args.tab}!{col_letter(desc_idx)}{args.row}", "values": [[data.get("youtube_description","")]]},
        {"range": f"{args.tab}!{col_letter(script_idx)}{args.row}", "values": [[data.get("script","")]]},
    ]

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=args.sheet_id,
        body={"valueInputOption": "RAW", "data": updates}
    ).execute()

    print(f"✅ Wrote title/description/script to row {args.row}")

if __name__ == "__main__":
    main()
