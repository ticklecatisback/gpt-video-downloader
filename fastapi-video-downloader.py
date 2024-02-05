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

