from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import json
import tempfile
import base64

app = FastAPI()

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_service_account_credentials():
    encoded_credentials = os.getenv('GCS_CREDENTIALS_BASE64')
    if not encoded_credentials:
        raise ValueError("Service account credentials are not set")
    decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
    service_account_info = json.loads(decoded_credentials)
    credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return credentials

def upload_file_to_drive(service, file_name, file_path, mime_type='image/jpeg'):
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

@app.get("/")
async def root():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
        <head>
            <title>FastAPI on Vercel</title>
            <link rel="icon" href="/static/favicon.ico" type="image/x-icon" />
        </head>
        <body>
            <div class="bg-gray-200 p-4 rounded-lg shadow-lg">
                <h1>Hello from FastAPI</h1>
                <ul>
                    <li><a href="/docs">/docs</a></li>
                    <li><a href="/redoc">/redoc</a></li>
                </ul>
                <p>Powered by <a href="https://vercel.com" target="_blank">Vercel</a></p>
            </div>
        </body>
    </html>
    """)

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"), limit: int = Query(10, description="The number of images to download")):
    credentials = get_service_account_credentials()
    service = build('drive', 'v3', credentials=credentials)

    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        try:
            downloader.download(query, limit=limit, output_dir=temp_dir, adult_filter_off=True, force_replace=False, timeout=60)
            uploaded_files = []
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                file_id = upload_file_to_drive(service, filename, file_path, mime_type='image/jpeg')  # Adjust MIME type if necessary
                uploaded_files.append(f"https://drive.google.com/uc?id={file_id}")
            return {"message": "Successfully uploaded images to Google Drive.", "files": uploaded_files}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
