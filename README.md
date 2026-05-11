# ReviewScope

**Intelligent web platform for NLP-based customer review analysis.**

A SaaS-ready system that turns raw customer reviews (CSV / Excel / Google Takeout JSON) into actionable business insights using a modular NLP pipeline:

- **Sentiment analysis** with DistilBERT (rating-aware correction)
- **Aspect-Based Sentiment Analysis (ABSA)** - detects per-aspect polarity (price, service, quality, …)
- **Topic modeling** with BERTopic
- **Keyword extraction** with KeyBERT
- **Executive summary generator** ("top problems / top strengths")
- **Model evaluation** - Logistic Regression baseline vs DistilBERT, with confusion matrix
- **Multilingual support** - automatic language detection via langdetect

## Stack

| Layer        | Tech                                                   |
| ------------ | ------------------------------------------------------ |
| Frontend     | React 19 + Vite, Tailwind CSS, Recharts, lucide-react  |
| Auth         | Supabase Auth (email + password)                       |
| Backend      | FastAPI, Pydantic v2, asyncpg, ThreadPoolExecutor      |
| Database     | Supabase Postgres + Row Level Security                 |
| Storage      | Supabase Storage (private bucket per user)             |
| ML / NLP     | HuggingFace Transformers, sentence-transformers, BERTopic, KeyBERT, scikit-learn |
| Reports      | reportlab (PDF), CSV                                   |
| Deployment   | Docker, docker-compose, ready for Render/Railway/Fly   |

## Architecture

```
┌──────────────────────────┐         ┌──────────────────────────┐
│       React SPA          │  HTTPS  │      Supabase Auth        │
│  (Vite, Tailwind,        │ ──────▶ │  (email+password, JWT)   │
│   Recharts, supabase-js) │         └────────────┬─────────────┘
└──────┬───────────────────┘                      │
       │ Bearer JWT                               │
       ▼                                          │
┌──────────────────────────┐                      │
│    FastAPI Backend       │                      │
│  /api/projects           │  verify  ◀───────────┘
│  /api/analyses/*         │   JWT
│  /api/evaluation/*       │     ▲
│  /api/me/*               │     │
└──┬─────────────┬─────────┘     │
   │             │               │
   ▼             ▼               ▼
┌─────────┐  ┌──────────┐  ┌─────────────────────┐
│  NLP    │  │ Storage  │  │  Postgres (Supabase) │
│ Pipeline│  │ (files)  │  │  profiles, projects, │
│         │  │          │  │  analyses, results   │
└─────────┘  └──────────┘  └─────────────────────┘
```

## Project structure

```
src/
├── api/
│   ├── main.py             # FastAPI app factory
│   ├── auth.py             # Supabase JWT verification dependency
│   └── routes/
│       ├── me.py
│       ├── projects.py
│       ├── analyses.py     # upload + run + history
│       ├── exports.py      # PDF / CSV
│       └── evaluation.py   # LR vs BERT
├── database/
│   └── supabase_client.py  # admin + per-user clients
├── schemas/                # Pydantic v2 request/response models
├── services/
│   ├── project_service.py
│   ├── analysis_service.py
│   ├── storage_service.py
│   └── export_service.py
├── nlp/
│   ├── pipeline.py         # high-level orchestrator
│   ├── aspect_analyzer.py  # ABSA (lexicon + window scoring)
│   ├── language_detector.py
│   ├── summary_generator.py
│   └── model_evaluator.py  # LR vs DistilBERT
├── models/                 # low-level model wrappers (legacy)
│   ├── sentiment_analyzer.py
│   ├── topic_extractor.py
│   └── keyword_extractor.py
├── parsers/                # CSV / Excel / Google Takeout JSON
└── config.py               # pydantic-settings

frontend/
├── src/
│   ├── App.jsx             # router + AuthProvider
│   ├── lib/
│   │   ├── supabase.js
│   │   ├── auth.jsx        # auth context
│   │   └── api.js          # axios w/ JWT interceptor
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Projects.jsx
│   │   ├── ProjectDetail.jsx
│   │   ├── AnalysisDetail.jsx
│   │   ├── History.jsx
│   │   └── Evaluation.jsx
│   └── components/
│       ├── AppShell.jsx
│       ├── PrivateRoute.jsx
│       ├── SentimentChart.jsx
│       ├── AspectChart.jsx
│       ├── TopicsDisplay.jsx
│       ├── KeywordsCloud.jsx
│       └── InsightsPanel.jsx
└── package.json

supabase/
└── migrations/
    └── 001_initial_schema.sql  # tables + RLS + storage bucket
```

## Quick start

### 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com), create a free project (Frankfurt is closest to Ukraine).
2. **Save the database password** somewhere safe.
3. Open `supabase/migrations/001_initial_schema.sql` from this repo, copy the entire content, paste into **SQL Editor → New query**, click **Run**. This creates the schema, RLS policies, and the `reviews` storage bucket.

### 2. Backend

```powershell
cd C:\Work\Diplom
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# Fill in: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY,
# SUPABASE_JWT_SECRET, DATABASE_URL

python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI docs: <http://localhost:8000/docs>

### 3. Frontend

```powershell
cd C:\Work\Diplom\frontend
npm install

copy .env.example .env.local
# Fill in: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY,
# VITE_API_URL=http://localhost:8000

