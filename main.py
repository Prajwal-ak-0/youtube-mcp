import os
from typing import List, Dict
import aiohttp
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

"""
YouTube MCP: A Model Context Protocol (MCP) server for YouTube video analysis.
This MCP server provides tools to extract transcripts, search videos, analyze content,
and retrieve engagement metrics from YouTube videos using Google Gemini AI.

Environment Variables:
    - GEMINI_API_KEY: API key for Google Gemini AI services
    - YOUTUBE_API_KEY: API key for YouTube Data API v3
"""

# Load env vars from .env file for local development
load_dotenv()

mcp = FastMCP("openai-llm")

# Initialize variable to cache the Gemini client instance
genai_client = None

def get_genai_client():
    """
    Initialize and return the Gemini client, using API key from environment variables.
    
    This method ensures we're getting the latest environment variable value each time.
    
    Returns:
        genai.Client: Initialized Gemini client
        
    Raises:
        ToolError: If the GEMINI_API_KEY environment variable is not set
    """
    global genai_client
    
    # Get API key at runtime
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ToolError("GEMINI_API_KEY environment variable is not set")
        
    # Initialize client if not already done
    if genai_client is None:
        genai_client = genai.Client(api_key=gemini_api_key)
    
    return genai_client

@mcp.tool("youtube/get-transcript")
async def get_transcript(video_id: str, languages: List[str] = ["en"]) -> List[Dict]:
    """
    Retrieves the transcript/subtitles for a specified YouTube video.
    
    Uses the YouTube Transcript API to fetch time-coded transcripts in the requested languages.
    The transcripts include timing information, text content, and duration for each segment.
    
    Args:
        video_id (str): The YouTube video ID (11-character string from video URL)
        languages (List[str], optional): List of language codes to search for transcripts.
                                        Defaults to ["en"] (English).
    
    Returns:
        List[Dict]: A list containing a single dictionary with:
            - type: "transcript"
            - data: Dictionary containing video_id, segments (list of transcript entries), 
                   and languages requested
    
    Raises:
        ToolError: When transcript retrieval fails (video unavailable, no captions, etc.)
    """
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
    """
    Generates a concise summary of a YouTube video's content using Gemini AI.
    
    This tool first retrieves the video's transcript, then uses Google's Gemini 2.0 Flash
    model to create a structured summary of the key points discussed in the video.
    
    Args:
        video_id (str): The YouTube video ID to summarize
    
    Returns:
        List[Dict]: A list containing a single dictionary with:
            - type: "summary"
            - data: Dictionary containing video_id, summary text, and model used
    
    Raises:
        ToolError: When summarization fails (API key missing, transcript unavailable, etc.)
    """
    try:
        # Get Gemini client
        client = get_genai_client()
            
        transcript_data = await get_transcript(video_id)
        transcript = " ".join([t['text'] for t in transcript_data[0]['data']['segments']])
        
        response = client.models.generate_content(
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
    """
    Answers natural language questions about a YouTube video's content.
    
    This tool leverages Google's Gemini 2.0 Flash model to provide responses to questions
    based solely on the video's transcript. It extracts insights, facts, and context
    without watching the video itself.
    
    Args:
        video_id (str): The YouTube video ID to query
        query (str): Natural language question about the video content
    
    Returns:
        List[Dict]: A list containing a single dictionary with:
            - type: "query-response"
            - data: Dictionary containing video_id, the original query, 
                   the AI-generated response, and model used
    
    Raises:
        ToolError: When query fails (API key missing, transcript unavailable, etc.)
    """
    try:
        # Get Gemini client
        client = get_genai_client()
            
        transcript_data = await get_transcript(video_id)
        transcript = " ".join([t['text'] for t in transcript_data[0]['data']['segments']])
        
        response = client.models.generate_content(
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
    """
    Searches YouTube for videos matching a specific query and returns detailed metadata.
    
    This tool performs a two-step API process:
    1. First searches for videos matching the query
    2. Then fetches detailed metadata for each result (title, channel, views, etc.)
    
    Args:
        query (str): Search terms to find relevant videos
        max_results (int, optional): Maximum number of results to return. 
                                    Defaults to 5, capped at 50.
    
    Returns:
        List[Dict]: A list containing a single dictionary with:
            - type: "search-results"
            - data: Dictionary containing original query, list of video objects
                   with detailed metadata, and total result count
                   
    Video metadata includes:
        - id: YouTube video ID
        - title: Video title
        - description: Video description
        - thumbnail: URL to high-quality thumbnail
        - channel_title: Channel name
        - channel_id: YouTube channel ID
        - published_at: Publication timestamp
        - views: View count
        - likes: Like count
        - comments: Comment count
        - duration: Video duration in ISO 8601 format
    
    Raises:
        ToolError: When search fails (API key missing, API error, etc.)
    """
    try:
        # Get API key at runtime
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if not youtube_api_key:
            raise ToolError("YOUTUBE_API_KEY environment variable is not set")
            
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": query,
                    "maxResults": min(max_results, 50),
                    "type": "video",
                    "key": youtube_api_key
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
                    "key": youtube_api_key
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
    """
    Retrieves comments from a YouTube video using the YouTube Data API.
    
    This tool fetches top-level comments from a video's comment section,
    including author information, comment text, timestamps, and like counts.
    
    Args:
        video_id (str): The YouTube video ID to get comments from
        max_comments (int, optional): Maximum number of comments to retrieve.
                                     Defaults to 100, capped at 100 per API limits.
    
    Returns:
        List[Dict]: A list containing a single dictionary with:
            - type: "comments"
            - data: Dictionary containing video_id and a list of comment objects
                   
    Comment objects include metadata from the YouTube API such as:
        - authorDisplayName: Comment author's display name
        - authorProfileImageUrl: URL to author's profile picture
        - authorChannelUrl: URL to author's YouTube channel
        - textDisplay: Comment text with formatting
        - textOriginal: Plain text version of comment
        - likeCount: Number of likes on the comment
        - publishedAt: Comment publication timestamp
        - updatedAt: Last edit timestamp (if edited)
    
    Raises:
        ToolError: When comment retrieval fails (API key missing, comments disabled, etc.)
    """
    try:
        # Get API key at runtime
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if not youtube_api_key:
            raise ToolError("YOUTUBE_API_KEY environment variable is not set")
            
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": min(max_comments, 100),
                    "key": youtube_api_key
                }
            ) as response:
                data = await response.json()
                
        if 'error' in data:
            raise ToolError(f"YouTube API error: {data['error']['message']}")
                
        return [{
            "type": "comments",
            "data": {
                "video_id": video_id,
                "comments": [item['snippet']['topLevelComment']['snippet'] 
                            for item in data.get('items', [])],
                "total_count": len(data.get('items', []))
            }
        }]
    except Exception as e:
        raise ToolError(f"Comments error: {str(e)}")

@mcp.tool("youtube/get-likes")
async def get_likes(video_id: str) -> List[Dict]:
    """
    Retrieves the current like count for a specified YouTube video.
    
    This tool accesses the YouTube Data API to fetch the most up-to-date
    engagement statistics for a video, specifically focusing on like count.
    
    Args:
        video_id (str): The YouTube video ID to get likes for
    
    Returns:
        List[Dict]: A list containing a single dictionary with:
            - type: "stats"
            - data: Dictionary containing video_id and likes count
    
    Raises:
        ToolError: When like count retrieval fails (API key missing, video unavailable, etc.)
    """
    try:
        # Get API key at runtime
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if not youtube_api_key:
            raise ToolError("YOUTUBE_API_KEY environment variable is not set")
            
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "statistics",
                    "id": video_id,
                    "key": youtube_api_key
                }
            ) as response:
                data = await response.json()
                
        if 'error' in data:
            raise ToolError(f"YouTube API error: {data['error']['message']}")
                
        if not data.get('items'):
            raise ToolError(f"Video not found: {video_id}")
                
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