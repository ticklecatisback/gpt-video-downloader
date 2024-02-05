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

app = FastAPI()
task_results = {}

SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

async def download_video(video_url, output_path, delay=1):
    try:
        yt = YouTube(video_url)
        # Check if the video is live
        if yt.is_live:
            print(f"Skipping live video: {yt.title}")
            return
        print(f"Downloading video: {yt.title}")
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if video_stream:
            video_stream.download(output_path=output_path)
            await time.sleep(delay)  # Async sleep
        else:
            print(f"No suitable video stream found for: {yt.title}")
    except Exception as e:
        if "This video is unavailable" in str(e):  # This error message might indicate an age-restricted video
            print(f"Skipping age-restricted or unavailable video: {yt.title}")
        else:
            print(f"Error downloading video {yt.title}: {e}")

async def search_and_download_videos(search_query, output_path, max_results=5, delay=1):
    search_results = Search(search_query).results
    downloaded_count = 0
    for video in search_results:
        if downloaded_count >= max_results:
            break
        video_url = video.watch_url
        await download_video(video_url, output_path, delay)
        downloaded_count += 1

async def zip_videos(directory):
    zip_path = os.path.join(directory, "videos.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for file in files:
                if file != "videos.zip":  # Avoid including the zip file itself
                    zipf.write(os.path.join(root, file), arcname=file)
    return zip_path

async def upload_to_drive(service, file_path):
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype='application/zip')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/uc?id={file.get('id')}"

@app.post("/download_and_upload_videos/")
async def download_video(video_url, output_path, delay=1):
    yt = None  # Initialize yt to None before the try block
    try:
        yt = YouTube(video_url)
        if yt.is_live:  # Assuming is_live checking is implemented elsewhere or removed
            print(f"Skipping live video: {yt.title}")
            return
        print(f"Downloading video: {yt.title}")
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if video_stream:
            video_stream.download(output_path=output_path)
            await time.sleep(delay)
        else:
            print(f"No suitable video stream found for: {yt.title}")
    except Exception as e:
        # Check if yt has been assigned before trying to access its attributes
        if yt:
            print(f"Error downloading video {yt.title}: {e}")
        else:
            print(f"Error initializing YouTube object for URL {video_url}: {e}")



async def background_process(task_id, search_query, output_path, max_results, delay, service, cleanup_dir=False):
    try:
        await search_and_download_videos(search_query, output_path, max_results, delay)
        zip_path = await zip_videos(output_path)
        drive_url = await upload_to_drive(service, zip_path)
        task_results[task_id] = drive_url  # Store the result using the task ID
    finally:
        if cleanup_dir:
            shutil.rmtree(output_path)

@app.get("/task_status/{task_id}")
async def task_status(task_id: str):
    if task_id in task_results:
        return {"status": "completed", "drive_url": task_results[task_id]}
    else:
        return {"status": "in_progress"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
