# 💰 AI-Powered Personal Expense Manager

A minimalist, AI-driven expense management system built with **FastAPI** and **Vanilla JS**. It features an interactive chatbot powered by **Cerebras** for financial insights and automated transaction recording.

## 🚀 Key Features

- **Interactive Dashboard**: Modern, glassmorphic UI with real-time spending charts.
- **AI Chatbot**: powered by Cerebras (llama-3.3-70b). Ask about your spending, get tips, or log expenses by typing "I spent 500 on coffee".
- **Advanced Tracking**: Group transactions by date, filter by category, and manage monthly budgets.
- **Invoice Processing**: interactive upload zone for processing digital receipts.
- **Dark Mode**: Smooth transitions between Light and Dark themes.

## 📡 API Layer

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/`      | Serve Frontend |
| `GET`  | `/docs`  | Interactive Swagger Documentation |
| `POST` | `/chatbot`| AI financial assistant endpoint |
| `POST` | `/expenses`| Create a new transaction |
| `GET`  | `/expenses`| List and filter transactions |
| `GET`  | `/analytics/summary/{uid}` | Aggregate spending data |
| `POST` | `/schema/init` | Setup database schema |

## 🛠️ Setup & Deployment

1. **Environment Variables**: Create a `.env` file with:
   ```bash
   DATABASE_URL=postgresql://user:pass@host:port/dbname
   CEREBRAS_API_KEY=your_key_here
   ```
2. **Installation**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run Locally**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload
   ```
4. **Initialize DB**: Visit `/docs` and execute the `/schema/init` endpoint.

## 📊 Database
Utilizes a clean PostgreSQL schema with 4 core tables: `users`, `categories`, `expenses`, and `budgets`. See [`schema/SCHEMA_DOCUMENTATION.md`](schema/SCHEMA_DOCUMENTATION.md) for details.
