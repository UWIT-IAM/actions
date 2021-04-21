from __future__ import annotations

from slack_sdk import WebClient

from models import ActionSettings, PostMessageInput, Workflow, WorkflowStep, WorkflowStepStatus


class SlackClientProxy:
    def __init__(self):
        self._settings = ActionSettings()
        self._client = WebClient(self._settings.slack_bot_token.get_secret_value())
        self._input_template = PostMessageInput.construct(
            channel_name='#tom-integration-sandbox',
        )

    @property
    def client(self) -> WebClient:
        return self._client

    @staticmethod
    def create_workflow() -> Workflow:
        workflow = Workflow(
            description='Lorem ipsum release workflow',
            channel_name='#tom-integration-sandbox'
        )
        workflow.steps.append(
            WorkflowStep(description='Setting up all the things', status=WorkflowStepStatus.not_started)
        )
        return workflow

    def create_workflow_canvas(self, workflow: Workflow):
        post_message_input = self._input_template.copy(
            update=dict(
                text=workflow.description,
                blocks=[b.dict(by_alias=True, exclude_none=True) for b in workflow.get_message_blocks()]
            )
        )
        message_input = post_message_input.dict(by_alias=True, exclude_none=True)
        message_input['channel'] = workflow.channel
        response = self.client.chat_postMessage(**message_input)
        message_id = response.data['message']['ts']
        channel_id = response.data['channel']
        workflow.message_id = message_id
        workflow.channel_id = channel_id

    def update_workflow_canvas(self, workflow: Workflow):
        update_message_input = self._input_template.copy(
            update=dict(
                text=workflow.description,
                ts=workflow.message_id,
                channel_id=workflow.channel_id,
                blocks=[
                    b.dict(by_alias=True, exclude_none=True) for b in workflow.get_message_blocks()
                ]
            )
        )
        update_message_input = update_message_input.dict(by_alias=True, exclude_none=True)
        update_message_input['channel'] = workflow.channel
        self.client.chat_update(**update_message_input)
