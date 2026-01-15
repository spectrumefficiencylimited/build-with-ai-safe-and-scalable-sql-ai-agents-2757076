import streamlit as st
import pandas as pd
import ibis
import sys

# ------------------
# SQL AI Agent setup
# ------------------
sys.path.append("../")
from sql_ai_agent.SqlAgent import SqlAgent

models = {
    "GPT-OSS-20B":"gpt-oss:20B-UD-Q8_K_XL"
    "Devstral Small 2 24B Instruct": "ai/devstral-small:24B",
    "Granite-4.0-h-micro": "ai/granite-4.0-h-micro",
    "Llama-3.2":"ai/llama3.2:latest",
    "Gemma-3n": "ai/gemma3n",

}

fallback_models = {
    "GPT-OSS-20B":"gpt-oss:20B-UD-Q8_K_XL"
    "Devstral Small 2 24B Instruct": "ai/devstral-small:24B",
    "Granite-4.0-h-micro": "ai/granite-4.0-h-micro",
    "Llama-3.2":"ai/llama3.2:latest",
    "Gemma-3n": "ai/gemma3n",

}


base_url = "http://model-runner.docker.internal/engines/v1"
api_key = "docker"
model = "ai/granite-4.0-h-micro"
fallback_model = "ai/devstral-small:24B"
tbl_name = "air_traffic"

con = ibis.postgres.connect(
    user="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="my_db",
)

agent = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    fallback=True,
    fallback_model=fallback_model,
    tbl_name=tbl_name,
)

# ------------------
# Streamlit page setup
# ------------------
st.set_page_config(page_title="SQL AI Chatbot", layout="wide")
st.title("SQL AI Chatbot")

# ------------------
# Session state
# ------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------
# Render chat history
# ------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown("**Generated SQL:**")
            st.code(msg["query"], language="sql")

            if msg["data"] is not None and not msg["data"].empty:
                st.markdown("**Query result:**")
                st.dataframe(msg["data"])
        else:
            st.write(msg["content"])

# ------------------
# Chat input (Enter to send)
# ------------------
prompt = st.chat_input("Ask a question about the data")

if prompt:
    # Store user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Running query..."):
            try:
                response = agent.ask_question(
                    question=prompt,
                    verbose=False,
                )

                st.markdown("**Generated SQL:**")
                st.code(response.query, language="sql")

                if response.data is not None and not response.data.empty:
                    st.markdown("**Query result:**")
                    st.dataframe(response.data)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "query": response.query,
                        "data": response.data,
                    }
                )

            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "query": None,
                        "data": None,
                    }
                )
