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
import subprocess

app = FastAPI()


SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

executor = ThreadPoolExecutor(max_workers=5)

async def download_video(video_url, output_path):
    loop = asyncio.get_running_loop()
    # Using youtube-dl to download the video to the specified output path
    await loop.run_in_executor(executor, lambda: subprocess.run(['youtube-dl', video_url, '-o', f'{output_path}/%(title)s.%(ext)s'], check=True))

async def search_and_download_videos(search_query, output_path, max_results=5):
    # Perform a search using youtubesearchpython
    videos_search = VideosSearch(search_query, limit=max_results)
    results = videos_search.result()['result']
    
    # Prepare a list of tasks for downloading found videos
    tasks = []
    for video in results:
        video_url = video['link']
        tasks.append(download_video(video_url, output_path))
    
    # Execute all download tasks concurrently
    await asyncio.gather(*tasks)

async def zip_videos(directory):
    zip_path = os.path.join(directory, "videos.zip")
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(['zip', '-r', zip_path, '.'], cwd=directory, check=True)
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
        
        drive_url = await upload_to_drive(service, zip_filename)
        
    return {"message": "Zip file uploaded successfully.", "url": drive_url}
