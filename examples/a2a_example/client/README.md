# A2A Client Code Overview
This code implements a push notification system with authentication and listening capabilities, designed to securely send and receive push notifications between agents or services.

## 1. [`main.py`](main.py) — Command Line Client Interface
This module:
- Provides an interactive CLI to communicate with an A2A agent by sending text prompts and optional file attachments.
- Supports features like **message streaming**, session **history retrieval**, and enabling **push notifications**.
- Fetches the agent’s **metadata** (`AgentCard`) to understand its capabilities and available skills.
- If push notifications are enabled, starts a push notification **listener** and configures authentication.
- **Sends messages** to the agent and processes synchronous or streamed responses.
- Supports quitting the client cleanly with commands like `:q` or `quit`.

## 2. [`push_notification_auth.py`](push_notification_auth.py) — Push Notification Authentication
This module implements:

- A base class for computing SHA256 hashes of request payloads to ensure integrity.
- `PushNotificationSenderAuth`:
  - Generates RSA JWK key pairs for signing JWT tokens.
  - Signs push notification payloads embedding a hashed payload and timestamp (`iat`) to prevent replay attacks.
  - Sends push notifications with JWT tokens in Authorization headers.
  - Verifies push notification URLs using a unique validation token.
  - Provides a JWKS endpoint serving public keys to receivers.
- `PushNotificationReceiverAuth`:
  - Loads JWKS from URLs to retrieve public keys.
  - Verifies incoming push notifications by validating JWT signatures, payload hashes, and token freshness.

## 3. [`push_notification_listener.py`](push_notification_listener.py) — Push Notification Listener Server

This module defines:
- A `PushNotificationListener` class that runs a Starlette ASGI app in a separate thread with its own asyncio loop.
- Two HTTP endpoints:
    - `GET /notify` for validation checks that echo back a `validationToken` query parameter.
    - `POST /notify` to receive push notifications, verify their authenticity, and log incoming data.
  - Starts a Uvicorn server on the specified host and port.
  - Uses asynchronous verification to ensure push notifications are authentic and recent.
  - Runs concurrently with the client interface without blocking user interaction.

---

Together, these modules provide a secure and efficient push notification mechanism:

- The **Client CLI** enables users to send messages and receive asynchronous updates.

- The **Authentication module** ensures the integrity and authenticity of push notifications via JWT and key verification.

- The **Listener server** handles incoming push notifications, performs validation, and allows for push notification URL verification.

This architecture ensures secure, authenticated communication between agents or services using push notifications.
