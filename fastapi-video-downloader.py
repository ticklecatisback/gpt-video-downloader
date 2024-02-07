from fastapi import FastAPI, BackgroundTasks, Query
from pytube import YouTube, Search
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import time
import uvicorn
import zipfile
import shutil
import tempfile
from uuid import uuid4
from youtubesearchpython import VideosSearch
import asyncio
from concurrent.futures import ThreadPoolExecutor
import subprocess
import requests
from io import BytesIO


app = FastAPI()


SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

async def get_video_urls_for_query(query: str, limit: int = 5):
    loop = asyncio.get_running_loop()
    videos_search = VideosSearch(query, limit=limit)
    await loop.run_in_executor(None, videos_search.next)  # Run in executor
    return [result['link'] for result in videos_search.result()['result']]

def download_video(video_url: str, output_path: str):
    yt = YouTube(video_url)
    video_stream = yt.streams.get_highest_resolution()
    video_stream.download(output_path=output_path)
    return os.path.join(output_path, video_stream.default_filename)

async def upload_file_background(service, file_path: str, temp_dir: str):
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype='application/zip')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')

    permission = {
        'type': 'anyone',
        'role': 'reader',
    }
    service.permissions().create(fileId=file_id, body=permission).execute()

    public_url = f"https://drive.google.com/uc?id={file_id}"
    print(f"File uploaded successfully: {public_url}")

    # Cleanup the temporary directory after upload
    os.remove(file_path)  # Remove the zip file first
    os.rmdir(temp_dir)  # Then remove the temporary directory
    print(f"Cleaned up temporary directory: {temp_dir}")

@app.post("/download-videos/")
async def download_videos(background_tasks: BackgroundTasks, query: str = Query(..., description="The search query for downloading videos"), limit: int = Query(1, description="The number of videos to download")):
    video_urls = await get_video_urls_for_query(query, limit)
    service = build_drive_service()

    # Create a persistent temporary directory
    temp_dir = tempfile.mkdtemp()
    zip_filename = os.path.join(temp_dir, "videos.zip")

    # Assuming you have a function to properly download videos and add them to the zip
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for i, video_url in enumerate(video_urls):
            video_name = f"video_{i}.mp4"  # Placeholder, replace with actual logic
            video_path = download_video(video_url, temp_dir)  # Adjust this call as needed
            zipf.write(video_path, arcname=video_name)

    # Add the upload task to run in the background, also pass temp_dir for cleanup
    background_tasks.add_task(upload_file_background, service, zip_filename, temp_dir)

    return {"message": "Processing videos. The zip file will be uploaded shortly."}
