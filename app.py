import os
import time
import streamlit as st
from dotenv import load_dotenv
from backend.db import DB
from backend.agents import DataAgent, ToolChoice
from backend.charts import auto_chart

load_dotenv()

st.set_page_config(page_title="Olist GenAI Data Agent", layout="wide")

@st.cache_resource(show_spinner=False)
def _get_db():
    db_path = os.environ.get("DB_PATH", "olist.db")
    return DB(db_path)

@st.cache_resource(show_spinner=False)
def _get_agent():
    return DataAgent(
        provider_api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENROUTER_API_KEY"),
        model_name=os.environ.get("MODEL_NAME", "gemini-1.5-flash"),
        max_rows=int(os.environ.get("MAX_ROWS", 500)),
        sql_timeout=int(os.environ.get("SQL_QUERY_TIMEOUT", 20)),
    )

db = _get_db()
agent = _get_agent()

st.title("🛒 Olist GenAI Data Agent")
st.caption("Ask questions about the Olist Brazilian e‑commerce dataset. Natural language → SQL → insights.")

with st.sidebar:
    st.subheader("Utilities")
    tool = st.radio("Mode", ["Ask data", "Explain term", "Translate query"], index=0)
    st.divider()
    st.subheader("Schema preview")
    if st.button("Show tables"):
        st.session_state["show_schema"] = True
    if st.session_state.get("show_schema"):
        st.code(db.describe_schema(), language="sql")

if "history" not in st.session_state:
    st.session_state.history = []

prompt = st.chat_input(placeholder="e.g., Top categories by revenue in 2018, show a bar chart")

for h in st.session_state.history:
    with st.chat_message(h["role"]):
        if h["type"] == "table":
            st.dataframe(h["content"])
        else:
            st.markdown(h["content"])

if prompt:
    st.chat_message("user").markdown(prompt)
    start = time.time()

    if tool == "Ask data":
        result = agent.answer_query(prompt, db)
    elif tool == "Explain term":
        result = agent.explain_term(prompt)
    else:
        result = agent.translate_query(prompt)

    elapsed = time.time() - start

    if result.kind == "text":
        with st.chat_message("assistant"):
            st.markdown(result.text)
        st.session_state.history.append({"role":"assistant","type":"text","content":result.text})

    elif result.kind == "table":
        with st.chat_message("assistant"):
            st.caption(f"SQL (safe):\n```sql\n{result.sql}\n```\nTime: {elapsed:.2f}s")
            st.dataframe(result.frame)
            chart = auto_chart(result.frame)
            if chart is not None:
                st.plotly_chart(chart, use_container_width=True)
            csv = result.frame.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, file_name="result.csv", mime="text/csv")
        st.session_state.history.append({"role":"assistant","type":"table","content":result.frame})

    elif result.kind == "error":
        with st.chat_message("assistant"):
            st.error(result.message)
            if result.sql:
                st.code(result.sql, language="sql")
        st.session_state.history.append({"role":"assistant","type":"text","content":result.message})
