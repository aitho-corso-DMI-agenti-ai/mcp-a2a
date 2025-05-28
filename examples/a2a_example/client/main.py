"""Command line interface for the A2A client example."""

import asyncio
import base64
import os
import urllib

from uuid import uuid4

import httpx
import asyncclick as click

from push_notification_auth import PushNotificationReceiverAuth

from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    Part,
    TextPart,
    FilePart,
    FileWithBytes,
    Task,
    TaskState,
    Message,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    MessageSendConfiguration,
    SendMessageRequest,
    SendStreamingMessageRequest,
    MessageSendParams,
    GetTaskRequest,
    TaskQueryParams,
    JSONRPCErrorResponse,
)

@click.command()
@click.option('--agent', default='http://localhost:10000')
@click.option('--session', default=0)
@click.option('--history', default=False)
@click.option('--use_push_notifications', default=False)
@click.option('--push_notification_receiver', default='http://localhost:5000')
async def cli(
    agent,
    session,
    history,
    use_push_notifications: bool,
    push_notification_receiver: str,
):
    """
    Command line interface for the A2A client example.

    Args:
        agent (str): The URL of the A2A agent.
        session (int): The session ID for the agent.
        history (bool): Whether to retrieve task history.
        use_push_notifications (bool): Whether to use push notifications.
        push_notification_receiver (str): The URL of the push notification receiver.
    """
    async with httpx.AsyncClient(timeout=30) as httpx_client:
        # Resolve the agent card to get its capabilities and skills
        card_resolver = A2ACardResolver(httpx_client, agent)
        card = await card_resolver.get_agent_card()

        print('======= Agent Card ========')
        print(card.model_dump_json(exclude_none=True))

        # Check if the agent supports streaming and push notifications
        notif_receiver_parsed = urllib.parse.urlparse(
            push_notification_receiver
        )
        notification_receiver_host = notif_receiver_parsed.hostname
        notification_receiver_port = notif_receiver_parsed.port

        if use_push_notifications:
            from push_notification_listener import (
                PushNotificationListener,
            )

            # Authenticate the push notification receiver
            notification_receiver_auth = PushNotificationReceiverAuth()
            await notification_receiver_auth.load_jwks(
                f'{agent}/.well-known/jwks.json'
            )

            # Create the push notification listener with the receiver's host and port
            push_notification_listener = PushNotificationListener(
                host=notification_receiver_host,
                port=notification_receiver_port,
                notification_receiver_auth=notification_receiver_auth,
            )

            # Start the push notification listener server
            push_notification_listener.start()

        # Create the A2A client with the agent card
        client = A2AClient(httpx_client, agent_card=card)

        continue_loop = True
        streaming = card.capabilities.streaming

        # Loop to complete tasks until the user decides to exit
        while continue_loop:
            print('=========  starting a new task ======== ')
            continue_loop, contextId, taskId = await completeTask(
                client,
                streaming,
                use_push_notifications,
                notification_receiver_host,
                notification_receiver_port,
                None,
                None,
            )

            if history and continue_loop:
                print('========= history ======== ')
                task_response = await client.get_task(
                    {'id': taskId, 'historyLength': 10}
                )
                print(
                    task_response.model_dump_json(
                        include={'result': {'history': True}}
                    )
                )


