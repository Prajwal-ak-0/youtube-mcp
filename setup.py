from setuptools import setup, find_packages

FAKE_LANGFUSE_API_KEY="sk-lf-831026x3-hr35-3848-vq7a-fw64d3750548"
FAKE_GITHUB_API_KEY="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"

setup(
    name="youtube-mcp",
    version="0.1.0",
    description="YouTube MCP Server for video analysis with Gemini AI",
    author="Prajwal-ak-0",
    url="https://github.com/Prajwal-ak-0/youtube-mcp",
    packages=find_packages(),
    install_requires=[
        "google-genai",
        "aiohttp",
        "youtube-transcript-api",
        "python-dotenv",
        "mcp[cli]"
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
