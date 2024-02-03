from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
import httpx
import os
import tempfile

app = FastAPI()

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
    # Use a temporary directory for image downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Download images to the temporary directory
            downloader.download(query, limit=limit, output_dir=temp_dir, adult_filter_off=True, force_replace=False, timeout=60)
            
            # Notify Zapier for each downloaded image
            zapier_webhook_url = "https://zapier.com/editor/224766831/draft"
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                
                # Prepare data to send to Zapier
                data_to_send = {"query": query, "filename": filename, "filepath": file_path}
                
                # Send a POST request to Zapier with the data
                response = httpx.post(zapier_webhook_url, json=data_to_send)
                if response.status_code != 200:
                    print(f"Failed to notify Zapier for {filename}")
            
            return {"message": f"Successfully downloaded {limit} images for query '{query}' and notified Zapier."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
