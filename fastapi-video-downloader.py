from fastapi import FastAPI, BackgroundTasks
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

app = FastAPI()
task_results = {}

SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

executor = ThreadPoolExecutor(max_workers=5)

async def download_video(video_url, output_path):
    loop = asyncio.get_running_loop()
    yt = YouTube(video_url)
    print(f"Downloading video: {yt.title}")
    video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
    if video_stream:
        await loop.run_in_executor(executor, lambda: video_stream.download(output_path=output_path))
    else:
        print(f"No suitable video stream found for: {yt.title}")

async def search_and_download_videos(search_query, output_path, max_results=5):
    videos_search = VideosSearch(search_query, limit=max_results)
    results = videos_search.result()['result']
    
    tasks = []
    for video in results:
        video_url = f"https://www.youtube.com/watch?v={video['id']}"
        tasks.append(download_video(video_url, output_path))
    
    await asyncio.gather(*tasks)

async def zip_videos(directory):
    zip_path = os.path.join(directory, "videos.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)
    return zip_path

async def upload_to_drive(service, file_path):
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype='application/zip')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/uc?id={file.get('id')}"

@app.post("/upload-searched-videos/")
async def upload_searched_videos(search_query: str, max_results: int = 5):
    service = build_drive_service()
    with tempfile.TemporaryDirectory() as temp_dir:
        await search_and_download_videos(search_query, temp_dir, max_results)
        zip_filename = await zip_videos(temp_dir)
        
        # Upload the zip file to Google Drive
        file_metadata = {'name': os.path.basename(zip_filename)}
        media = MediaFileUpload(zip_filename, mimetype='application/zip')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        permission = {'type': 'anyone', 'role': 'reader'}
        service.permissions().create(fileId=file.get('id'), body=permission).execute()
        drive_url = f"https://drive.google.com/uc?id={file.get('id')}"

    return {"message": "Zip file uploaded successfully.", "url": drive_url}
