"""
Listener for push notifications using Starlette and asyncio.
This module defines a `PushNotificationListener` class that sets up a Starlette application
to listen for incoming push notifications and handle validation checks.
"""

import asyncio
import threading
import traceback

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

from push_notification_auth import PushNotificationReceiverAuth


class PushNotificationListener:
    """
    Push Notification Listener that listens for incoming push notifications
    and handles validation checks and notifications.
    This class runs a Starlette application with two endpoints:
    - `/notify` for receiving push notifications
    - `/notify` with a query parameter `validationToken` for validation checks
    """
    def __init__(
        self,
        host,
        port,
        notification_receiver_auth: PushNotificationReceiverAuth,
    ):
        self.host = host
        self.port = port
        self.notification_receiver_auth = notification_receiver_auth
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(
            target=lambda loop: loop.run_forever(), args=(self.loop,)
        )
        self.thread.daemon = True
        self.thread.start()

    def start(self):
        """
        Starts the push notification listener server in a separate thread.
        This method initializes the Starlette application and starts the server.
        It should be called to begin listening for notifications.
        """
        try:
            # Need to start server in separate thread as current thread
            # will be blocked when it is waiting on user prompt.
            asyncio.run_coroutine_threadsafe(
                self.start_server(),
                self.loop,
            )
            print('======= push notification listener started =======')
        except Exception as e:
            print(e)

    async def start_server(self):
        """Initializes and starts the Starlette server to listen for push notifications."""
        import uvicorn

        self.app = Starlette()
        self.app.add_route(
            '/notify', self.handle_notification, methods=['POST']
        )
        self.app.add_route(
            '/notify', self.handle_validation_check, methods=['GET']
        )

        config = uvicorn.Config(
            self.app, host=self.host, port=self.port, log_level='critical'
        )
        self.server = uvicorn.Server(config)
        await self.server.serve()

    async def handle_validation_check(self, request: Request):
        """
        Handles validation checks for push notifications.
        This endpoint is called with a query parameter `validationToken`
        to verify the push notification service.

        Args:
            request (Request): The incoming request containing the validation token.

        Returns:
            Response: A response containing the validation token if valid,
                      or a 400 status code if the token is missing.
        """
        validation_token = request.query_params.get('validationToken')
        print(
            f'\npush notification verification received => \n{validation_token}\n'
        )

        if not validation_token:
            return Response(status_code=400)

        return Response(content=validation_token, status_code=200)

    async def handle_notification(self, request: Request):
        """
        Handles incoming push notifications.
        This endpoint processes the notification data and verifies it using
        the provided authentication method.

        Args:
            request (Request): The incoming request containing the push notification data.

        Returns:
            Response: A response indicating the success or failure of the notification handling.
        """
        data = await request.json()
        try:
            if not await self.notification_receiver_auth.verify_push_notification(
                request
            ):
                print('push notification verification failed')
                return
        except Exception as e:
            print(f'error verifying push notification: {e}')
            print(traceback.format_exc())
            return

        print(f'\npush notification received => \n{data}\n')
        return Response(status_code=200)
