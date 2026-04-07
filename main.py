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
@app.get("/projects")
def get_projects():
    try:
        response = supabase.table("projects").select("*").order("id", desc=True).execute()

        if response.data is None:
            raise HTTPException(status_code=500, detail="Failed to fetch projects")

        return {"data": response.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# --------------------------------------------------
# Delete project by ID
# --------------------------------------------------
@app.delete("/projects/{project_id}")
def delete_project(project_id: str):
    try:
        # 1. Get project
        response = supabase.table("projects").select("*").eq("id", project_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project = response.data
        image_urls = project.get("image_urls", [])

        # 2. Delete images from Cloudinary
        for url in image_urls:
            # Extract public_id safely
            # Example: https://res.cloudinary.com/xxx/image/upload/v123/projects/abc.jpg
            public_id = url.split("/upload/")[1].rsplit(".", 1)[0]
            cloudinary.uploader.destroy(public_id)

        # 3. Delete row from Supabase
        supabase.table("projects").delete().eq("id", project_id).execute()

        return {"message": "Project and images deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/gold")
async def create_gold_item(
    name: str = Form(...),
    type: str = Form(...),
    goldtype: str = Form(...),
    purity: str = Form(...),
    weight_gm: float = Form(...),
    gender: str = Form(...),
    images: List[UploadFile] = File(...)   # 👈 multiple files
):
    try:
        image_urls = []

        for image in images:
            upload_result = cloudinary.uploader.upload(
                image.file,
                folder="gold_collection"
            )
            image_urls.append(upload_result["secure_url"])

        data = {
            "name": name,
            "type": type,
            "goldtype": goldtype,
            "purity": purity,
            "weight_gm": weight_gm,
            "gender": gender,
            "image_urls": image_urls   # 👈 store list
        }

        res = supabase.table("gold_collection").insert(data).execute()

        return {
            "status": "success",
            "data": res.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# --------------------------------------------------
# GET: All Gold Items
# --------------------------------------------------
@app.get("/gold")
def get_all_gold_items():
    try:
        res = (
            supabase
            .table("gold_collection")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        return {
            "count": len(res.data),
            "data": res.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------
# DELETE: Remove Gold Item
# --------------------------------------------------
@app.delete("/gold/{gold_id}")
def delete_gold_item(gold_id: int):
    try:
        supabase.table("gold_collection").delete().eq("id", gold_id).execute()
        return {"status": "deleted", "id": gold_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

