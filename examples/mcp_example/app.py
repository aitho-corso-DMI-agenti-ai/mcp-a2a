"""Streamlit app for MCP RAG agent."""

import os
import streamlit as st
import torch

from rag_core import MCPAgent

# Fix per torch
torch.classes.__path__ = [os.path.join(torch.__path__[0], torch.classes.__file__)]

# Percorso al server MCP
SERVER_PATH = os.path.join(os.path.dirname(__file__), "mcp_server.py")

# Configurazione della pagina
st.set_page_config(page_title="MCP RAG", page_icon="💬")
st.title("💬 Chat con MCP RAG")
st.subheader("Powered by LangGraph and Model Context Protocol")
st.markdown(
    "Questa chat è alimentata da un agente MCP (Model Context Protocol) " \
    "che può eseguire vari strumenti e rispondere a domande."
)
st.markdown("---")

@st.cache_resource(show_spinner=False)
def get_agent():
    """Crea e restituisce un agente MCP."""
    mcp_agent = MCPAgent(server_path=SERVER_PATH)
    mcp_agent.start()
    return mcp_agent

# Inizializza l'agente MCP
agent = get_agent()
tools = agent.get_tools().tools
resources = agent.get_resources().resources
prompts = agent.get_prompts().prompts

# Stato iniziale
st.session_state.setdefault("messages", [{
    "role": "assistant",
    "content": "Ciao! Fammi una domanda e io cercherò di aiutarti."
}])
st.session_state.setdefault("pill_to_send", None)
st.session_state.setdefault("selected_prompt", None)

# Callback per la pill selezionata
def on_prompt_selected():
    label = st.session_state.selected_prompt
    if label:
        st.session_state.pill_to_send = label_to_name[label]  # Usa il nome corretto
    st.session_state.selected_prompt = None

# Sidebar
with st.sidebar:
    with st.expander("## 🛠️ MCP Tools", expanded=True):
        for tool in tools:
            st.markdown(f"- `{tool.name}`: {tool.description}")
    st.markdown("---")

    with st.expander("## 📚 MCP Resources", expanded=True):
        for resource in resources:
            print(resource)
            st.markdown(f"- `{resource.name}` - `{str(resource.uri)}`: {resource.description}:")
    st.markdown("---")

    with st.expander("## 💬 MCP Prompts", expanded=True):
        label_to_name = {
            f"`{prompt.name}` — {prompt.description}": prompt.name
            for prompt in prompts
        }

        st.pills(
            "💡 Scegli un prompt:",
            options=list(label_to_name.keys()),
            key="selected_prompt",
            on_change=on_prompt_selected
        )

# Funzione per inviare un messaggio
def send_message(user_message: str):
    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })

    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Sto ragionando..."):
            response, used_tool, thought = agent.invoke(user_message)

        if thought:
            with st.expander("🧠 Ragionamento interno (LLM)", expanded=False):
                st.markdown(thought)

        st.markdown(response)

        if used_tool:
            st.caption(f"🛠️ MCP tool usato: `{used_tool}`")

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    if used_tool:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"🛠️ MCP Tool usato: {used_tool}"
        })

# Mostra messaggi della chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input manuale
user_input = st.chat_input("Scrivi qui la tua domanda...")
if user_input:
    send_message(user_input)

# Se è stata selezionata una pill, carica il prompt e invialo
if st.session_state.pill_to_send:
    prompt_text = agent.load_prompt_by_name(st.session_state.pill_to_send)
    send_message(prompt_text)
    st.session_state.pill_to_send = None
