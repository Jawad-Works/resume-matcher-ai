import json
import os
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import PyPDF2
import docx
import requests

router = APIRouter(prefix="/matching", tags=["matching"])


def extract_text_from_pdf(file):
    """
    Extract text from a PDF file.

    Args:
        file: A file object containing the PDF to extract text from

    Returns:
        str: The extracted text content from all pages of the PDF
    """
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_text_from_docx(file):
    """Extract text from a DOCX file."""
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])


def get_gemini_score_and_suggestions(jd: str, resume: str) -> dict:
    """Call Gemini API to score and suggest improvements."""
    api_key = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"

    prompt = f"""
You are an expert job-matching assistant. Given the following job description and resume, do the following:
1. Give a compatibility score between 0 and 100 (higher is better).
2. Suggest specific improvements to the resume to better match the job description.

Job Description:
{jd}

Resume:
{resume}

Respond in JSON with keys: \"score\" (number) and \"suggestions\" (string).
"""

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        print("Gemini raw response:", response.text)
        ai_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        # Robustly remove code block markers and 'json' label
        ai_text_clean = ai_text.strip()
        if ai_text_clean.startswith("```json"):
            ai_text_clean = ai_text_clean[len("```json") :].lstrip()
        if ai_text_clean.startswith("```"):
            ai_text_clean = ai_text_clean[len("```") :].lstrip()
        if ai_text_clean.endswith("```"):
            ai_text_clean = ai_text_clean[:-3].rstrip()
        try:
            result = json.loads(ai_text_clean)
            return result
        except Exception as e:
            return {
                "score": None,
                "suggestions": f"AI response not JSON: {ai_text_clean} \n Error: {e}",
            }
    except Exception as e:
        return {"score": None, "suggestions": f"AI call failed: {e}"}


@router.post("/score-upload")
async def score_upload(resume: UploadFile = File(...), jobDescription: str = Form(...)):
    """API endpoint to score resume vs job description using Gemini."""
    resume_text = ""
    filename = resume.filename or ""
    filename = filename.lower()
    if filename.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume.file)
    elif filename.endswith(".docx"):
        resume_text = extract_text_from_docx(resume.file)
    else:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Unsupported file type. Please upload a PDF or DOCX file.",
            },
        )

    # Call Gemini AI model
    ai_result = get_gemini_score_and_suggestions(jobDescription, resume_text)

    print("ai_result", ai_result)
    return {
        "success": True,
        "data": {
            "score": ai_result.get("score"),
            "suggestions": ai_result.get("suggestions"),
        },
    }
