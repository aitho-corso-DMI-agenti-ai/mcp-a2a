# LLMs and LangChain introduction

This repository contains example notebooks for the 2025 course [Agenti Intelligenti e Machine Learning (AiTHO)](https://web.dmi.unict.it/it/corsi/l-31/agenti-intelligenti-e-machine-learning-aitho), focusing on MCP and A2A.

## Tech Stack

- **Python**
- **[LangChain](https://github.com/langchain-ai/langchain)** – A framework for building AI-based conversational chains
- **[LangGraph](https://github.com/langchain-ai/langgraph)** – A framework for building AI agent workflows
- **[Streamlit](https://streamlit.io/)** - A fast and intuitive framework for building interactive web apps directly in Python, commonly used for AI and data science applications
- **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction)** – A standardized interface for defining, sharing, and exchanging model context across different systems and agents
- **[Agent-to-Agent Protocol (A2A)](https://google.github.io/A2A/)** - A communication protocol enabling direct, structured interactions between autonomous AI agents, supporting task coordination and collaboration

## Project Structure

All the slides are located in the `slide/` directory.

The code is located in the `examples/` directory.

More infos about the examples is to be found in the [`MCP example README`](examples/mcp_example/README.md) and the [`A2A example README`](examples/a2a_example/README.md).

## AI Models
The examples use OpenAI models by default (by importing the `langchain_openai` module for LangChain). You're welcome to switch to any model provider of your choice.

## Setup Instructions

### 1. Install Poetry

Poetry is the dependency manager used in this project. Follow the [official installation guide](https://python-poetry.org/docs/#installation) to set it up on your system.

### 2. Install Project Dependencies

```bash
poetry install
```

### 3. Setup API keys

Copy the file `.env.example` as `.env` and put your own keys.

### 4. Launch the applications

#### 4.1 Streamlit MCP application

```bash
poetry run streamlit run examples/mcp_example/app.py --server.address 0.0.0.0
```

#### 4.2 A2A Application
- Start the agent with the following command:
    ```bash
    poetry run python examples/a2a_example/agent/main.py --host 0.0.0.0 --port 8080
    ```

- Then start the CLI client:
    ```bash
    poetry run python examples/a2a_example/client/main.py --agent http://localhost:8080
    ```
