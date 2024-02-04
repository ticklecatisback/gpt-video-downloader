from fastapi import FastAPI, BackgroundTasks
from pytube import YouTube, Search
import os
import time
import uvicorn

app = FastAPI()

# Function to download video from YouTube given a video URL and an output path
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
            await time.sleep(delay)  # Async sleep
    except Exception as e:
        print(f"Error downloading video {yt.title}: {e}")

# Function to search YouTube and download videos based on the query
async def search_and_download_videos(search_query, output_path, max_results=5, delay=1):
    search_results = Search(search_query).results
    downloaded_count = 0
    for video in search_results:
        if downloaded_count >= max_results:
            break
        video_url = video.watch_url
        await download_video(video_url, output_path, delay)
        downloaded_count += 1

@app.post("/download_videos/")
async def download_videos(background_tasks: BackgroundTasks, search_query: str, max_results: int = 5, delay: int = 1):
    output_path = "downloaded_videos"
    os.makedirs(output_path, exist_ok=True)
    background_tasks.add_task(search_and_download_videos, search_query, output_path, max_results, delay)
    return {"message": "Download started", "search_query": search_query, "max_results": max_results, "delay": delay}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
