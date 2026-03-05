import os
import requests
import gradio as gr

API_BASE = "http://localhost:8000"


# ── Upload ──────────────────────────────────────────────────────────────────

def upload_pdf(file):
    if file is None:
        return "No file selected.", ""

    filename = os.path.basename(file)
    with open(file, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/upload/",
            files={"file": (filename, f, "application/pdf")},
        )

    if resp.status_code == 202:
        data = resp.json()
        sid = data["session_id"]
        return f"Uploaded successfully.\nSession ID: {sid}\nStatus: processing...", sid
    return f"Upload failed: {resp.text}", ""


def poll_status(session_id):
    if not session_id:
        return "No session ID to check."
    resp = requests.get(f"{API_BASE}/sessions/{session_id}")
    if resp.status_code == 404:
        return "Session not found."
    if resp.status_code != 200:
        return f"Error {resp.status_code}"
    data = resp.json()
    status = data["status"]
    if status == "ready":
        return f"Ready — {data['filename']}"
    if status == "failed":
        return f"Failed: {data.get('error', 'unknown error')}"
    return "Still processing... check again in a few seconds."


# ── Sessions ─────────────────────────────────────────────────────────────────

def refresh_sessions():
    resp = requests.get(f"{API_BASE}/sessions/")
    if resp.status_code != 200:
        return gr.update(choices=[], value=None)
    sessions = resp.json().get("sessions", [])
    ready = [s for s in sessions if s["status"] == "ready"]
    choices = [
        (f"{s['filename']}  [{s['session_id'][:8]}]", s["session_id"])
        for s in ready
    ]
    return gr.update(choices=choices, value=choices[0][1] if choices else None)


# ── Chat / stream ─────────────────────────────────────────────────────────────

def respond(session_id, question, search_type, model_type, history):
    if history is None:
        history = []

    if not session_id:
        history = history + [{"role": "assistant", "content": "Please select a session first."}]
        yield history, history, ""
        return
    if not question.strip():
        yield history, history, ""
        return

    history = history + [{"role": "user", "content": question}]
    yield history, history, ""

    payload = {
        "session_id": session_id,
        "question": question,
        "search_type": search_type,
        "model_type": model_type,
        "top_k": 5,
    }

    answer = ""
    try:
        with requests.post(f"{API_BASE}/query/stream", json=payload, stream=True) as r:
            if r.status_code != 200:
                history = history + [{"role": "assistant", "content": f"Error {r.status_code}: {r.text}"}]
                yield history, history, ""
                return
            history = history + [{"role": "assistant", "content": ""}]
            for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                answer += chunk
                history[-1] = {"role": "assistant", "content": answer}
                yield history, history, ""
    except Exception as e:
        history = history + [{"role": "assistant", "content": f"Request failed: {e}"}]
        yield history, history, ""


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="RAG Assistant") as demo:
    gr.Markdown("# RAG Assistant")

    with gr.Tabs():

        # ── Tab 1: Upload ──
        with gr.Tab("Upload"):
            file_input = gr.File(label="Select PDF", file_types=[".pdf"])
            upload_btn = gr.Button("Upload", variant="primary")
            upload_status = gr.Textbox(label="Status", interactive=False, lines=3)
            session_id_box = gr.Textbox(label="Session ID", interactive=False)
            check_btn = gr.Button("Check Ingestion Status")

            upload_btn.click(
                upload_pdf,
                inputs=[file_input],
                outputs=[upload_status, session_id_box],
            )
            check_btn.click(
                poll_status,
                inputs=[session_id_box],
                outputs=[upload_status],
            )

        # ── Tab 2: Chat ──
        with gr.Tab("Chat"):
            with gr.Row():
                session_dd = gr.Dropdown(
                    label="Select PDF Session",
                    choices=[],
                    interactive=True,
                    scale=4,
                )
                refresh_btn = gr.Button("Refresh Sessions", scale=1)

            with gr.Row():
                search_type = gr.Radio(
                    ["hybrid", "semantic", "keyword"],
                    value="hybrid",
                    label="Retrieval Type",
                )
                model_type = gr.Radio(
                    ["openai", "ollama"],
                    value="openai",
                    label="Model",
                )

            chatbot = gr.Chatbot(height=450, label="Chat")
            chat_state = gr.State([])

            with gr.Row():
                question_box = gr.Textbox(
                    placeholder="Ask something about the document...",
                    show_label=False,
                    scale=5,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            clear_btn = gr.Button("Clear Chat")

            refresh_btn.click(refresh_sessions, outputs=[session_dd])

            send_btn.click(
                respond,
                inputs=[session_dd, question_box, search_type, model_type, chat_state],
                outputs=[chatbot, chat_state, question_box],
            )
            question_box.submit(
                respond,
                inputs=[session_dd, question_box, search_type, model_type, chat_state],
                outputs=[chatbot, chat_state, question_box],
            )
            clear_btn.click(lambda: ([], []), outputs=[chatbot, chat_state])

    demo.load(refresh_sessions, outputs=[session_dd])


if __name__ == "__main__":
    demo.launch()
