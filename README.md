# GenAI E‑commerce Data Agent (Olist)


A Streamlit-based GenAI agent that lets users chat with the Olist Brazilian E‑commerce dataset and get insights via natural language → SQL → tables/charts. Built to satisfy the Maersk AI/ML Campus Hiring Assignment.


## ✨ Features
- Natural language questions → **safe SQL** over a local **SQLite** database
- **Schema-aware prompting** (the model sees real tables/columns + examples)
- **Conversation memory** (follow‑ups, context retention)
- **Result visualizations** (auto bar/line charts when suitable)
- **Utilities**: explain terms, translate queries, export results to CSV
- Clean **Streamlit UI** with history, SQL preview, and latency timings


## 🧱 Architecture
```
Streamlit UI (app.py)
├─ Chat Orchestrator (backend/agents.py)
│ ├─ NL2SQL Planner (backend/nl2sql.py)
│ ├─ Safety / Guardrails (backend/nl2sql.py)
│ └─ Utilities: glossary/translate/summarize
├─ DB Layer (backend/db.py) → SQLite (olist.db)
└─ Charts (backend/charts.py) → Plotly


Data Loader (data/load_olist.py) → builds olist.db from Kaggle CSVs
```


## ⚙️ Stack
- Python 3.10+
- Streamlit, Pandas, SQLite3, SQLAlchemy
- Plotly (charts), sqlparse (format), pydantic (schemas)
- LLM via **Gemini** (Google AI Studio) or **OpenRouter** (Claude / GPT / Mistral)


## 🚀 Quickstart
1) **Clone & install**
```bash
python -m venv .venv && source .venv/bin/activate # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env # add your API key(s)
```


2) **Download Olist dataset** from Kaggle → unzip → note the folder path. Then build the SQLite DB:
```bash
python -m data.load_olist --csv_dir /path/to/olist_unzipped --out_db olist.db
```


3) **Run app**
```bash
streamlit run app.py
```
Open the local URL shown in the terminal.


### Environment variables (.env)
```
# Choose exactly one provider (Gemini recommended)
GEMINI_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
# Model names
MODEL_NAME=gemini-1.5-flash # or openrouter/anthropic/claude-3.5-sonnet, etc.
# Optional
MAX_ROWS=500
SQL_QUERY_TIMEOUT=20
```


## 🧪 Example questions
- "Which product category had the highest sales in 2018? Show top 10."
- "Average order value per month in 2017 vs 2018 — plot line chart"
- "Top 5 cities by number of unique customers"
- "Return rate by category (orders with status ‘canceled’ or ‘unavailable’)?"
- "Translate this to Portuguese and run: top categories by revenue"


## 🛡️ Safety & Guardrails
- Only allows **SELECT** statements, no DDL/DML
- Autolimit rows; blocks multiple statements; parameterizes filters
- Pretty SQL preview + error surfacing
