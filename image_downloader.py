from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
import logging
import os
import tempfile

app = FastAPI()
logging.basicConfig(level=logging.INFO)

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
    return HTMLResponse(html)

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(10, description="The number of images to download")):
    try:
        logging.info(f"Downloading {limit} images for query: {query}")
        # Use the temporary directory for image download
        temp_dir = tempfile.gettempdir()
        output_dir = os.path.join(temp_dir, "downloaded_images")
        os.makedirs(output_dir, exist_ok=True)

        downloader.download(query, limit=limit, output_dir=output_dir, adult_filter_off=True, force_replace=False, timeout=60)
        return {"message": f"Successfully downloaded {limit} images for query '{query}' in the temporary directory."}
    except Exception as e:
        logging.error(f"Failed to download images: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
