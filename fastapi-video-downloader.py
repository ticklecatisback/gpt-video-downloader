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
    videos_search = VideosSearch(query, limit=limit)
    await videos_search.next()  # Assuming this updates videos_search.results
    if videos_search.results:  # This line is pseudo-code; adjust based on actual attribute
        video_urls = [result['link'] for result in videos_search.results]  # Adjust based on actual structure
        return video_urls
    else:
        return []



def download_video(video_url: str):
    # Command to download video
    command = ['youtube-dl', video_url]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error downloading video: {e.output}")
        return None


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
    # You'll need to implement or adjust get_video_urls_for_query to fetch video URLs
    video_urls = await get_video_urls_for_query(query, limit=limit)
    service = build_drive_service()
    uploaded_urls = []

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_filename = os.path.join(temp_dir, "videos.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for i, video_url in enumerate(video_urls):
                file_content = download_video_in_memory(video_url)
                if not file_content:
                    continue  # Skip this video and proceed to the next
                
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
