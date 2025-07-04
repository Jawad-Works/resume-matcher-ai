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


def get_gemini_score_and_suggestions(jd: str, resume: str, user_type: str) -> dict:
    """Call Gemini API to score and suggest improvements based on user type."""
    api_key = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"

    # Input validation
    if not jd or not resume:
        return {"score": None, "suggestions": "Job description and resume are required"}

    if user_type not in ["HR", "candidate"]:
        return {
            "score": None,
            "suggestions": "User type must be either 'HR' or 'candidate'",
        }

    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        return {"score": None, "suggestions": "API key not configured"}

    # Generate user-specific prompt
    prompt = generate_user_specific_prompt(jd, resume, user_type)

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        print("Gemini raw response:", response.text)

        ai_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        ai_text_clean = clean_json_response(ai_text)

        try:
            result = json.loads(ai_text_clean)
            return validate_response(result, user_type)
        except json.JSONDecodeError as e:
            return {
                "score": None,
                "suggestions": f"AI response not valid JSON: {ai_text_clean} \n Error: {e}",
            }
    except requests.exceptions.Timeout:
        return {"score": None, "suggestions": "Request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        return {"score": None, "suggestions": f"Network error: {str(e)}"}
    except KeyError as e:
        return {
            "score": None,
            "suggestions": f"Unexpected API response format: {str(e)}",
        }
    except Exception as e:
        return {"score": None, "suggestions": f"AI call failed: {e}"}


def generate_user_specific_prompt(jd: str, resume: str, user_type: str) -> str:
    """Generate tailored prompts based on user type."""

    if user_type == "HR":
        return f"""
You are an expert HR consultant and recruitment specialist. Analyze the following job description and candidate's resume to provide a comprehensive evaluation for hiring decision-making.

Job Description:
{jd}

Candidate's Resume:
{resume}

**ANALYSIS REQUIRED:**

1. **OVERALL COMPATIBILITY SCORE (0-100)**: Provide a numerical score with detailed justification.

2. **DETAILED SECTION-BY-SECTION ANALYSIS**:
   - **Technical Skills Match**: Compare required vs. candidate's technical skills
   - **Experience Alignment**: Evaluate years of experience, industry relevance, and role progression
   - **Educational Background**: Assess education requirements vs. candidate's qualifications
   - **Cultural Fit Indicators**: Analyze soft skills, leadership experience, and team collaboration
   - **Domain Expertise**: Evaluate industry-specific knowledge and certifications

3. **RED FLAGS & CONCERNS**:
   - **Critical Gaps**: What essential requirements are missing?
   - **Experience Mismatches**: Where does the candidate fall short?
   - **Overqualification Risks**: Is the candidate overqualified and likely to leave?
   - **Career Progression Issues**: Any concerning patterns in job changes or career growth?

4. **HIRING RECOMMENDATION**:
   - **Immediate Decision**: Recommend hire/reject/interview with reasoning
   - **Risk Assessment**: Probability of success in the role
   - **Interview Focus Areas**: Key areas to probe during interviews
   - **Salary Negotiation Insights**: Market positioning based on candidate's profile

5. **COMPARATIVE ANALYSIS**:
   - How does this candidate compare to typical market standards for this role?
   - What percentage of job requirements does this candidate meet?

Respond in JSON format with keys: 
- "overall_score" (number 0-100)
- "technical_skills_score" (number 0-100)
- "experience_score" (number 0-100)
- "education_score" (number 0-100)
- "cultural_fit_score" (number 0-100)
- "domain_expertise_score" (number 0-100)
- "critical_gaps" (string)
- "red_flags" (string)
- "hiring_recommendation" (string)
- "interview_focus_areas" (string)
- "detailed_analysis" (string)
- "risk_assessment" (string)
"""

    else:  # candidate
        return f"""
You are an expert career coach and resume optimization specialist. Analyze the following job description and the candidate's resume to provide actionable improvement recommendations.

Job Description:
{jd}

Your Resume:
{resume}

**COMPREHENSIVE RESUME OPTIMIZATION ANALYSIS:**

1. **COMPATIBILITY SCORING**: Provide detailed scores for each section with explanations.

2. **SECTION-BY-SECTION IMPROVEMENT PLAN**:
   - **Technical Skills**: What skills to add, remove, or emphasize
   - **Professional Experience**: How to reframe accomplishments and responsibilities
   - **Education & Certifications**: Additional qualifications to pursue
   - **Keywords Optimization**: Missing keywords that ATS systems look for
   - **Quantifiable Achievements**: How to add metrics and numbers to demonstrate impact

3. **RESUME STRUCTURE & FORMATTING**:
   - **Content Organization**: How to restructure sections for better impact
   - **Bullet Point Optimization**: Rewrite suggestions for stronger action verbs
   - **Summary/Objective**: Craft a compelling professional summary
   - **Skill Prioritization**: Which skills to highlight prominently

4. **SKILL DEVELOPMENT ROADMAP**:
   - **Immediate Actions**: Skills you can develop in 1-3 months
   - **Short-term Goals**: 3-6 month development plan
   - **Long-term Strategy**: 6-12 month career development plan
   - **Certification Recommendations**: Specific certifications to pursue

5. **TAILORING STRATEGIES**:
   - **Job-Specific Customization**: How to modify resume for this specific role
   - **Industry Alignment**: Adjustments for industry standards
   - **ATS Optimization**: Formatting and keyword suggestions for applicant tracking systems

6. **COMPETITIVE POSITIONING**:
   - **Unique Value Proposition**: What makes you stand out
   - **Market Positioning**: How to position yourself against other candidates
   - **Salary Negotiation Preparation**: Strengthen your negotiation position

Respond in JSON format with keys:
- "overall_score" (number 0-100)
- "technical_skills_score" (number 0-100)
- "experience_score" (number 0-100)
- "education_score" (number 0-100)
- "resume_structure_score" (number 0-100)
- "ats_optimization_score" (number 0-100)
- "missing_keywords" (string)
- "skill_development_roadmap" (string)
- "resume_rewrite_suggestions" (string)
- "immediate_actions" (string)
- "certification_recommendations" (string)
- "competitive_advantages" (string)
- "detailed_improvement_plan" (string)
"""


def clean_json_response(text: str) -> str:
    """Clean JSON response from AI model."""
    text = text.strip()
    # Remove various markdown code block patterns
    patterns = ["```json", "```JSON", "```"]
    for pattern in patterns:
        if text.startswith(pattern):
            text = text[len(pattern) :].lstrip()
            break

    if text.endswith("```"):
        text = text[:-3].rstrip()

    return text


def validate_response(result: dict, user_type: str) -> dict:
    """Validate the AI response based on user type."""
    if not isinstance(result, dict):
        return {"score": None, "suggestions": "Invalid response format from AI"}

    # Check for required keys based on user type
    if user_type == "HR":
        required_keys = [
            "overall_score",
            "critical_gaps",
            "hiring_recommendation",
            "detailed_analysis",
        ]
    else:  # candidate
        required_keys = [
            "overall_score",
            "skill_development_roadmap",
            "detailed_improvement_plan",
        ]

    missing_keys = [key for key in required_keys if key not in result]
    if missing_keys:
        return {
            "score": result.get("overall_score"),
            "suggestions": f"Incomplete response. Missing: {', '.join(missing_keys)}. Available data: {str(result)}",
        }

    # Validate score ranges
    score_keys = [key for key in result.keys() if key.endswith("_score")]
    for key in score_keys:
        if result[key] is not None and not (0 <= result[key] <= 100):
            result[key] = None

    return result


@router.post("/score-upload")
async def score_upload(
    resume: UploadFile = File(...),
    jobDescription: str = Form(...),
    userType: str = Form(...),
):
    """API endpoint to score resume vs job description using Gemini with user-specific analysis."""

    # Validate user type
    if userType not in ["HR", "candidate"]:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Invalid user type. Must be either 'HR' or 'candidate'.",
            },
        )

    # Validate job description
    if not jobDescription or jobDescription.strip() == "":
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Job description cannot be empty.",
            },
        )

    # Extract resume text
    resume_text = ""
    filename = resume.filename or ""
    filename = filename.lower()

    try:
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
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error extracting text from file: {str(e)}",
            },
        )

    # Validate extracted resume text
    if not resume_text or resume_text.strip() == "":
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Could not extract text from resume. Please ensure the file is not corrupted.",
            },
        )

    # Call Gemini AI model with user type
    ai_result = get_gemini_score_and_suggestions(jobDescription, resume_text, userType)

    print("ai_result", ai_result)

    # Handle AI service errors
    if ai_result.get("score") is None and "failed" in ai_result.get("suggestions", ""):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": ai_result.get("suggestions", "AI service unavailable"),
            },
        )

    # Format response based on user type
    if userType == "HR":
        return {
            "success": True,
            "userType": userType,
            "data": {
                "overall_score": ai_result.get("overall_score"),
                "section_scores": {
                    "technical_skills": ai_result.get("technical_skills_score"),
                    "experience": ai_result.get("experience_score"),
                    "education": ai_result.get("education_score"),
                    "cultural_fit": ai_result.get("cultural_fit_score"),
                    "domain_expertise": ai_result.get("domain_expertise_score"),
                },
                "hiring_analysis": {
                    "critical_gaps": ai_result.get("critical_gaps"),
                    "red_flags": ai_result.get("red_flags"),
                    "hiring_recommendation": ai_result.get("hiring_recommendation"),
                    "interview_focus_areas": ai_result.get("interview_focus_areas"),
                    "risk_assessment": ai_result.get("risk_assessment"),
                },
                "detailed_analysis": ai_result.get("detailed_analysis"),
                # Keep legacy fields for backward compatibility
                "score": ai_result.get("overall_score"),
                "suggestions": ai_result.get("detailed_analysis"),
            },
        }
    else:  # candidate
        return {
            "success": True,
            "userType": userType,
            "data": {
                "overall_score": ai_result.get("overall_score"),
                "section_scores": {
                    "technical_skills": ai_result.get("technical_skills_score"),
                    "experience": ai_result.get("experience_score"),
                    "education": ai_result.get("education_score"),
                    "resume_structure": ai_result.get("resume_structure_score"),
                    "ats_optimization": ai_result.get("ats_optimization_score"),
                },
                "improvement_plan": {
                    "missing_keywords": ai_result.get("missing_keywords"),
                    "skill_development_roadmap": ai_result.get(
                        "skill_development_roadmap"
                    ),
                    "resume_rewrite_suggestions": ai_result.get(
                        "resume_rewrite_suggestions"
                    ),
                    "immediate_actions": ai_result.get("immediate_actions"),
                    "certification_recommendations": ai_result.get(
                        "certification_recommendations"
                    ),
                    "competitive_advantages": ai_result.get("competitive_advantages"),
                },
                "detailed_improvement_plan": ai_result.get("detailed_improvement_plan"),
                # Keep legacy fields for backward compatibility
                "score": ai_result.get("overall_score"),
                "suggestions": ai_result.get("detailed_improvement_plan"),
            },
        }


