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
from pytube.exceptions import PytubeError

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


def download_video(video_url: str, output_path: str, filename: str):
    try:
        yt = YouTube(video_url)
        video_stream = yt.streams.get_highest_resolution()
        video_stream.download(output_path=output_path, filename=filename)
        return True
    except PytubeError as e:  # Use a general pytube exception or the correct specific one if available
        print(f"Error downloading video {video_url}: {e}")
        # Handle specific error messages if necessary, e.g., checking error message strings
        return False
    except Exception as e:
        print(f"Unexpected error downloading video {video_url}: {e}")
        return False


def cleanup_temp_dir(temp_dir):
    # Check if the directory exists
    if os.path.exists(temp_dir):
        # Iterate over all files and remove them
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Removes files and links
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Recursively removes directories
        # Finally, remove the empty directory
        os.rmdir(temp_dir)


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

    shutil.rmtree(temp_dir)  # Corrected to use shutil.rmtree to remove the directory and its contents
    print(f"Cleaned up temporary directory: {temp_dir}")


@app.post("/download-videos/")
async def download_videos(background_tasks: BackgroundTasks,
                          query: str = Query(..., description="The search query for downloading videos"),
                          limit: int = Query(1, description="The number of videos to download")):
    video_urls = await get_video_urls_for_query(query, limit)
    service = build_drive_service()

    # Create a temporary directory for videos and the zip file
    temp_dir = tempfile.mkdtemp()
    zip_filename = os.path.join(temp_dir, "videos.zip")

    try:
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for i, video_url in enumerate(video_urls):
                video_name = f"video_{i}.mp4"
                video_path = os.path.join(temp_dir, video_name)
                # Assuming you have a properly defined download_video function
                success = download_video(video_url, temp_dir, video_name)
                if success:
                    zipf.write(video_path, arcname=video_name)
                    print(f"Downloaded and added {video_name} to zip")
                else:
                    print(f"Failed to download {video_name}")
        print(f"Zip file created at {zip_filename}")

        # Queue the upload as a background task
        background_tasks.add_task(upload_file_background, service, zip_filename, temp_dir)
    except Exception as e:
        print(f"Error during video download or zip file creation: {e}")

    return {"message": "Processing videos. The zip file will be uploaded shortly."}
