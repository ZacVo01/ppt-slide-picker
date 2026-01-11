import pathlib
import uuid
import random
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pdf2image import convert_from_bytes

# ---------------------------
# Initialize app
# ---------------------------
app = FastAPI()

# Base directory
BASE_DIR = pathlib.Path(__file__).parent

# Folder for static slide images
SLIDE_DIR = BASE_DIR / "static" / "slides"
SLIDE_DIR.mkdir(parents=True, exist_ok=True)

# Simple in-memory session store
sessions = {}

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------
# Upload page
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def upload_page():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Upload PDF Slides</title></head>
    <body>
        <h1>Upload your PDF slides (2–20 pages)</h1>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <button type="submit">Upload</button>
        </form>
    </body>
    </html>
    """

# ---------------------------
# Upload handler
# ---------------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile):
    session_id = str(uuid.uuid4())
    content = await file.read()

    # Convert PDF to images
    images = convert_from_bytes(content)
    slide_paths = []

    session_folder = SLIDE_DIR / session_id
    session_folder.mkdir(parents=True, exist_ok=True)

    for i, img in enumerate(images):
        img_path = session_folder / f"slide_{i}.png"
        img.save(img_path)
        slide_paths.append(f"/static/slides/{session_id}/slide_{i}.png")

    if len(slide_paths) < 2 or len(slide_paths) > 20:
        return HTMLResponse("PDF must have 2–20 pages")

    slide_ids = list(range(len(slide_paths)))
    random.shuffle(slide_ids)

    sessions[session_id] = {
        "slides": slide_ids,
        "slide_images": slide_paths
    }

    return HTMLResponse(f'<script>window.location.href="/pick/{session_id}"</script>')

# ---------------------------
# Pick two slides
# ---------------------------
@app.get("/pick/{session_id}", response_class=HTMLResponse)
def pick(session_id: str):
    slides = sessions[session_id]["slides"]
    images = sessions[session_id]["slide_images"]

    if len(slides) == 1:
        return HTMLResponse(f'<script>window.location.href="/result/{session_id}"</script>')

    a, b = slides[0], slides[1]
    img_a, img_b = images[a], images[b]

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pick Your Slide</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            background-color: #f0f0f0;
            padding: 20px;
        }}
        h1 {{
            margin-bottom: 40px;
        }}
        .slide-container {{
            display: flex;
            justify-content: center;
            gap: 50px;
            flex-wrap: wrap;
        }}
        .slide-button {{
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 10px;
            background-color: #fff;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .slide-button:hover {{
            transform: scale(1.05);
            box-shadow: 0px 4px 15px rgba(0,0,0,0.2);
        }}
        img {{
            display: block;
            max-width: 400px;
            height: auto;
            margin-bottom: 10px;
        }}
        .slide-number {{
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <h1>Pick Your Slide</h1>
    <form action="/choose" method="post">
        <input type="hidden" name="session_id" value="{session_id}">
        <div class="slide-container">
            <button type="submit" class="slide-button" name="winner" value="{a}">
                <div class="slide-number">Slide {a + 1}</div>
                <img src="{img_a}">
            </button>
            <button type="submit" class="slide-button" name="winner" value="{b}">
                <div class="slide-number">Slide {b + 1}</div>
                <img src="{img_b}">
            </button>
        </div>
    </form>
</body>
</html>"""
    return HTMLResponse(html_content)

# ---------------------------
# Handle user choice
# ---------------------------
@app.post("/choose")
def choose(session_id: str = Form(...), winner: int = Form(...)):
    slides = sessions[session_id]["slides"]
    slides.remove(winner)
    sessions[session_id]["slides"] = slides
    random.shuffle(slides)
    return HTMLResponse(f'<script>window.location.href="/pick/{session_id}"</script>')

# ---------------------------
# Show final result
# ---------------------------
@app.get("/result/{session_id}", response_class=HTMLResponse)
def result(session_id: str):
    winner = sessions[session_id]["slides"][0]
    img_path = sessions[session_id]["slide_images"][winner]

    html_content = f"""<!DOCTYPE html>
<html>
<head><title>Final Slide Selected</title></head>
<body style="text-align:center; font-family:Arial, sans-serif; padding:40px; background:#f0f0f0;">
    <h1>🎉 Final Slide Selected</h1>
    <p>You picked slide number: {winner + 1}</p>
    <img src="{img_path}" style="max-width:960px; width:100%; height:auto; border:2px solid #007bff; border-radius:8px;">
</body>
</html>"""
    return HTMLResponse(html_content)