# Alternative endpoint for backward compatibility
@router.post("/score-upload-legacy")
async def score_upload_legacy(
    resume: UploadFile = File(...), jobDescription: str = Form(...)
):
    """Legacy API endpoint for backward compatibility - defaults to candidate user type."""
    return await score_upload(resume, jobDescription, "candidate")


# Additional endpoint for text-based input (no file upload)
@router.post("/score-text")
async def score_text(
    resume_text: str = Form(...),
    job_description: str = Form(...),
    user_type: str = Form(...),
):
    """API endpoint to score resume text vs job description using Gemini."""

    # Validate inputs
    if user_type not in ["HR", "candidate"]:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Invalid user type. Must be either 'HR' or 'candidate'.",
            },
        )

    if not job_description or job_description.strip() == "":
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Job description cannot be empty.",
            },
        )

    if not resume_text or resume_text.strip() == "":
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Resume text cannot be empty.",
            },
        )

    # Call Gemini AI model
    ai_result = get_gemini_score_and_suggestions(
        job_description, resume_text, user_type
    )

    print("ai_result", ai_result)

    # Handle AI service errors
    if ai_result.get("score") is None and "failed" in ai_result.get("suggestions", ""):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": ai_result.get("suggestions", "AI service unavailable"),
            },
        )

    # Format response based on user type (same logic as score_upload)
    if user_type == "HR":
        return {
            "success": True,
            "userType": user_type,
            "data": {
                "overall_score": ai_result.get("overall_score"),
                "section_scores": {
                    "technical_skills": ai_result.get("technical_skills_score"),
                    "experience": ai_result.get("experience_score"),
                    "education": ai_result.get("education_score"),
                    "cultural_fit": ai_result.get("cultural_fit_score"),
                    "domain_expertise": ai_result.get("domain_expertise_score"),
                },
                "hiring_analysis": {
                    "critical_gaps": ai_result.get("critical_gaps"),
                    "red_flags": ai_result.get("red_flags"),
                    "hiring_recommendation": ai_result.get("hiring_recommendation"),
                    "interview_focus_areas": ai_result.get("interview_focus_areas"),
                    "risk_assessment": ai_result.get("risk_assessment"),
                },
                "detailed_analysis": ai_result.get("detailed_analysis"),
                "score": ai_result.get("overall_score"),
                "suggestions": ai_result.get("detailed_analysis"),
            },
        }
    else:  # candidate
        return {
            "success": True,
            "userType": user_type,
            "data": {
                "overall_score": ai_result.get("overall_score"),
                "section_scores": {
                    "technical_skills": ai_result.get("technical_skills_score"),
                    "experience": ai_result.get("experience_score"),
                    "education": ai_result.get("education_score"),
                    "resume_structure": ai_result.get("resume_structure_score"),
                    "ats_optimization": ai_result.get("ats_optimization_score"),
                },
                "improvement_plan": {
                    "missing_keywords": ai_result.get("missing_keywords"),
                    "skill_development_roadmap": ai_result.get(
                        "skill_development_roadmap"
                    ),
                    "resume_rewrite_suggestions": ai_result.get(
                        "resume_rewrite_suggestions"
                    ),
                    "immediate_actions": ai_result.get("immediate_actions"),
                    "certification_recommendations": ai_result.get(
                        "certification_recommendations"
                    ),
                    "competitive_advantages": ai_result.get("competitive_advantages"),
                },
                "detailed_improvement_plan": ai_result.get("detailed_improvement_plan"),
                "score": ai_result.get("overall_score"),
                "suggestions": ai_result.get("detailed_improvement_plan"),
            },
        }
