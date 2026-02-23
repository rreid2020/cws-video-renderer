import argparse
import json
import os
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build


HEADERS = [
    "id",
    "topic",
    "format",
    "status",
    "youtube_title",
    "youtube_description",
    "script",
    "youtube_url",
    "created_at",
    "processed_at",
    "error",
]

STATUS_COL = "status"
PROCESSED_AT_COL = "processed_at"
ERROR_COL = "error"


def col_letter(col_index_0: int) -> str:
    """0-based to A1 col letters (A, B, ..., Z, AA, AB...)"""
    col_index_0 += 1
    s = ""
    while col_index_0:
        col_index_0, r = divmod(col_index_0 - 1, 26)
        s = chr(65 + r) + s
    return s


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_service():
    info = json.loads(os.environ["GOOGLE_SHEETS_SA_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet-id", default=os.environ.get("SHEET_ID"), required=False)
    ap.add_argument("--tab", default=os.environ.get("SHEET_TAB", "Topics"), required=False)
    args = ap.parse_args()

    if not args.sheet_id:
        raise SystemExit("Missing SHEET_ID (env or --sheet-id).")

    service = get_service()
    sheets = service.spreadsheets().values()

    # Read all rows in the tab
    read_range = f"{args.tab}!A1:K"
    resp = sheets.get(spreadsheetId=args.sheet_id, range=read_range).execute()
    values = resp.get("values", [])

    if not values:
        raise SystemExit(f"No data found in range {read_range}")

    header = values[0]
    # If user header differs slightly, we still locate key columns by name
    header_map = {name.strip(): idx for idx, name in enumerate(header)}

    def idx_of(name: str) -> int:
        if name in header_map:
            return header_map[name]
        raise SystemExit(f"Missing required header column '{name}' in row 1.")

    status_idx = idx_of(STATUS_COL)
    topic_idx = idx_of("topic")
    format_idx = idx_of("format")
    id_idx = idx_of("id")

    processed_at_idx = header_map.get(PROCESSED_AT_COL, None)
    error_idx = header_map.get(ERROR_COL, None)

    # Find first NEW row (starting from row 2 in sheet)
    picked_row_num = None
    picked = None

    for i in range(1, len(values)):
        row = values[i]
        status = row[status_idx].strip().upper() if len(row) > status_idx and row[status_idx] else ""
        if status == "NEW":
            picked_row_num = i + 1  # sheet row number
            picked = row
            break

    if not picked_row_num:
        print("No NEW topics found. Nothing to do.")
        return

    # Build picked payload
    def safe_get(idx: int) -> str:
        return picked[idx] if len(picked) > idx else ""

    payload = {
        "sheet_row": picked_row_num,
        "id": safe_get(id_idx),
        "topic": safe_get(topic_idx),
        "format": safe_get(format_idx) or "short",
        "status_before": "NEW",
    }

    # Update status to PROCESSING (+ clear error, set processed_at blank for now)
    status_cell = f"{args.tab}!{col_letter(status_idx)}{picked_row_num}"
    updates = [
        {"range": status_cell, "values": [["PROCESSING"]]},
    ]

    if error_idx is not None:
        err_cell = f"{args.tab}!{col_letter(error_idx)}{picked_row_num}"
        updates.append({"range": err_cell, "values": [[""]]})

    # Optional: stamp processed_at when done; for PROCESSING we can leave blank
    # If you'd rather stamp a "started_at", add a new column later.

    body = {
        "valueInputOption": "RAW",
        "data": updates,
    }

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=args.sheet_id,
        body=body
    ).execute()

    print("✅ Picked topic and set to PROCESSING:")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
