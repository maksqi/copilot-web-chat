import json
import os
import random

import requests
from datetime import datetime
from uuid import uuid4
from flask import Flask, render_template, request, jsonify, make_response
import sqlite3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


# SQLite helper functions
def get_db_connection():
    conn = sqlite3.connect('chat.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                model TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
            )
        """)
    conn.close()


init_db()

COPILOT_CHAT_COMPLETION_URL = "https://api.githubcopilot.com/chat/completions"
COPILOT_CHAT_AUTH_URL = "https://api.github.com/copilot_internal/v2/token"

# Available models for Copilot
AVAILABLE_MODELS = [
    {"id": "claude-3.7-sonnet", "name": "Claude 3.7 Sonnet"},
    {"id": "claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
    {"id": "gpt-4o-2024-05-13", "name": "GPT-4o"},
    {"id": "gpt-4", "name": "GPT-4"},
    # {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
    {"id": "o1", "name": "o1"},
    {"id": "o3-mini", "name": "o3-mini"},
    {"id": "gemini-2.0-flash-001", "name": "Gemini 2.0 Flash 001"},
]


def get_copilot_token():
    # path to file /Users/{username}/.config/github-copilot/apps.json
    # token will start with ghu_

    return random.choice(os.getenv('COPILOT_TOKENS').split(','))


def get_api_token(oauth_token):
    headers = {
        "Authorization": f"token {oauth_token}",
        "Accept": "application/json",
        "Editor-Version": "Zed/unknown",
        "Copilot-Integration-Id": "vscode-chat"
    }
    try:
        response = requests.get(COPILOT_CHAT_AUTH_URL, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("token")
        else:
            print("Failed to get API token:", response.text)
            return None
    except Exception as e:
        print("Error getting API token:", e)
        return None


def generate_chat_title(user_message, assistant_reply):
    """
    Uses the Copilot Chat API to generate a short title for the conversation.
    """
    prompt = (
        f"Generate a short, descriptive title for the following conversation in a casual tone:\n"
        f"User: {user_message}\n"
        f"Assistant: {assistant_reply}\n"
        f"Title:"
    )
    payload = {
        "intent": False,
        "n": 1,
        "stream": False,
        "temperature": 0.7,
        "model": "gpt-4o-2024-05-13",  # or choose an appropriate model
        "messages": [{"role": "system", "content": prompt}]
    }
    headers = {
        "Authorization": f"Bearer {get_api_token(get_copilot_token())}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Editor-Version": "Zed/unknown",
        "Copilot-Integration-Id": "vscode-chat"
    }
    try:
        response = requests.post(COPILOT_CHAT_COMPLETION_URL, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                title = message.get("content", "").strip()
                return title
    except Exception as e:
        print("Error generating title:", e)
    return None


# Helper function to obtain current user id from cookies.
def get_current_user_id():
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid4())
    return user_id


# Updated function to send a chat message using the SQLite DB for chat history.
def send_chat_message(chat_id, user_message, user_id, retry=False):
    conn = get_db_connection()
    chat = conn.execute("SELECT * FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id)).fetchone()
    if not chat:
        conn.close()
        return {"error": "Chat not found"}

    # Retrieve existing messages sorted by timestamp.
    messages = conn.execute("SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp", (chat_id,)).fetchall()
    payload_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    # Append the current user's message.
    payload_messages.append({"role": "user", "content": user_message})

    payload = {
        "intent": True,
        "n": 1,
        "stream": False,
        "temperature": 0.7,
        "model": chat["model"],
        "messages": payload_messages
    }

    token = get_copilot_token()
    print(f"Current model used: {chat['model']}")
    print(f"Current token used: {token}")

    headers = {
        "Authorization": f"Bearer {get_api_token(token)}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Editor-Version": "Zed/unknown",
        "Copilot-Integration-Id": "vscode-chat"
    }

    try:
        response = requests.post(COPILOT_CHAT_COMPLETION_URL, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                assistant_reply = message.get("content", "")
                if not assistant_reply:
                    delta = choices[0].get("delta", {})
                    assistant_reply = delta.get("content", "")

                # Save the new messages in the database.
                now = datetime.utcnow().isoformat()
                conn.execute(
                    "INSERT INTO messages (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (chat_id, "user", user_message, now)
                )
                conn.execute(
                    "INSERT INTO messages (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (chat_id, "assistant", assistant_reply, datetime.utcnow().isoformat())
                )
                conn.commit()
                # If the chat name is still the default, generate a title based on user request and assistant reply.
                if chat["name"] == "New Chat":
                    title = generate_chat_title(user_message, assistant_reply)
                    if title:
                        conn.execute("UPDATE chats SET name = ? WHERE id = ?", (title, chat_id))
                        conn.commit()
                        conn.close()
                        return {"reply": assistant_reply, "title": title}
                conn.close()
                return {"reply": assistant_reply}
            else:
                conn.close()
                return {"error": "No choices in response"}
        elif response.status_code == 400 and not retry:
            # Check if the error contains "off_topic" code
            error_data = response.json().get("error", {})
            if error_data.get("code") == "off_topic":
                print("Received off_topic error. Retrying with 'not code'.")
                # Add "not code" to original message and retry request
                new_user_message = user_message + " not code"
                return send_chat_message(chat_id, new_user_message, user_id, retry=True)
            else:
                conn.close()
                return {"error": f"Error from Copilot API: {response.text}"}
        else:
            conn.close()
            return {"error": f"Error from Copilot API: {response.text}"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


# Route: Home page. Loads chats for the current user and creates a default chat if none exist.
@app.route("/")
def index():
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid4())

    # Get model from URL parameter
    model_from_url = request.args.get("model")
    conn = get_db_connection()

    # If there's a model in URL, update all user's chats
    if model_from_url:
        conn.execute("UPDATE chats SET model = ? WHERE user_id = ?",
                     (model_from_url, user_id))
        conn.commit()

    chats = conn.execute("SELECT * FROM chats WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    if not chats:
        # Create a default chat for the user.
        chat_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        default_model = model_from_url or "gpt-4o"
        conn.execute("INSERT INTO chats (id, user_id, name, model, created_at) VALUES (?, ?, ?, ?, ?)",
                     (chat_id, user_id, "New Chat", default_model, now))
        conn.commit()
        chats = conn.execute("SELECT * FROM chats WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    response = make_response(render_template("chat.html",
                                             models=AVAILABLE_MODELS,
                                             chats=chats,
                                             request=request
                                             ))
    response.set_cookie("user_id", user_id)
    return response


# Route: Create a new chat.
@app.route("/chat/new", methods=["POST"])
def new_chat():
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid4())
    chat_id = str(uuid4())

    # Get current model from user's existing chat
    conn = get_db_connection()
    existing_chat = conn.execute("SELECT model FROM chats WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                                 (user_id,)).fetchone()
    model_choice = existing_chat["model"] if existing_chat else request.form.get("model", "gpt-4o")

    now = datetime.utcnow().isoformat()
    conn.execute("INSERT INTO chats (id, user_id, name, model, created_at) VALUES (?, ?, ?, ?, ?)",
                 (chat_id, user_id, "New Chat", model_choice, now))
    conn.commit()
    chat = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    conn.close()
    return jsonify({
        "id": chat["id"],
        "name": chat["name"],
        "model": chat["model"],
        "created_at": chat["created_at"]
    })


# Route: Rename chat.
@app.route("/chat/<chat_id>/rename", methods=["POST"])
def rename_chat(chat_id):
    user_id = request.cookies.get("user_id")
    new_name = request.form.get("name", "Unnamed Chat")
    conn = get_db_connection()
    result = conn.execute("UPDATE chats SET name = ? WHERE id = ? AND user_id = ?",
                          (new_name, chat_id, user_id))
    conn.commit()
    if result.rowcount > 0:
        conn.close()
        return jsonify({"success": True})
    conn.close()
    return jsonify({"error": "Chat not found"}), 404


# Route: Delete chat.
@app.route("/chat/<chat_id>/delete", methods=["POST"])
def delete_chat(chat_id):
    user_id = request.cookies.get("user_id")
    conn = get_db_connection()
    conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    result = conn.execute("DELETE FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id))
    conn.commit()
    if result.rowcount > 0:
        conn.close()
        return jsonify({"success": True})
    conn.close()
    return jsonify({"error": "Chat not found"}), 404


# Route: Update chat model.
@app.route("/chat/<chat_id>/update_model", methods=["POST"])
def update_model(chat_id):
    user_id = request.cookies.get("user_id")
    model = request.form.get("model")
    if model:
        conn = get_db_connection()
        # Update model for all user's chats
        result = conn.execute("UPDATE chats SET model = ? WHERE user_id = ?",
                              (model, user_id))
        conn.commit()
        conn.close()
        if result.rowcount > 0:
            print(f"Updated model for chat {chat_id} to: {model}")
            return jsonify({"success": True})
    return jsonify({"error": "Chat not found"}), 404


# Route: Send a message.
@app.route("/send", methods=["POST"])
def send():
    user_message = request.form.get("message")
    chat_id = request.form.get("chat_id")
    user_id = request.cookies.get("user_id")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    if not chat_id:
        return jsonify({"error": "No chat specified"}), 400
    result = send_chat_message(chat_id, user_message, user_id)
    return jsonify(result)


# New route: Fetch messages for a given chat (used by the frontend).
@app.route('/chat/<chat_id>/messages', methods=["GET"])
def get_messages(chat_id):
    user_id = request.cookies.get("user_id")
    conn = get_db_connection()
    chat = conn.execute("SELECT * FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id)).fetchone()
    if chat:
        messages = conn.execute("SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp", (chat_id,)).fetchall()
        messages_list = [{"role": msg["role"], "content": msg["content"], "timestamp": msg["timestamp"]} for msg in
                         messages]
        conn.close()
        return jsonify(messages_list)
    conn.close()
    return jsonify({"error": "Chat not found"}), 404


# New route: Fetch statistics for all user messages across all chats.
@app.route("/stats/messages", methods=["GET"])
def get_messages_stats():
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) as total FROM messages WHERE role = 'user'").fetchone()["total"]
    conn.close()
    return jsonify({"total": total})


@app.template_filter('tojson')
def to_json(value):
    return json.dumps(value)


# New route to serve robots.txt for SEO purposes
@app.route("/robots.txt")
def robots_txt():
    robots = "User-agent: *\nDisallow:"
    return robots, 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    app.run(debug=True, port=6767)
