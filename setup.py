from setuptools import setup, find_packages

setup(
    name="youtube-mcp",
    version="0.1.0",
    description="YouTube MCP Server for video analysis with Gemini AI",
    author="Prajwal-ak-0",
    url="https://github.com/Prajwal-ak-0/youtube-mcp",
    packages=find_packages(),
    install_requires=[
        "mcp",
        "google-genai",
        "aiohttp",
        "youtube-transcript-api",
        "python-dotenv",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
) 