from shiny import App, ui, render, reactive
import sys
import ibis
import pandas as pd

sys.path.append("../")
from sql_ai_agent.SqlAgent import SqlAgent

# ------------------
# Settings
# ------------------
base_url = "http://model-runner.docker.internal/engines/v1"
api_key = "docker"
temperature = 0
model = "ai/llama3.2:latest"
# model = "ai/devstral-small:24B"
model = "ai/granite-4.0-h-micro"
# model = "ai/gemma3n"
fallback_model = "ai/gemma3n"
fallback_model = "ai/granite-4.0-h-micro"
fallback_model = "ai/devstral-small:24B"
tbl_name = "air_traffic"
max_token = 10000


# ------------------
# Data
# ------------------
con = ibis.postgres.connect(
    user="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="my_db",
)

# ------------------
# Agent
# ------------------
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
# UI
# ------------------
app_ui = ui.page_fluid(
    ui.h2("SQL AI Chatbot"),
    ui.card(
        ui.output_ui("chat_history"),
        ui.output_table("query_result"),
        ui.input_text_area(
            "user_message",
            label=None,
            placeholder="Type your question here...",
            rows=3,
        ),
        ui.input_action_button("send", "Send"),
    ),
)


# ------------------
# Server
# ------------------
def server(input, output, session):
    chat = reactive.Value([])
    result_df = reactive.Value(pd.DataFrame())

    @reactive.effect
    @reactive.event(input.send)  # 👈 ONLY triggers on button click
    def _():
        question = input.user_message()
        if not question.strip():
            return

        messages = chat.get()
        messages.append({"role": "user", "content": question})

        try:
            response = agent.ask_question(question=question, verbose=False)

            if response.data is not None:
                result_df.set(response.data)
            else:
                result_df.set(pd.DataFrame())

            assistant_msg = (
                f"Here is the SQL query I generated:\n\n```sql\n{response.query}\n```"
            )

        except Exception as e:
            result_df.set(pd.DataFrame())
            assistant_msg = f"⚠️ Error:\n{str(e)}"

        messages.append({"role": "assistant", "content": assistant_msg})
        chat.set(messages)

        # Clear input after submit
        ui.update_text_area("user_message", value="")

    # ------------------
    # Chat history
    # ------------------
    @output
    @render.ui
    def chat_history():
        bubbles = []

        for m in chat.get():
            style = (
                "background-color:#f8f9fa; padding:8px; margin:6px; border-radius:6px;"
                if m["role"] == "assistant"
                else "background-color:#d1e7dd; padding:8px; margin:6px; border-radius:6px; text-align:right;"
            )

            bubbles.append(
                ui.div(
                    ui.pre(m["content"]) if m["role"] == "assistant" else m["content"],
                    style=style,
                )
            )

        return ui.div(*bubbles)

    # ------------------
    # Query result table
    # ------------------
    @output
    @render.table
    def query_result():
        df = result_df.get()
        if df.empty:
            return None
        return df


# ------------------
# App
# ------------------
app = App(app_ui, server)
