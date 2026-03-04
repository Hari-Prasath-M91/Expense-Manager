# 💰 Expense Manager

A simple way to track where your money goes. Built with **FastAPI** on the backend and plain **Javascript/CSS** on the front. It uses **Cerebras (Llama 3.3)** to do the heavy lifting like reading emails and chatting about your spending.

## What it actually does

*   **Gmail Sync (The best part)**: It looks through your emails from the last 24 hours. It's smart enough to find UPI alerts, bank debits, and those random subscriptions you forgot about. You get to review them before they're saved.
*   **Smart Receipt OCR**: Upload a photo of your invoice. It automatically extracts all line items, their individual prices, and the global taxes using Tesseract + Cerebras AI.
*   **Expense Splitting**: Going out with friends? The OCR results let you assign specific line items to different people, and automatically calculates everyone's proportional share of the taxes and tips, leaving you with only your portion of the bill to save.
*   **Currency Conversion**: If you spend in USD or EUR, it'll automatically figure out the INR (or whatever you use) value using real-time rates.
*   **AI Chatbot**: You can just talk to it. "How much did I spend on Swiggy?" or "I just spent 200 on snacks" works fine.
*   **Dark Mode**: Works with your system settings.
*   **Auth**: It uses Google Login. We added refresh tokens so you don't have to keep logging in every hour.

## Google Cloud Setup

To get Gmail Sync working, you need a GCP project:

1.  **Create Project**: Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2.  **Enable APIs**: Enable the **Gmail API** in the "APIs & Services" dashboard.
3.  **OAuth Consent Screen**:
    *   Set User Type to **External**.
    *   Add the scope: `https://www.googleapis.com/auth/gmail.readonly`.
    *   Add your email as a **Test User** (since it'll be in testing mode).
4.  **Credentials**: Create "OAuth 2.0 Client ID" credentials (Web Application).
    *   **Authorized Redirect URI**: `http://localhost:10000/auth/callback` (or your production URL).
5.  **Env Vars**: Copy the **Client ID** and **Client Secret** to your `.env` file.

## OCR Setup

The application uses **Tesseract OCR** as the first-pass vision engine before sending the raw text to the Cerebras AI model for structured itemized extraction. 

1. **Install Tesseract**: 
   - **Windows**: Download the installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) and install it.
   - **Mac/Linux**: Install via Homebrew (`brew install tesseract`) or apt (`sudo apt-get install tesseract-ocr`).
2. **Set the Path**: If the Tesseract executable is not automatically available in your system's PATH, explicitly set the `TESSERACT_CMD` variable in your `.env` file pointing exactly to the executable file (e.g., `C:/Program Files/Tesseract-OCR/tesseract.exe`). Using forward slashes is recommended to avoid escape character issues on Windows.

## How to get it running

1.  **Setup `.env`**:
    ```bash
    DATABASE_URL=postgresql://...
    CEREBRAS_API_KEY=...
    GOOGLE_CLIENT_ID=...
    GOOGLE_CLIENT_SECRET=...
    SECRET_KEY=...
    TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe # Required for OCR receipts
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Start the Server**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload
    ```
    
## Tables
- `users`: Profile and currency settings.
- `expenses`: The actual transactions (with Gmail IDs to avoid dupes).
- `categories`: Simple ones like Food, Shopping, Bills.
- `gmail_scanned_ids`: A list of everything we've already looked at.
