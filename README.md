# YouTube MCP
[![smithery badge](https://smithery.ai/badge/@Prajwal-ak-0/youtube-mcp)](https://smithery.ai/server/@Prajwal-ak-0/youtube-mcp)

A Model Context Protocol (MCP) server for YouTube video analysis, providing tools to get transcripts, summarize content, and query videos using Gemini AI.

## Features

- 📝 **Transcript Extraction**: Get detailed transcripts from YouTube videos
- 📊 **Video Summarization**: Generate concise summaries using Gemini AI
- ❓ **Natural Language Queries**: Ask questions about video content
- 🔍 **YouTube Search**: Find videos matching specific queries
- 💬 **Comment Analysis**: Retrieve and analyze video comments

## Requirements

- Python 3.9+
- Google Gemini API key
- YouTube Data API key

## Running Locally

### Installing via Smithery

To install youtube-mcp for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@Prajwal-ak-0/youtube-mcp):

```bash
npx -y @smithery/cli install @Prajwal-ak-0/youtube-mcp --client claude
```

### Option 1: Direct Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Prajwal-ak-0/youtube-mcp
   cd youtube-mcp
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   YOUTUBE_API_KEY=your_youtube_api_key
   ```

4. Run the MCP server:
   ```bash
   python main.py
   ```

### Option 2: Using MCP CLI

1. Install the MCP CLI:
   ```bash
   pip install mcp
   ```

2. Create an `mcp.json` file in your project:
   ```json
   {
     "youtube": {
       "command": "uv",
       "args": [
         "--directory",
         "/absolute/path/to/youtube-mcp",
         "run",
         "main.py",
         "--transport",
         "stdio",
         "--debug"
       ]
     }
   }
   ```

3. Start the server with MCP:
   ```bash
   mcp run youtube
   ```

## Using with Docker

1. Build the Docker image:
   ```bash
   docker build -t youtube-mcp .
   ```

2. Run the container with your API keys:
   ```bash
   docker run -e GEMINI_API_KEY=your_gemini_api_key -e YOUTUBE_API_KEY=your_youtube_api_key youtube-mcp
   ```

## Deploying on Smithery

This MCP server can be deployed on [Smithery](https://smithery.ai) for easier access:

1. Add or claim your server on Smithery
2. Click "Deploy" on the Smithery Deployments tab
3. Provide your API keys when prompted

## Available Tools

- `youtube/get-transcript`: Get video transcript
- `youtube/summarize`: Generate a video summary
- `youtube/query`: Answer questions about a video
- `youtube/search`: Search for YouTube videos
- `youtube/get-comments`: Retrieve video comments
- `youtube/get-likes`: Get video like count

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
