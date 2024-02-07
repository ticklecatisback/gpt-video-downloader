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

executor = ThreadPoolExecutor(max_workers=5)

async def get_video_urls_for_query(query: str, limit: int = 5):
    def _sync_search():
        videos_search = VideosSearch(query, limit=limit)
        videos_search.next()
        return [result['link'] for result in videos_search.result()['result']]

    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, _sync_search)
    return results



def download_video(video_url: str, output_path: str):
    try:
        yt = YouTube(video_url)
        # Get the highest resolution stream available
        video_stream = yt.streams.get_highest_resolution()
        # Download the video directly to the specified output path
        video_stream.download(output_path=output_path)
        return True
    except Exception as e:
        print(f"Error downloading video: {e}")
        return False

def download_video_in_memory(direct_video_url: str):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(direct_video_url, headers=headers)
        response.raise_for_status()  # Ensures we raise exceptions for bad responses
        return BytesIO(response.content)
    except requests.RequestException as e:
        print(f"Error downloading video content: {e}")
        return None


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




@app.post("/download-videos/")
async def download_videos(query: str = Query(..., description="The search query for downloading videos"), 
                          limit: int = Query(1, description="The number of videos to download")):
    video_urls = await get_video_urls_for_query(query, limit=limit)
    service = build_drive_service()

    with tempfile.TemporaryDirectory() as temp_dir:
        for i, video_url in enumerate(video_urls):
            video_name = f"video_{i}.mp4"  # Name of the video file
            video_path = os.path.join(temp_dir, video_name)
            # Use pytube to download the video directly to the specified path
            if not download_video(video_url, temp_dir):
                continue  # Skip this video if download failed
                
                video_name = f"video_{i}.mp4"  # Adjust the extension based on actual video format
                video_path = os.path.join(temp_dir, video_name)
                with open(video_path, 'wb') as video_file:
                    video_file.write(file_content.getbuffer())  # Write the video content to a file
                
                zipf.write(video_path, arcname=video_name)  # Add the video to the zip file

        # Upload the zip file to Google Drive with adjusted MIME type for videos
        file_metadata = {'name': 'videos.zip'}
        media = MediaFileUpload(zip_filename, mimetype='application/zip')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        permission = {'type': 'anyone', 'role': 'reader'}
        service.permissions().create(fileId=file.get('id'), body=permission).execute()
        drive_url = f"https://drive.google.com/uc?id={file.get('id')}"
        
        return {"message": "Zip file with videos uploaded successfully.", "url": drive_url}

# Adjust or add any necessary functions for video handling, such as get_video_urls_for_query and download_video_in_memory

# Your root function remains unchanged