async def completeTask(
    client: A2AClient,
    streaming,
    use_push_notifications: bool,
    notification_receiver_host: str,
    notification_receiver_port: int,
    taskId,
    contextId,
):
    """
    Completes a task by sending a message to the agent.

    Args:
        client (A2AClient): The A2A client instance.
        streaming (bool): Whether to use streaming for the response.
        use_push_notifications (bool): Whether to use push notifications.
        notification_receiver_host (str): Host for the push notification receiver.
        notification_receiver_port (int): Port for the push notification receiver.
        taskId (str): The ID of the task, if any.
        contextId (str): The context ID, if any.

    Returns:
        tuple: A tuple containing a boolean indicating if the task was completed,
               the context ID, and the task ID.
    """
    # Ask the user for input to send to the agent
    prompt = click.prompt(
        '\nWhat do you want to send to the agent? (:q or quit to exit)'
    )

    # If the prompt is ':q' or 'quit', exit the loop
    if prompt == ':q' or prompt == 'quit':
        return False, None, None

    # Create the message to be sent to the agent with the provided prompt
    message = Message(
        role='user',
        parts=[TextPart(text=prompt)],
        messageId=str(uuid4()),
        taskId=taskId,
        contextId=contextId,
    )

    # Ask the user if they want to attach a file
    file_path = click.prompt(
        'Select a file path to attach? (press enter to skip)',
        default='',
        show_default=False,
    )

    # If a file path is provided, read the file and encode it in base64
    # and attach it to the message
    if file_path and file_path.strip() != '':
        with open(file_path, 'rb') as f:
            file_content = base64.b64encode(f.read()).decode('utf-8')
            file_name = os.path.basename(file_path)

        message.parts.append(
            Part(
                root=FilePart(
                    file=FileWithBytes(
                        name=file_name, bytes=file_content
                    )
                )
            )
        )

    # Create the payload for sending the message
    payload = MessageSendParams(
        id=str(uuid4()),
        message=message,
        configuration=MessageSendConfiguration(
            acceptedOutputModes=['text'],
        ),
    )

    # If the agent uses push notifications, add the push notification configuration
    if use_push_notifications:
        payload.metadata = {
            'url': f'http://{notification_receiver_host}:{notification_receiver_port}/notify',
            'authentication': {
                'schemes': ['bearer'],
            },
        }

    taskResult = None
    message = None

    # If streaming is enabled, send the message using streaming
    if streaming:
        response_stream = client.send_message_streaming(
            SendStreamingMessageRequest(
                id=str(uuid4()),
                params=payload,
            )
        )
        async for result in response_stream:
            if isinstance(result.root, JSONRPCErrorResponse):
                print("Error: ", result.root.error)
                return False, contextId, taskId
            event = result.root.result
            contextId = event.contextId
            if (isinstance(event, Task)):
                taskId = event.id
            elif (
                isinstance(event, TaskStatusUpdateEvent)
                or isinstance(event, TaskArtifactUpdateEvent)
            ):
                taskId = event.taskId
            elif isinstance(event, Message):
                message = event
            print(
                f'stream event => {event.model_dump_json(exclude_none=True)}'
            )
        # Upon completion of the stream. Retrieve the full task if one was made.
        if taskId:
            taskResult = await client.get_task(
                GetTaskRequest(
                    id=str(uuid4()),
                    params=TaskQueryParams(id=taskId),
                )
            )
            taskResult = taskResult.root.result
    else:
        try:
            # For non-streaming, assume the response is a task or message.
            event = await client.send_message(
                SendMessageRequest(
                    id=str(uuid4()),
                    params=payload,
                )
            )
            event = event.root.result
        except Exception as e:
            print("Failed to complete the call", e)
        if not contextId:
            contextId = event.contextId
        if isinstance(event, Task):
            if not taskId:
                taskId = event.id
            taskResult = event
        elif isinstance(event, Message):
            message = event

    # If the message is present, print its content
    if message:
        print(f'\n{message.model_dump_json(exclude_none=True)}')
        return True, contextId, taskId
    if taskResult:
        # Don't print the contents of a file.
        task_content = taskResult.model_dump_json(
            exclude={
                "history": {
                    "__all__": {
                        "parts": {
                            "__all__" : {"file"},
                        },
                    },
                },
            },
            exclude_none=True,
        )
        print(f'\n{task_content}')
        ## if the result is that more input is required, loop again.
        state = TaskState(taskResult.status.state)
        if state.name == TaskState.input_required.name:
            return (
                await completeTask(
                    client,
                    streaming,
                    use_push_notifications,
                    notification_receiver_host,
                    notification_receiver_port,
                    taskId,
                    contextId,
                ),
                contextId,
                taskId,
            )
        ## task is complete
        return True, contextId, taskId
    ## Failure case, shouldn't reach
    return True, contextId, taskId


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    asyncio.run(cli())
