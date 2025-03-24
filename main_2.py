import os
import asyncio
from datetime import datetime
from typing import List, Any
import aiohttp
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from dotenv import load_dotenv

load_dotenv()

# Initialize MCP Server with latest features
mcp = FastMCP(
    name="YouTube AI Tools",
    description="Advanced YouTube analysis toolkit using MCP"
)

# Environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Initialize Gemini client
genai_client = None
if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)

# --- Resources ---
@mcp.resource("youtube/transcripts/{video_id}")
async def transcript_resource(video_id: str) -> str:
    """Provides the transcript for a YouTube video"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=["en"],
            preserve_formatting=True
        )
        return "\n".join([f"[{t['start']:.2f}-{t['start']+t['duration']:.2f}] {t['text']}" for t in transcript])
    except Exception as e:
        raise ValueError(f"Failed to retrieve transcript: {str(e)}")

@mcp.resource("youtube/video/{video_id}")
async def video_metadata_resource(video_id: str) -> str:
    """Provides metadata for a YouTube video"""
    try:
        if not YOUTUBE_API_KEY:
            return "YouTube API key not configured"
            
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": video_id,
                    "key": YOUTUBE_API_KEY
                }
            ) as response:
                data = await response.json()
                
        if 'error' in data:
            return f"YouTube API error: {data['error']['message']}"
                
        if not data.get('items'):
            return f"No video found with ID: {video_id}"
                
        item = data['items'][0]
        return f"""
            Title: {item['snippet']['title']}
            Channel: {item['snippet']['channelTitle']}
            Published: {item['snippet']['publishedAt']}
            Description: {item['snippet']['description']}
            Duration: {item['contentDetails']['duration']}
            Views: {item['statistics'].get('viewCount', '0')}
            Likes: {item['statistics'].get('likeCount', '0')}
            Comments: {item['statistics'].get('commentCount', '0')}
        """
    except Exception as e:
        return f"Error retrieving video metadata: {str(e)}"

# --- Prompts ---
@mcp.prompt("youtube/summarize")
async def summary_prompt(video_id: str) -> str:
    """Create a prompt template for summarizing YouTube video transcripts"""
    try:
        transcript = await transcript_resource(video_id)
        metadata = await video_metadata_resource(video_id)
        
        return f"""Summarize this YouTube video based on its transcript:

{metadata}

Transcript:
{transcript}

Please provide:
1. A concise 2-3 sentence summary
2. 3-5 key points in bullet form
3. Any technical details mentioned
4. The main takeaways from this video
"""
    except Exception as e:
        return f"Error creating summary prompt: {str(e)}"

@mcp.prompt("youtube/query")
async def query_prompt(video_id: str, query: str) -> str:
    """Create a prompt template for querying YouTube video transcripts"""
    try:
        transcript = await transcript_resource(video_id)
        metadata = await video_metadata_resource(video_id)
        
        return f"""Answer this question based ONLY on the content of this YouTube video:

{metadata}

Question: {query}

Transcript:
{transcript}

If the transcript doesn't contain information to answer this question, please state that clearly.
"""
    except Exception as e:
        return f"Error creating query prompt: {str(e)}"

# --- Tools ---
@mcp.tool("youtube/get-transcript")
async def get_transcript(video_id: str, languages: List[str] = ["en"]) -> Any:
    """Get YouTube video transcript with enhanced error handling"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=languages,
            preserve_formatting=True
        )
        return {
            "video_id": video_id,
            "segments": transcript,
            "languages": languages,
            "retrieved_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise ToolError(f"Failed to retrieve transcript: {str(e)}")

@mcp.tool("youtube/summarize")
async def summarize_transcript(video_id: str) -> Any:
    """Generate AI summary of YouTube video transcript"""
    try:
        # Get the summarization prompt
        prompt_text = await summary_prompt(video_id)
        
        global genai_client
        if not genai_client:
            raise ToolError("GEMINI_API_KEY environment variable is not set or client not initialized")
        
        # Use Gemini to summarize
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_text
        )
        
        if not response.text:
            raise ToolError("No summary generated - empty response from Gemini")
        
        return {
            "video_id": video_id,
            "summary": response.text,
            "model": "gemini-2.0-flash"
        }
    except Exception as e:
        raise ToolError(f"Summarization failed: {str(e)}")

@mcp.tool("youtube/query")
async def query_transcript(video_id: str, query: str) -> Any:
    """Answer questions about YouTube video content"""
    try:
        # Get the query prompt
        prompt_text = await query_prompt(video_id, query)
        
        global genai_client
        if not genai_client:
            raise ToolError("GEMINI_API_KEY environment variable is not set or client not initialized")
        
        # Use Gemini to answer query
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_text
        )
        
        if not response.text:
            raise ToolError("No response generated - empty response from Gemini")
        
        return {
            "video_id": video_id,
            "query": query,
            "response": response.text,
            "model": "gemini-2.0-flash"
        }
    except Exception as e:
        raise ToolError(f"Query failed: {str(e)}")

@mcp.tool("youtube/search")
async def search_videos(query: str, max_results: int = 5) -> Any:
    """Search YouTube for videos matching a query"""
    try:
        if not YOUTUBE_API_KEY:
            raise ToolError("YOUTUBE_API_KEY environment variable is not set")
            
        async with aiohttp.ClientSession() as session:
            # Initial search
            search_params = {
                "part": "snippet",
                "q": query,
                "maxResults": min(max_results, 50),
                "type": "video",
                "key": YOUTUBE_API_KEY
            }
            
            async with session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=search_params
            ) as response:
                search_data = await response.json()
                
            if 'error' in search_data:
                raise ToolError(f"YouTube API error: {search_data['error']['message']}")
                    
            video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]
            
            if not video_ids:
                return {
                    "query": query,
                    "videos": [],
                    "total_results": 0
                }
            
            # Get detailed video info
            async with session.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "key": YOUTUBE_API_KEY
                }
            ) as response:
                videos_data = await response.json()
            
            # Process results
            videos = []
            for item in videos_data.get('items', []):
                videos.append({
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'stats': {
                        'views': item['statistics'].get('viewCount', '0'),
                        'likes': item['statistics'].get('likeCount', '0'),
                        'comments': item['statistics'].get('commentCount', '0')
                    },
                    'duration': item['contentDetails']['duration'],
                    'channel': {
                        'title': item['snippet']['channelTitle'],
                        'id': item['snippet']['channelId']
                    },
                    'published_at': item['snippet']['publishedAt']
                })
            
            return {
                "query": query,
                "videos": videos,
                "total_results": len(videos)
            }
            
    except Exception as e:
        raise ToolError(f"Search failed: {str(e)}")

@mcp.tool("youtube/get-comments")
async def get_comments(video_id: str, max_comments: int = 100) -> Any:
    """Get YouTube video comments"""
    try:
        if not YOUTUBE_API_KEY:
            raise ToolError("YOUTUBE_API_KEY environment variable is not set")
            
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
                
            if 'error' in data:
                raise ToolError(f"YouTube API error: {data['error']['message']}")
                
            return {
                "video_id": video_id,
                "comments": [
                    {
                        "author": item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        "text": item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        "published_at": item['snippet']['topLevelComment']['snippet']['publishedAt'],
                        "likes": item['snippet']['topLevelComment']['snippet']['likeCount']
                    }
                    for item in data.get('items', [])
                ]
            }
    except Exception as e:
        raise ToolError(f"Failed to get comments: {str(e)}")

if __name__ == "__main__":
    # Run the MCP server using stdio transport (required for mcp dev command)
    asyncio.run(mcp.run_stdio_async())
