import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from pypdf import PdfReader
from google import genai

app = FastAPI(
    title="SIBOH CBE Smart Exam API",
    description="Upload a PDF lesson note or textbook and generate Kenyan CBE assessments automatically."
)

# Reads your API key securely from the Cloud Server's Environment Variables
api_key = os.environ.get("GEMINI_API_KEY", "").strip()
client = genai.Client(api_key=api_key)

@app.get("/")
def home():
    return {"status": "Online", "message": "SIBOH CBE AI Backend is live in the cloud!"}

@app.post("/generate-exam")
async def generate_exam(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a valid PDF file.")

    pdf_bytes = await file.read()
    reader = PdfReader(io.BytesIO(pdf_bytes))

    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from this PDF.")

    prompt = f"""
    You are a senior Kenyan Competency-Based Education (CBE) curriculum specialist.
    Based strictly on the uploaded document below, generate:
    1. A 3-bullet summary of the topic.
    2. Two competency-based application questions with a marking scheme.

    Document Content:
    {full_text[:15000]}
    """

    models_to_try = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return {
                "filename": file.filename,
                "pages_read": len(reader.pages),
                "model_used": model_name,
                "cbe_assessment": response.text
            }
        except Exception:
            continue

    raise HTTPException(status_code=503, detail="AI models are temporarily busy. Please try again.")
