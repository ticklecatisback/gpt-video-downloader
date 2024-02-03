from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
import base64
import os
import tempfile
import uuid

app = FastAPI()

html = """
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
"""

def get_service_account_credentials():
    encoded_credentials = os.getenv("GCS_CREDENTIALS_BASE64")
    if encoded_credentials is None:
        raise Exception("The GCS_CREDENTIALS_BASE64 environment variable is not set.")
    decoded_credentials = base64.b64decode(encoded_credentials)
    credentials_dict = json.loads(decoded_credentials)
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    return credentials

def build_drive_service():
    credentials = get_service_account_credentials()
    return build('drive', 'v3', credentials=credentials)

@app.get("/")
async def root():
    return HTMLResponse(html)

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(10, description="The number of images to download")):
    try:
        service = build_drive_service()
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader.download(query, limit=limit, output_dir=temp_dir, adult_filter_off=True, force_replace=False, timeout=60)
            urls = []
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                file_metadata = {'name': filename}
                media = MediaFileUpload(file_path, mimetype='image/jpeg')  # Adjust based on your image type
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                file_id = file.get('id')
                url = f"https://drive.google.com/uc?id={file_id}"
                urls.append(url)
            return {"message": "Images uploaded successfully.", "urls": urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
