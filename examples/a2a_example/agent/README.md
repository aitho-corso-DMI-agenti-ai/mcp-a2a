# Agent Code Overview
This code implements a Currency Conversion Agent using the Agent2Agent (A2A) protocol. This protocol enables AI agents to communicate and collaborate seamlessly, regardless of their underlying frameworks or platforms.

## 1. [`main.py`](main.py) — Server Initialization
This module:
- Loads environment variables using `dotenv`.
- Defines the agent's capabilities and skills, such as streaming and push notifications.
- Creates the agent's metadata (`AgentCard`), detailing its functionalities and how to interact with it.
- Initializes the request handler (`DefaultRequestHandler`) and the agent executor (`CurrencyAgentExecutor`).
- Starts the A2A server using `uvicorn` and the ASGI framework `Starlette`.

## 2. [`agent.py`](agent.py) — Agent Logic
This module defines:
- The `get_exchange_rate` function, which fetches exchange rates from the **Frankfurter API**.
- The `CurrencyAgent` class, which:
    - Utilizes a language model (`ChatOpenAI`).
    - Integrates the get_exchange_rate function as a tool.
    - Defines a system instruction to guide the agent's behavior.
    - Implements methods for synchronous (`invoke`) and asynchronous (`stream`) interactions.

## 3. [`agent_executor.py`](agent_executor.py) — Request Execution
This module implements:
- The `CurrencyAgentExecutor` class, which:
    - Validates incoming requests.
    - Executes tasks using the agent.
    - Manages task states and updates using `TaskUpdater`.
    - Handles streaming responses and updates the task status accordingly.

---

In the A2A protocol, the **`AgentExecutor`** is crucial for:
- Processing Requests: It interprets incoming messages and determines the appropriate actions.
- **Executing Agent Logic**: It utilizes the agent's tools and models to process information.
- **Managing Task States**: It monitors and updates the task's progress throughout its lifecycle.
- **Communicating with Clients**: It sends responses, updates, and notifications back to the client via the `EventQueue`.

Essentially, the `AgentExecutor` acts as the bridge between the A2A server infrastructure and the agent's internal logic, ensuring that requests are handled appropriately and that the client is kept informed of the task's status.
