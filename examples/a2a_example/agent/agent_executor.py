"""
Executor for the Currency Conversion Agent.
The executor handles the execution of the agent's tasks,
validates requests, and manages task updates.
"""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

from agent import CurrencyAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CurrencyAgentExecutor(AgentExecutor):
    """
    Currency Conversion AgentExecutor Example.
    This class implements the AgentExecutor interface to handle the execution
    of the Currency Conversion Agent's tasks. It validates requests, retrieves user input,
    and processes it with the agent. It also manages task updates and streaming responses.
    """

    def __init__(self):
        self.agent = CurrencyAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute the agent with the provided context and event queue.
        Validates the request, retrieves user input, and processes it with the agent.
        If the task is not already created, it creates a new task and updates the status
        accordingly. Handles streaming responses and updates the task status based on
        the agent's output.

        Args:
            context (RequestContext): The request context containing user input and task details.
            event_queue (EventQueue): The event queue for task updates and notifications.

        Raises:
            ServerError: If there is an error in processing the request or streaming the response.
        """
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        # Retrieve user input from the context
        query = context.get_user_input()
        task = context.current_task

        # If the task is not already created, create a new task
        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)

        # Create a TaskUpdater to manage task updates
        updater = TaskUpdater(event_queue, task.id, task.contextId)

        try:
            async for item in self.agent.stream(query, task.contextId):
                # If the item is not a dictionary, log and continue
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']

                if not is_task_complete and not require_user_input:
                    # Update the task status to working
                    updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item['content'],
                            task.contextId,
                            task.id,
                        ),
                    )
                elif require_user_input:
                    updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item['content'],
                            task.contextId,
                            task.id,
                        ),
                        final=True,
                    )
                    break
                else:
                    updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='conversion_result',
                    )
                    updater.complete()
                    break

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
