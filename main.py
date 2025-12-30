import os
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import cloudinary
import cloudinary.uploader

# --------------------------------------------------
# Load .env locally
# --------------------------------------------------
if os.getenv("RENDER") != "true":
    from dotenv import load_dotenv
    load_dotenv()

# --------------------------------------------------
# Supabase setup
# --------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials missing")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------------------------------
# Cloudinary setup (explicit, no URL parsing)
# --------------------------------------------------
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET):
    raise RuntimeError("Cloudinary credentials missing")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# --------------------------------------------------
# FastAPI app
# --------------------------------------------------
app = FastAPI(title="Projects API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Health check
# --------------------------------------------------
@app.get("/")
def health():
    return {"status": "OK"}

# --------------------------------------------------
# Create project endpoint
# --------------------------------------------------
@app.post("/projects")
async def create_project(
    description: str = Form(...),
    images: List[UploadFile] = File(...)
):
    if not images:
        raise HTTPException(status_code=400, detail="No images uploaded")

    image_urls = []
    try:
        for image in images:
            image.file.seek(0)  # reset file pointer
            result = cloudinary.uploader.upload(
                image.file,
                folder="projects"
            )
            url = result.get("secure_url")
            if url:
                image_urls.append(url)

        if not image_urls:
            raise HTTPException(status_code=500, detail="Failed to upload images to Cloudinary")

        # Insert into Supabase
        data = {"description": description, "image_urls": image_urls}
        response = supabase.table("projects").insert(data).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Supabase insert failed")

        return {"message": "Project created successfully", "data": response.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------
# Test Cloudinary upload separately
# --------------------------------------------------
@app.post("/test-upload")
async def test_upload(image: UploadFile = File(...)):
    try:
        image.file.seek(0)
        result = cloudinary.uploader.upload(image.file)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))