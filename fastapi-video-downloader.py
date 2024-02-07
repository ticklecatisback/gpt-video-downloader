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



def download_video(video_url: str, output_path: str, filename: str):
    try:
        yt = YouTube(video_url)
        video_stream = yt.streams.get_highest_resolution()
        # Specify the output path (directory) and filename separately
        video_stream.download(output_path=output_path, filename=filename)
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

from googleapiclient.http import MediaFileUpload

async def upload_file_background(service, file_path):
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype='application/zip')
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')

        # Set the file to be publicly readable (optional)
        permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(fileId=file_id, body=permission).execute()

        # Return or log the public URL
        public_url = f"https://drive.google.com/uc?id={file_id}"
        print(f"File uploaded successfully: {public_url}")
        return public_url
    except Exception as e:
        print(f"Failed to upload file: {e}")
        return None





@app.post("/download-videos/")
async def download_videos(background_tasks: BackgroundTasks, query: str = Query(..., description="The search query for downloading videos"), 
                          limit: int = Query(1, description="The number of videos to download")):
    video_urls = await get_video_urls_for_query(query, limit=limit)
    service = build_drive_service()
    background_tasks.add_task(upload_file_background, service, zip_filename)

    return {"message": "Processing videos. The zip file will be uploaded shortly."}

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_filename = os.path.join(temp_dir, "videos.zip")

        for i, video_url in enumerate(video_urls):  # Ensure you use video_url from the loop
            video_name = f"video_{i}.mp4"
            video_path = os.path.join(temp_dir, video_name)
            # Call download_video function here to actually download the video
            if download_video(video_url, temp_dir, video_name):  # Ensure directory and filename are correctly passed
                print(f"Downloaded {video_name}")
            else:
                print(f"Failed to download {video_name}")

        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for i, _ in enumerate(video_urls):
                video_name = f"video_{i}.mp4"
                video_path = os.path.join(temp_dir, video_name)
                if os.path.exists(video_path):
                    print(f"Adding {video_name} to zip")
                    zipf.write(video_path, arcname=video_name)
                else:
                    print(f"File does not exist: {video_path}")

        drive_url = await upload_to_drive(service, zip_filename)  # Upload the zip file to Google Drive

    return {"message": "Zip file with videos uploaded successfully.", "url": drive_url}
