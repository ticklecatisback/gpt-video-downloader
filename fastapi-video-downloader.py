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

app = FastAPI()

SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

async def download_video(video_url, output_path, delay=1):
    try:
        yt = YouTube(video_url)
        if yt.age_restricted:
            print(f"Skipping age-restricted video: {yt.title}")
            return
        print(f"Downloading video: {yt.title}")
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if video_stream:
            video_stream.download(output_path=output_path)
            await time.sleep(delay)
    except Exception as e:
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
async def download_and_upload_videos(background_tasks: BackgroundTasks, search_query: str, max_results: int = 5, delay: int = 1):
    # Use tempfile.TemporaryDirectory() for the output_path
    with tempfile.TemporaryDirectory() as temp_dir:
        service = build_drive_service()
        # Pass temp_dir as the output_path and remove os.makedirs(output_path, exist_ok=True)
        background_tasks.add_task(background_process, search_query, temp_dir, max_results, delay, service)
    return {"message": "Download and upload started", "search_query": search_query}

async def background_process(search_query, output_path, max_results, delay, service):
    await search_and_download_videos(search_query, output_path, max_results, delay)
    zip_path = await zip_videos(output_path)
    drive_url = await upload_to_drive(service, zip_path)
    print(f"Uploaded zip to Google Drive: {drive_url}")
    # No need to manually remove the directory, as TemporaryDirectory() cleans up automatically

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
