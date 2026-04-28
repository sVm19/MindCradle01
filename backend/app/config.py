import os
from dotenv import load_dotenv

load_dotenv()

# PocketBase
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090")

# NVIDIA AI
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_API_URL = os.getenv(
    "NVIDIA_API_URL",
    "https://integrate.api.nvidia.com/v1/chat/completions",
)
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
