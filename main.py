import os
from typing import List, Dict
import aiohttp
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("openai-llm")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

genai_client = None  # Initialize genai_client here

@mcp.tool("youtube/get-transcript")
async def get_transcript(video_id: str, languages: List[str] = ["en"]) -> List[Dict]:
    """Get YouTube video transcript with MCP error handling"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=languages,
            preserve_formatting=True
        )
        return [{
            "type": "transcript",
            "data": {
                "video_id": video_id,
                "segments": transcript,
                "languages": languages
            }
        }]
    except Exception as e:
        raise ToolError(f"Transcript error: {str(e)}")

@mcp.tool("youtube/summarize")
async def summarize_transcript(video_id: str) -> List[Dict]:
    """Summarize transcript using Gemini Flash"""
    try:
        global genai_client
        
        if not GEMINI_API_KEY:
            raise ToolError("GEMINI_API_KEY environment variable is not set")
            
        if genai_client is None:
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
            
        transcript_data = await get_transcript(video_id)
        transcript = " ".join([t['text'] for t in transcript_data[0]['data']['segments']])
        
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{
                "role": "user",
                "parts": [{
                    "text": f"Summarize this YouTube video transcript in 3-5 bullet points:\n\n{transcript}"
                }]
            }],
        )
        
        if not response.text:
            raise ToolError("No summary generated - empty response from Gemini")
            
        return [{
            "type": "summary",
            "data": {
                "video_id": video_id,
                "summary": response.text,
                "model": "gemini-2.0-flash"
            }
        }]
    except Exception as e:
        raise ToolError(f"Summarization error: {str(e)}")

@mcp.tool("youtube/query")
async def query_transcript(video_id: str, query: str) -> List[Dict]:
    """Answer natural language queries about a YouTube video using its transcript"""
    try:
        global genai_client
        
        if not GEMINI_API_KEY:
            raise ToolError("GEMINI_API_KEY environment variable is not set")
            
        if genai_client is None:
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
            
        transcript_data = await get_transcript(video_id)
        transcript = " ".join([t['text'] for t in transcript_data[0]['data']['segments']])
        
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{
                "role": "user",
                "parts": [{
                    "text": f"""The following is a transcript from a YouTube video:
                        Transcript:
                        {transcript}

                        Based only on the information in this transcript, please answer the following question:
                        {query}

                        If the transcript doesn't contain information to answer this question, please state that clearly.
                    """
                }]
            }],
        )
        
        if not response.text:
            raise ToolError("No response generated - empty response from Gemini")
            
        return [{
            "type": "query-response",
            "data": {
                "video_id": video_id,
                "query": query,
                "response": response.text,
                "model": "gemini-2.0-flash"
            }
        }]
    except Exception as e:
        raise ToolError(f"Query error: {str(e)}")

@mcp.tool("youtube/search")
async def search_videos(query: str, max_results: int = 5) -> List[Dict]:
    """Search YouTube for videos matching a query and return metadata"""
    try:
        if not YOUTUBE_API_KEY:
            raise ToolError("YOUTUBE_API_KEY environment variable is not set")
            
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": query,
                    "maxResults": min(max_results, 50),
                    "type": "video",
                    "key": YOUTUBE_API_KEY
                }
            ) as response:
                search_data = await response.json()
                
        if 'error' in search_data:
            raise ToolError(f"YouTube API error: {search_data['error']['message']}")
                
        video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]
        
        if not video_ids:
            return [{
                "type": "search-results",
                "data": {
                    "query": query,
                    "videos": [],
                    "total_results": 0
                }
            }]
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "key": YOUTUBE_API_KEY
                }
            ) as response:
                videos_data = await response.json()
        
        videos = []
        for item in videos_data.get('items', []):
            video = {
                'id': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'thumbnail': item['snippet']['thumbnails']['high']['url'],
                'channel_title': item['snippet']['channelTitle'],
                'channel_id': item['snippet']['channelId'],
                'published_at': item['snippet']['publishedAt'],
                'views': item['statistics'].get('viewCount', '0'),
                'likes': item['statistics'].get('likeCount', '0'),
                'comments': item['statistics'].get('commentCount', '0'),
                'duration': item['contentDetails']['duration']
            }
            videos.append(video)
        
        return [{
            "type": "search-results",
            "data": {
                "query": query,
                "videos": videos,
                "total_results": len(videos)
            }
        }]
    
    except Exception as e:
        raise ToolError(f"Search error: {str(e)}")

@mcp.tool("youtube/get-comments")
async def get_comments(video_id: str, max_comments: int = 100) -> List[Dict]:
    """Get video comments using YouTube Data API"""
    try:
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": min(max_comments, 100),
                    "key": YOUTUBE_API_KEY
                }
            ) as response:
                data = await response.json()
                
        return [{
            "type": "comments",
            "data": {
                "video_id": video_id,
                "comments": [item['snippet']['topLevelComment']['snippet'] 
                            for item in data.get('items', [])]
            }
        }]
    except Exception as e:
        raise ToolError(f"Comments error: {str(e)}")

@mcp.tool("youtube/get-likes")
async def get_likes(video_id: str) -> List[Dict]:
    """Get video like count"""
    try:
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "statistics",
                    "id": video_id,
                    "key": YOUTUBE_API_KEY
                }
            ) as response:
                data = await response.json()
                
        return [{
            "type": "stats",
            "data": {
                "video_id": video_id,
                "likes": data['items'][0]['statistics'].get('likeCount', 0)
            }
        }]
    except Exception as e:
        raise ToolError(f"Likes error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())