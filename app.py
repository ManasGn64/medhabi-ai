import os
import json
from groq import Groq
from dotenv import load_dotenv
from ddgs import DDGS
import streamlit as st
from datetime import datetime

load_dotenv()

st.set_page_config(page_title="Medhabi", page_icon="🌱", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;1,600&family=Inter:wght@300;400;500&display=swap');

* { box-sizing: border-box; }
.stApp { background: #fafaf8; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 1rem 8rem 1rem !important; max-width: 700px !important; }

[data-testid="stSidebar"] { background: #f5f5f3; border-right: 1px solid #e8e8e5; }

.site-header {
    padding: 48px 0 12px 0;
    border-bottom: 1px solid #e8e8e5;
    margin-bottom: 32px;
}
.site-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.2em;
    color: #1a1a1a;
    letter-spacing: -0.5px;
}
.site-title em { font-style: italic; color: #8b6914; }
.site-desc {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #999;
    margin-top: 4px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}

.user-row { display: flex; justify-content: flex-end; margin: 16px 0 4px 0; }
.user-bubble {
    background: #1a1a1a;
    color: #fff;
    padding: 13px 18px;
    border-radius: 18px 18px 4px 18px;
    max-width: 72%;
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    line-height: 1.65;
    font-weight: 400;
}
.bot-row { display: flex; justify-content: flex-start; margin: 16px 0 4px 0; }
.bot-bubble {
    background: #ffffff;
    color: #1a1a1a;
    padding: 13px 18px;
    border-radius: 18px 18px 18px 4px;
    max-width: 72%;
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    line-height: 1.65;
    font-weight: 400;
    border: 1px solid #e8e8e5;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.msg-meta {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    color: #bbb;
    margin: 2px 4px 12px 4px;
}
.msg-meta-right { text-align: right; }

.tool-pill {
    display: inline-block;
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    color: #8b6914;
    border: 1px solid #e0d0a0;
    background: #fdf8ec;
    padding: 2px 10px;
    border-radius: 10px;
    margin-bottom: 6px;
}

.stTextInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid #e0e0dc !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 15px !important;
    color: #1a1a1a !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}
.stTextInput > div > div > input:focus {
    border-color: #8b6914 !important;
    box-shadow: 0 0 0 3px rgba(139,105,20,0.08) !important;
}
.stButton > button {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 20px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    width: 100% !important;
    letter-spacing: 0.3px !important;
}
.stButton > button:hover { background: #333 !important; }
.divider { border: none; border-top: 1px solid #e8e8e5; margin: 20px 0; }
</style>
""", unsafe_allow_html=True)

# ---- TOOLS ----
def search_web(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No results found."
        output = ""
        for r in results:
            output += f"Title: {r['title']}\nSummary: {r['body']}\nURL: {r['href']}\n\n"
        return output
    except Exception as e:
        return f"Search failed: {str(e)}"

def calculate(expression: str) -> str:
    try:
        clean = expression.replace("%", "/100*")
        return str(eval(clean))
    except Exception as e:
        return f"Error: {e}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the internet for real-time information",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a math expression",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"]
            }
        }
    }
]

def run_tool(name, args):
    if name == "search_web":
        return search_web(args["query"])
    elif name == "calculate":
        return calculate(args["expression"])
    return "Unknown tool"

# ---- HISTORY ----
HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ---- SYSTEM PROMPT ----
MEDHABI_SYSTEM = """You are Medhabi, a calm and professional life coach.

Strict rules:
- No emojis ever
- No bullet points or lists ever
- Short responses only — 2 to 4 sentences maximum
- Write in plain flowing prose like a real conversation
- When someone shares a problem, first acknowledge it warmly, then ask one gentle question
- Be honest and grounded — what has happened cannot be changed, only how we respond
- Guide people toward growth and clarity with warmth and directness
- Sound like a wise, calm human — not a chatbot"""

# ---- SESSION STATE ----
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": MEDHABI_SYSTEM}]
if "chat_display" not in st.session_state:
    st.session_state.chat_display = load_history()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---- CHAT FUNCTION ----
def chat(user_message):
    st.session_state.messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=st.session_state.messages,
        tools=tools,
        tool_choice="auto"
    )
    message = response.choices[0].message
    tools_used = []

    if message.tool_calls:
        st.session_state.messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message.tool_calls]
        })
        for tc in message.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            tools_used.append(name)
            result = run_tool(name, args)
            st.session_state.messages.append({"role": "tool", "tool_call_id": tc.id, "name": name, "content": result})
        final_response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=st.session_state.messages)
        final = final_response.choices[0].message.content
    else:
        final = message.content

    st.session_state.messages.append({"role": "assistant", "content": final})
    return final, tools_used

# ---- SIDEBAR ----
with st.sidebar:
    st.markdown("### Medhabi")
    st.markdown("*A space to think clearly.*")
    st.markdown("---")
    st.markdown("Life challenges  \nGoal clarity  \nMindset  \nHard truths  \nResearch")
    st.markdown("---")
    if st.button("Clear conversation"):
        st.session_state.chat_display = []
        st.session_state.messages = [{"role": "system", "content": MEDHABI_SYSTEM}]
        save_history([])
        st.rerun()
    st.markdown(f"{len(st.session_state.chat_display)} messages")

# ---- HEADER ----
st.markdown("""
<div class="site-header">
    <div class="site-title">Med<em>habi.</em></div>
    <div class="site-desc">Your personal life coach — calm, honest, grounded</div>
</div>
""", unsafe_allow_html=True)

# ---- CHAT ----
for item in st.session_state.chat_display:
    if item["role"] == "user":
        st.markdown(f'<div class="user-row"><div class="user-bubble">{item["content"]}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="msg-meta msg-meta-right">{item.get("time","")}</div>', unsafe_allow_html=True)
    else:
        tool_html = ""
        if item.get("tools"):
            for t in item["tools"]:
                label = "Web Search" if t == "search_web" else "Calculator"
                tool_html += f'<div class="tool-pill">{label}</div><br>'
        st.markdown(f'<div class="bot-row"><div><div>{tool_html}</div><div class="bot-bubble">{item["content"]}</div></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="msg-meta">{item.get("time","")}</div>', unsafe_allow_html=True)

# ---- INPUT ----
st.markdown("<hr class='divider'>", unsafe_allow_html=True)
col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_input("Message", placeholder="What is on your mind?", label_visibility="collapsed", key="input", on_change=None)
with col2:
    send = st.button("Send")

# Triggers on BOTH button click AND Enter key
triggered = send or (user_input and user_input != st.session_state.get("last_input", ""))

if triggered and user_input.strip():
    st.session_state["last_input"] = user_input
    now = datetime.now().strftime("%I:%M %p")
    st.session_state.chat_display.append({"role": "user", "content": user_input, "time": now})
    with st.spinner(""):
        reply, tools_used = chat(user_input)
    st.session_state.chat_display.append({"role": "assistant", "content": reply, "tools": tools_used, "time": now})
    save_history(st.session_state.chat_display)
    st.rerun()