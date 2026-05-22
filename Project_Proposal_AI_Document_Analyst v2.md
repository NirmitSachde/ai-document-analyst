# Project Proposal: AI Document Analyst

## What It Is
A FastAPI web application that takes uploaded business documents (PDFs, CSVs, text files) and uses an LLM to automatically extract requirements, generate summaries, answer natural language questions, and perform change impact analysis across document versions.

## Architecture
1. **FastAPI backend** with file upload endpoint
2. **PDF/text parsing** using PyMuPDF (fitz) or pdfplumber
3. **LLM integration** via Google Gemini API (gemini-2.0-flash or gemini-1.5-pro)
4. **Four core features:**
   - **Document Summarizer**: Upload a doc, get a structured summary with key entities, dates, requirements and action items extracted
   - **Requirements Extractor**: Upload a business document (PRD, spec, user story), LLM parses it into structured JSON with requirement ID, description, priority, dependencies
   - **Q&A Interface**: Ask natural language questions about an uploaded document, LLM answers with citations to specific sections
   - **Change Impact Analysis**: Upload two versions of a document, system compares them, identifies modified requirements and generates a structured change log for stakeholder review
5. **SQLite database** storing uploaded documents, extracted requirements, and query history
6. **Simple HTML/JS frontend** (or Streamlit) for demo purposes
7. **Docker containerization**

## Tech Stack
- Python, FastAPI, SQLite
- Google Gemini API (google-generativeai package)
- PyMuPDF or pdfplumber for PDF parsing
- Pydantic for data validation
- Jinja2 templates or Streamlit for frontend
- Docker for containerization

## Build Order (fastest path)
1. FastAPI app scaffold with file upload endpoint (10 min)
2. PDF text extraction function (10 min)
3. Gemini API integration with structured prompts for summarization (15 min)
4. Requirements extraction endpoint returning structured JSON (15 min)
5. Q&A endpoint with document context (15 min)
6. Change impact analysis endpoint: accept two docs, diff, LLM generates change log (20 min)
7. SQLite storage for documents and extracted data (10 min)
8. Simple frontend with upload + display (15 min)
9. Docker containerization (10 min)
10. README with architecture diagram and usage (10 min)

## Total estimated build time: ~2.5 hours

## Resume Bullets
- "Built an AI-powered document analysis application using Python, FastAPI and the Gemini API (LLM) to automatically extract structured requirements, generate summaries and answer natural language questions from uploaded business documents"
- "Implemented SQLite storage for document metadata and extracted requirements with Pydantic validation and Docker containerization"
- "Developed a change impact analysis feature that compares document versions, identifies modified requirements and generates structured change logs for stakeholder review"

## GitHub Repo Name
`ai-document-analyst`

## Gemini API Setup
```python
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

response = model.generate_content("Your prompt here")
```

## Key Endpoints
- POST /upload - Upload a document
- GET /summary/{doc_id} - Get structured summary
- GET /requirements/{doc_id} - Get extracted requirements as JSON
- POST /qa - Ask a question about a document
- POST /compare - Upload two document versions, get change impact log
- GET /history - Query history and past extractions
