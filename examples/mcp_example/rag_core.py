"""
MCP Agent for RAG with LangChain and LangGraph
This module implements an MCP (Model Context Protocol) agent that can interact with a server
and perform various tasks using LangChain and LangGraph.
"""

import asyncio
import re
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.tools.retriever import create_retriever_tool

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.prompts import load_mcp_prompt

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from utils import convert_blobs_to_documents

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

class MCPAgent:
    """
    Agente MCP con sessione e cliente stdin/stdout mantenuti aperti.
    Usa un event loop dedicato per gestire le chiamate sincrone.
    """
    def __init__(self, server_path: str = "mcp_server.py"):
        self.server_path = server_path
        self.loop = asyncio.new_event_loop()
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        # placeholder per sessione e agent
        self.session = None
        self.agent = None

    def start(self):
        """Avvia il client MCP e crea l'agente"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._initialize())

    async def create_in_memory_retriever(self):
        """Crea un retriever in memoria per le risorse MCP"""
        print("Ingesting MCP resources...")
        blobs = await load_mcp_resources(session=self.session)
        documents = convert_blobs_to_documents(blobs)
        print(documents)

        vector_store = InMemoryVectorStore.from_documents(
            documents=documents,
            embedding=self.embedding_model
        )
        print(f"Indexed {len(documents)} documents from MCP resources.")

        return vector_store.as_retriever(search_kwargs={"k": 1})

    async def _initialize(self):
        """Inizializza la sessione MCP e l'agente"""
        # Configura server MCP
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_path]
        )
        # Avvia stdio client e sessione
        self._stdio_cm = stdio_client(server_params)
        self._stdio = await self._stdio_cm.__aenter__()
        read, write = self._stdio
        self.session = await ClientSession(read, write).__aenter__()
        await self.session.initialize()

        # Carica strumenti MCP
        mcp_tools = await load_mcp_tools(self.session)

        # Carica risorse e build vector store
        retriever = await self.create_in_memory_retriever()

        retriever_tool = create_retriever_tool(
            retriever=retriever,
            name="mcp_resource_retriever",
            description="Recupera risorse pertinenti dal server MCP per la query."
        )
        # Crea agente React
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
        )
        memory = MemorySaver()
        self.agent = create_react_agent(
            model=llm,
            checkpointer=memory,
            tools=[retriever_tool] + mcp_tools,
            prompt=SystemMessage(
                """You are a helpful assistant. Use tools when needed.
                Reply in the user's language."""
            ),
        )

    def get_tools(self):
        """Restituisce strumenti MCP via chiamata sincrona"""
        return self.loop.run_until_complete(self.session.list_tools())

    def get_resources(self):
        """Restituisce risorse MCP via chiamata sincrona"""
        return self.loop.run_until_complete(self.session.list_resources())

    def get_prompts(self):
        """Restituisce prompt MCP via chiamata sincrona"""
        return self.loop.run_until_complete(self.session.list_prompts())

    def load_prompt_by_name(self, prompt_name: str) -> str:
        """Carica un prompt per nome in modo sincrono"""
        prompts = self.loop.run_until_complete(load_mcp_prompt(self.session, prompt_name))
        return prompts[0].content

    def invoke(self, user_message: str) -> tuple[str, str, str]:
        """Invoca l'agente MCP in modo sincrono

        Args:
            user_message (str): Il messaggio dell'utente da inviare all'agente.

        Returns:
            tuple[str, str, str]: Una tupla contenente la risposta dell'agente,
                                  il nome dello strumento usato (se presente),
                                  e il ragionamento interno dell'agente (se presente).
        """
        result = self.loop.run_until_complete(
            self.agent.ainvoke(
                { "messages": [HumanMessage(content=user_message)] },
                config={
                    "configurable": {
                        "session_id": "default",
                        "thread_id": "default",
                        "recursion_limit": 1,
                    }
                },
                debug=True,
            )
        )
        full = result["messages"][-1].content
        thought = "\n\n".join(re.findall(r"<think>(.*?)</think>", full, re.DOTALL)) or None
        clean = re.sub(r"<think>.*?</think>", "", full, flags=re.DOTALL).strip()
        prev = result["messages"][-2]
        used = prev.name if isinstance(prev, ToolMessage) else None
        return clean, used, thought

    def stop(self):
        """Chiude la sessione e lo stdio client"""
        async def _shutdown():
            await self.session.__aexit__(None, None, None)
            await self._stdio_cm.__aexit__(None, None, None)
        self.loop.run_until_complete(_shutdown())
        self.loop.close()
