from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader, APIKey
import time
from pytube import YouTube, Search

app = FastAPI()

API_KEY_NAME = "openai_gpt"
API_KEY = "AIzaSyA1YLgp6A9oS_TWxnadWbE6j_GCfvxX24Y"  # Replace with your actual API key

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

@app.post("/downloadAudio/")
async def download_audio(url: str, output_path: str, delay: int = 1, api_key: APIKey = Depends(get_api_key)):
    try:
        print(f"Downloading audio from: {url}")
        yt = YouTube(url)
        audio = yt.streams.filter(only_audio=True).first()
        if audio:
            audio.download(output_path=output_path)
            time.sleep(delay)  # Delay to avoid rate limiting
            return {"message": "Download successful"}
        else:
            raise HTTPException(status_code=404, detail="Audio not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/findSimilarSongs/")
async def find_similar_songs(url: str, max_results: int = 5, api_key: APIKey = Depends(get_api_key)):
    try:
        yt = YouTube(url)
        title = yt.title
        search_query = title.split('-')[0]  # Assuming "Artist - Song Title" format
        search_results = Search(search_query).results
        return [video.watch_url for video in search_results[:max_results]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
