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

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI. Use /download-images/ to download images."}


@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(10, description="The number of images to download")):
    try:
        # Your Zapier Webhook URL
        zapier_webhook_url = "https://zapier.com/editor/224766831/draft"

        # Using a temporary directory to save downloaded images
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader.download(query, limit=limit, output_dir=temp_dir, adult_filter_off=True, force_replace=False, timeout=60)
            
            # Assuming you want to notify Zapier after downloading images
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                
                # Prepare the data you want to send to Zapier
                data_to_send = {"query": query, "filename": filename, "filepath": file_path}
                
                # Send a POST request to Zapier with the data
                response = httpx.post(zapier_webhook_url, json=data_to_send)
                if response.status_code != 200:
                    raise Exception(f"Failed to notify Zapier for {filename}")

            return {"message": f"Successfully downloaded {limit} images for query '{query}' and notified Zapier."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
