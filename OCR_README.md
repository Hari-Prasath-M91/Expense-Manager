# AI-Powered OCR Expense Manager

An enterprise-grade, modular, N-Tier architecture AI-Powered Expense Manager focused on OCR-based receipt processing.

## 🏗 Architecture

The project uses a clean N-Tier layered architecture to ensure separation of concerns, high cohesion, and low coupling mapping to SOLID principles:

- **Presentation Layer (API):** Built using FastAPI (`backend/api/`), handling routing and endpoint definitions.
- **Business Logic Layer (Services):** 
  - OCR (`backend/services/ocr/`): Handles image preprocessing with OpenCV and text extraction using PyTesseract. Contains fallback parsing logic.
  - Expense (`backend/services/expense/`): Provides deterministic, keyword-mapping categorization.
  - Splitting (`backend/services/splitting/`): Precision-safe bill splitting algorithm calculator (Equal, Custom, Proportional, Item-based), using `Decimal` rounding.
- **Data Access Layer (Repositories):** Encapsulates the DB abstraction (`backend/repositories/`), isolating SQLAlchemy calls from the logic.
- **Persistence Layer:** Database operations modeled with SQLAlchemy using SQLite, enhanced with FTS5 for performant text searching.
- **Frontend Layer:** A lightweight Streamlit UI (`frontend/app.py`) for visually testing functionalities.

## 🚀 Setup Instructions

### 1. Requirements
Ensure you have Python 3.11+ installed.
You must have **Tesseract OCR** installed on your system.
- *Windows*: Download from UB Mannheim. Add it to your PATH.
- *Linux*: `sudo apt-get install tesseract-ocr`
- *macOS*: `brew install tesseract`

### 2. Environment Setup

Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r backend/requirements.txt
```

### 3. Create `.env`

Create a `.env` in the `backend/` directory or root:

```env
PROJECT_NAME="AI-Powered Expense Manager"
DATABASE_URL="sqlite:///./expense_manager.db"
# TESSERACT_CMD="C:/Program Files/Tesseract-OCR/tesseract.exe" # Uncomment if not in PATH on Windows
```

### 4. Running the Backend API

Start the FastAPI application:
```bash
uvicorn backend.main:app --reload --port 8000
```
- Interactive API Docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Running the Frontend UI

In a new terminal, launch the Streamlit frontend:
```bash
streamlit run frontend/app.py
```
- Access the frontend at: [http://localhost:8501](http://localhost:8501)

## 🧪 Testing

The system includes a robust test suite covering logic, models, endpoints, and OCR parsing heuristics.

Run the test suite via pytest:
```bash
pytest backend/tests/ -v
```

## 📊 Endpoints Overview

- `POST /api/v1/expenses/upload`: Uploads an image, runs OCR, categorizes it, and saves it.
- `POST /api/v1/expenses/{id}/split`: Dispatches exact split logic calculations.
- `POST /api/v1/search`: Trigger Full-Text-Search over SQLite FTS5 table index.
- `GET /api/v1/metrics/ocr`: Retrieves aggregate metrics like Processing Time and Automation stats.
