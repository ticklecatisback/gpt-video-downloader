from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
from google.cloud import storage
from google.oauth2 import service_account
import json
import base64
import os
import tempfile
import uuid

app = FastAPI()

# Define HTML response for the root path
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

# Function to dynamically obtain the GCS client
def get_gcs_client():
    encoded_credentials = os.getenv("GCS_CREDENTIALS_BASE64")
    decoded_credentials = base64.b64decode(encoded_credentials)
    credentials_json = json.loads(decoded_credentials)
    credentials = service_account.Credentials.from_service_account_info(credentials_json)
    client = storage.Client(credentials=credentials, project=credentials_json['project_id'])
    return client

# Function to upload file to GCS
def upload_file_to_gcs(file_path, bucket_name, object_name=None):
    client = get_gcs_client()  # Ensure to get a fresh client
    bucket = client.bucket(bucket_name)
    if object_name is None:
        object_name = os.path.basename(file_path)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(file_path)
    return object_name

# Function to create a signed URL
def create_gcs_signed_url(bucket_name, object_name, expiration=3600):
    client = get_gcs_client()  # Ensure to get a fresh client
    blob = client.bucket(bucket_name).blob(object_name)
    try:
        url = blob.generate_signed_url(expiration=expiration)
    except Exception as e:
        print(e)
        return None
    return url

# Endpoint for testing GCS access
@app.get("/test-gcs")
async def test_gcs():
    client = get_gcs_client()
    if not client:
        return {"error": "Failed to create GCS client."}
    buckets = list(client.list_buckets())
    return {"buckets": [bucket.name for bucket in buckets]}

@app.get("/")
async def root():
    return HTMLResponse(html)

# Endpoint for downloading images and uploading them to GCS
@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(10, description="The number of images to download")):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader.download(query, limit=limit, output_dir=temp_dir, adult_filter_off=True, force_replace=False, timeout=60)
            urls = []
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                gcs_object_name = f"{uuid.uuid4()}-{filename}"
                # Correctly use bucket_name instead of a direct bucket object
                object_name = upload_file_to_gcs(file_path, GCS_BUCKET_NAME, gcs_object_name)
                url = create_gcs_signed_url(GCS_BUCKET_NAME, object_name)
                urls.append(url)
            return {"message": "Images uploaded successfully.", "urls": urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
