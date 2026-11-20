import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from pypdf import PdfReader
from google import genai

app = FastAPI(
    title="SIBOH CBE Smart Exam Generator",
    description="Upload a PDF lesson note or textbook and generate Kenyan CBE assessments automatically."
)

api_key = os.environ.get("GEMINI_API_KEY", "").strip()
client = genai.Client(api_key=api_key)

# Serve a complete, clean web interface at the main URL (/)
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SIBOH CBE Smart Exam Generator</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f7f6;
                color: #1f2937;
                margin: 0;
                padding: 20px;
                display: flex;
                justify-content: center;
            }
            .container {
                max-width: 760px;
                width: 100%;
                background: #ffffff;
                padding: 32px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            }
            .badge {
                display: inline-block;
                background: #e0f2fe;
                color: #0369a1;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 10px;
            }
            h1 {
                margin: 0 0 8px 0;
                color: #0f172a;
                font-size: 26px;
            }
            p.subtitle {
                color: #475569;
                margin-top: 0;
                margin-bottom: 24px;
                line-height: 1.5;
            }
            .upload-box {
                border: 2px dashed #94a3b8;
                border-radius: 10px;
                padding: 28px;
                text-align: center;
                background: #f8fafc;
                margin-bottom: 20px;
            }
            input[type="file"] {
                margin: 12px 0;
                font-size: 15px;
            }
            button {
                background-color: #0f766e;
                color: white;
                border: none;
                padding: 14px 28px;
                font-size: 16px;
                font-weight: 600;
                border-radius: 8px;
                cursor: pointer;
                width: 100%;
                transition: background 0.2s;
            }
            button:hover {
                background-color: #115e59;
            }
            button:disabled {
                background-color: #94a3b8;
                cursor: not-allowed;
            }
            #status {
                margin-top: 16px;
                font-weight: 600;
                color: #0369a1;
                text-align: center;
            }
            #result-card {
                display: none;
                margin-top: 28px;
                padding: 24px;
                background: #f8fafc;
                border-left: 4px solid #0f766e;
                border-radius: 8px;
                white-space: pre-wrap;
                line-height: 1.6;
                font-size: 15px;
            }
            .footer {
                margin-top: 28px;
                text-align: center;
                font-size: 13px;
                color: #64748b;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <span class="badge">KENYA CBE AI EDITION</span>
            <h1>SIBOH Smart Tutor & Exam Generator</h1>
            <p class="subtitle">Upload any PDF lesson note, handout, or curriculum guide to automatically generate Competency-Based Education (CBE) application questions and a teacher's marking scheme.</p>
            
            <div class="upload-box">
                <strong>Select a PDF Document</strong><br>
                <input type="file" id="pdfFile" accept=".pdf">
            </div>

            <button id="generateBtn" onclick="uploadAndGenerate()">Generate CBE Assessment</button>
            <div id="status"></div>
            <div id="result-card"></div>

            <div class="footer">
                Engineered by Maxwell Kibet • Powered by FastAPI & Google Gemini Cloud AI
            </div>
        </div>

        <script>
            async function uploadAndGenerate() {
                const fileInput = document.getElementById('pdfFile');
                const btn = document.getElementById('generateBtn');
                const status = document.getElementById('status');
                const resultCard = document.getElementById('result-card');

                if (!fileInput.files.length) {
                    alert("Please choose a PDF file first!");
                    return;
                }

                const formData = new FormData();
                formData.append("file", fileInput.files[0]);

                btn.disabled = true;
                btn.innerText = "Analyzing PDF & Generating Exam...";
                status.innerText = "Reading pages and consulting AI specialist (takes ~5-10 seconds)...";
                resultCard.style.display = "none";

                try {
                    const response = await fetch('/generate-exam', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.detail || "Something went wrong.");
                    }

                    status.innerText = `Done! Processed ${data.pages_read} page(s) from "${data.filename}"`;
                    resultCard.innerText = data.cbe_assessment;
                    resultCard.style.display = "block";
                } catch (err) {
                    status.innerText = "Error: " + err.message;
                } finally {
                    btn.disabled = false;
                    btn.innerText = "Generate CBE Assessment";
                }
            }
        </script>
    </body>
    </html>
    """

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
    2. Two competency-based application questions with a clear marking scheme.

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
