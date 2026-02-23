import argparse, json, os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--folder-id", required=True)
    args = ap.parse_args()

    info = json.loads(os.environ["GDRIVE_SA_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )

    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": os.path.basename(args.file), "parents": [args.folder_id]}
    media = MediaFileUpload(args.file, mimetype="video/mp4", resumable=True)

    created = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,name,webViewLink"
    ).execute()

    print("Uploaded:", created["name"])
    print("File ID:", created["id"])
    print("Link:", created.get("webViewLink"))

if __name__ == "__main__":
    main()