npm run dev
```

Open <http://localhost:3000> (configured in `frontend/vite.config.js`).

### 4. With Docker

```powershell
copy .env.example .env
# Fill all SUPABASE_* values + VITE_SUPABASE_*
docker compose up --build
```

- Backend on `:8000`
- Frontend on `:3000`

### 5. Deploy: Railway (API) + Vercel (frontend)

Production split: FastAPI stays on **[Railway](https://railway.app)** (`Dockerfile` at repo root), SPA on **[Vercel](https://vercel.com)** (`frontend/`). Database stays **hosted Supabase**.

**RAM:** Docker image pulls PyTorch, transformers, and NLP deps — Railway often needs **≥8 GB RAM** per instance or analyse runs risk OOM.

**Railway (backend)**

1. New project → deploy from GitHub → this repo. Root `.` default; `./Dockerfile` is used automatically. `railway.toml` extends healthcheck timeout for `/api/health`.
2. Set variables (names match `.env.example`):  
   `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`, plus:
   - `CORS_ORIGINS` — comma-separated list; include production UI, e.g. `https://your-app.vercel.app`
   - `CORS_ORIGIN_REGEX` (optional, for Vercel previews): `https://.*\.vercel\.app`
3. Copy the HTTPS service URL.

Railway injects `PORT`; the container listens on `$PORT`.

**Vercel (frontend)**

1. Import the same repo → **Root Directory: `frontend`**.
2. Environment variables (**Production**, and Preview if needed):  
   `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` = Railway origin **without** trailing slash — e.g. `https://xxx.up.railway.app` (do **not** add `/api`; the client builds `.../api/...`).
3. SPA rewrites live in `frontend/vercel.json`.

**Supabase Auth → URL configuration:** add production Vercel URL and optionally `https://*.vercel.app` for previews.

## API endpoints

| Method | Endpoint                                | Description                          |
| ------ | --------------------------------------- | ------------------------------------ |
| GET    | `/api/health`                           | Service health                       |
| GET    | `/api/me`                               | Current user profile                 |
| POST   | `/api/me/api-key/rotate`                | Rotate personal API key              |
| GET    | `/api/projects`                         | List user's projects                 |
| POST   | `/api/projects`                         | Create project                       |
| GET    | `/api/projects/{id}`                    | Get project                          |
| PATCH  | `/api/projects/{id}`                    | Update project                       |
| DELETE | `/api/projects/{id}`                    | Delete project (cascades)            |
| POST   | `/api/analyses/upload`                  | Upload review file (multipart)       |
| POST   | `/api/analyses/{id}/run`                | Run NLP pipeline on uploaded file    |
| GET    | `/api/analyses`                         | List analyses (filter by project_id) |
| GET    | `/api/analyses/{id}`                    | Get analysis + results               |
| DELETE | `/api/analyses/{id}`                    | Delete analysis & file               |
| GET    | `/api/analyses/{id}/export/csv`         | Export results as CSV                |
| GET    | `/api/analyses/{id}/export/pdf`         | Export results as PDF                |
| POST   | `/api/evaluation/run`                   | Compare LR vs BERT on a dataset      |
| GET    | `/api/evaluation/history`               | Past evaluations                     |

All authenticated endpoints expect `Authorization: Bearer <supabase_jwt>`.

## Database schema (Supabase)

```
auth.users            ← managed by Supabase Auth
profiles              ← extends users (full_name, plan, api_key)
projects              ← user_id (FK)
analyses              ← project_id, user_id, file_path, status
results               ← analysis_id (1:1, JSONB payload)
model_evaluations     ← user_id, model_name, accuracy/precision/recall/F1, confusion_matrix
storage.buckets       ← `reviews` (private, 50 MB limit)
```

RLS policies guarantee that users can only see their own rows.

## Scaling into a real SaaS

1. **Background workers** - replace the in-process ThreadPoolExecutor with a Celery/RQ worker pool consuming a Redis queue. Status pings via WebSocket.
2. **Model quantization** - use `optimum-onnxruntime` or `bitsandbytes` to halve memory and double inference speed for DistilBERT.
3. **Per-tenant quotas** - implement usage limits at API layer (reviews-per-month, MB-per-month) keyed on `profiles.plan`.
4. **Webhook integrations** - allow customers to push reviews directly from Stripe/Shopify/Google Maps via signed webhooks.
5. **Schedule streaming analyses** - cron/edge functions that re-run analyses for monitoring projects (negative-spike alerts).
6. **Aspect taxonomy editor** - let users edit their domain-specific aspect lexicon from the UI.
7. **Vector search** - store review embeddings in `pgvector` for "find similar reviews" and clustering UI.
8. **Stripe billing** - free → pro → enterprise tiers, metered usage via Stripe Customer Portal.

## Monetization ideas

- **Tiered subscription:**
  - Free - 1 project, 100 reviews/month, watermarked PDF
  - Pro - unlimited projects, 25k reviews/month, no watermark, ABSA, scheduled re-analysis
  - Enterprise - custom aspect lexicon, SSO, on-premise deploy, SLA
- **Per-API call billing** for businesses integrating ReviewScope into their internal CRM
- **Industry-specific lexicons** sold as add-ons (restaurants, hospitality, e-commerce, SaaS)
- **White-label dashboards** for marketing agencies analysing reviews on behalf of clients
- **Negative-spike alerting** as a paid notification channel (email, Slack, webhook)

## License

Gurzhii Maksym, 2026. All rights reserved.
