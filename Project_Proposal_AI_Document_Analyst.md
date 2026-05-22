# Project Proposal: AI Document Analyst

## What It Is
A FastAPI web application that takes uploaded business documents (PDFs, CSVs, text files) and uses an LLM to automatically extract requirements, generate summaries, identify key entities, and answer natural language questions about the document content.

## Why This Aligns with AbbVie BSA-AI Role
The JD asks for: requirements gathering, AI applications, translating business needs into functional specs, data modeling, report generation from databases, system documentation. This project does all of that with an LLM backbone.

## Architecture
1. **FastAPI backend** with file upload endpoint
2. **PDF/text parsing** using PyMuPDF (fitz) or pdfplumber
3. **LLM integration** via Anthropic Claude API (claude-sonnet-4-20250514)
4. **Three core features:**
   - **Document Summarizer**: Upload a doc, get a structured summary with key entities, dates, requirements, and action items extracted
   - **Requirements Extractor**: Upload a business document (PRD, spec, user story), LLM parses it into structured JSON with requirement ID, description, priority, dependencies
   - **Q&A Interface**: Ask natural language questions about an uploaded document, LLM answers with citations to specific sections
5. **SQLite database** storing uploaded documents, extracted requirements, and query history
6. **Simple HTML/JS frontend** (or Streamlit) for demo purposes

## Tech Stack
- Python, FastAPI, SQLite
- Anthropic Claude API (claude-sonnet-4-20250514)
- PyMuPDF or pdfplumber for PDF parsing
- Pydantic for data validation
- Jinja2 templates or Streamlit for frontend
- Docker for containerization

## Build Order (fastest path)
1. FastAPI app scaffold with file upload endpoint (10 min)
2. PDF text extraction function (10 min)
3. Claude API integration with structured prompts for summarization (15 min)
4. Requirements extraction endpoint returning structured JSON (15 min)
5. Q&A endpoint with document context (15 min)
6. SQLite storage for documents and extracted data (10 min)
7. Simple frontend with upload + display (15 min)
8. Docker containerization (10 min)
9. README with architecture diagram and usage (10 min)

## Total estimated build time: ~2 hours

## Resume Bullet (once built)
"Built an AI-powered document analysis application using Python, FastAPI and the Claude API to automatically extract structured requirements, generate summaries and answer natural language questions from uploaded business documents, with SQLite storage and Docker deployment"

## GitHub Repo Name Suggestion
`ai-document-analyst`
