from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
from google.cloud import storage
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

# Function to decode credentials and create a GCS client
def get_gcs_client():
    # Fetch the encoded credentials from the environment variable
    encoded_credentials = os.getenv("GCS_CREDENTIALS_BASE64")
    
    # Decode the credentials
    decoded_credentials = base64.b64decode(encoded_credentials)
    
    # Load the JSON credentials
    credentials_json = json.loads(decoded_credentials)
    
    # Create a credentials object from the decoded JSON
    credentials = service_account.Credentials.from_service_account_info(credentials_json)
    
    # Initialize the GCS client with the credentials
    client = storage.Client(credentials=credentials, project=credentials_json['project_id'])
    
    return client

# Example usage within an endpoint
@app.get("/test-gcs")
async def test_gcs():
    # Use the GCS client to interact with GCS
    client = get_gcs_client()
    buckets = list(client.list_buckets())
    return {"buckets": [bucket.name for bucket in buckets]}


@app.get("/")
async def root():
    return HTMLResponse(html)

# Google Cloud Storage Configuration
GCS_BUCKET_NAME = 'bucket32332'
# Ensure you replace 'your-google-cloud-project-id' with your actual project ID
storage_client = storage.Client(project='triple-water-379900')
bucket = storage_client.bucket(GCS_BUCKET_NAME)

def upload_file_to_gcs(file_path, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file_path)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(file_path)
    return object_name

def create_gcs_signed_url(bucket_name, object_name, expiration=3600):
    blob = storage_client.bucket(bucket_name).blob(object_name)
    try:
        url = blob.generate_signed_url(expiration=expiration)
    except Exception as e:
        print(e)
        return None
    return url

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(10, description="The number of images to download")):
    try:
        # Using a temporary directory to store downloaded images
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader.download(query, limit=limit, output_dir=temp_dir, adult_filter_off=True, force_replace=False, timeout=60)

            # Upload files to GCS and get URLs
            urls = []
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                gcs_object_name = f"{uuid.uuid4()}-{filename}"
                upload_file_to_gcs(file_path, bucket, gcs_object_name)
                url = create_gcs_signed_url(GCS_BUCKET_NAME, gcs_object_name)
                urls.append(url)

            return {"message": "Images uploaded successfully.", "urls": urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Additional FastAPI routes and logic...
