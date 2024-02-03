from fastapi import FastAPI, HTTPException, UploadFile, File
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO

app = FastAPI()

# Path to your service account key file
SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
PROJECT_ID = 'triple-water-379900'

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES)

service = build('drive', 'v3', credentials=credentials)

@app.post("/upload/")
async def upload_file_to_drive(file: UploadFile = File(...)):
    try:
        # Read file content
        file_content = await file.read()
        file_name = file.filename
        mime_type = file.content_type

        # Upload file to Google Drive
        file_metadata = {'name': file_name}
        media = MediaIoBaseUpload(BytesIO(file_content), mimetype=mime_type)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        # Make the file viewable by anyone with the link
        permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(fileId=file.get('id'), body=permission).execute()

        # Return the view link
        link = f"https://drive.google.com/file/d/{file.get('id')}/view"
        return {"message": "File uploaded successfully.", "link": link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
