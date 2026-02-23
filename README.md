# 💰 AI-Powered Personal Expense Manager — Database API

A PostgreSQL database schema + FastAPI REST endpoint layer for the AI-Powered Personal Expense Manager. Designed for deployment on **Render**.

## 🚀 Deploy to Render

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Once deployed, initialize the schema:

```bash
curl -X POST https://your-app.onrender.com/schema/initialize
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Swagger UI (interactive docs) |
| `GET` | `/health` | Health check |
| `GET` | `/info` | System info & DB status |
| `GET` | `/stats` | Database statistics |
| `POST` | `/schema/initialize` | Apply schema to database |
| `GET` | `/schema/tables` | List all tables |
| `GET` | `/schema/tables/{name}` | Describe table columns |
| `POST` | `/query` | Execute read-only SQL |
| `POST` | `/execute` | Execute write SQL |
| `POST` | `/users` | Create user |
| `GET` | `/users` | List users |
| `POST` | `/expenses` | Create expense |
| `GET` | `/expenses` | List/filter expenses |
| `GET` | `/analytics/summary/{user_id}` | Spending analytics |
| `GET` | `/analytics/top-vendors/{user_id}` | Top vendors |
| `POST` | `/budgets` | Create budget |
| `GET` | `/categories` | List categories |

## 🛠️ Local Development

```bash
docker build -t expense-manager-api .
docker run -p 10000:10000 -e DATABASE_URL=postgresql://user:pass@host:5432/dbname expense-manager-api
```

Then visit `http://localhost:10000` for the Swagger UI.

## 📊 Schema

42 tables across 15 modules — see [`schema/SCHEMA_DOCUMENTATION.md`](schema/SCHEMA_DOCUMENTATION.md) for full details.
