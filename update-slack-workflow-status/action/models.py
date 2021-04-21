from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, BaseSettings, Extra, Field, SecretStr
from pytz import timezone
import json


class WorkflowStepStatus(Enum):
    not_started = 'not started'
    in_progress = 'in progress'
    skipped = 'skipped'
    succeeded = 'succeeded'
    failed = 'failed'


class WorkflowStatus(Enum):
    initializing = 'initializing'
    in_progress = 'in progress'
    succeeded = 'succeeded'
    failed = 'failed'


STEP_STATUS_ICONS = {
    WorkflowStepStatus.succeeded: ':white_check_mark:',
    WorkflowStepStatus.failed: ':octagonal_sign:',
    WorkflowStepStatus.not_started: ':double_vertical_bar:',
    WorkflowStepStatus.in_progress: ':arrow_forward:',
    WorkflowStepStatus.skipped: ':fast_forward:'
}

WORKFLOW_STATUS_ICONS = {
    WorkflowStatus.initializing: ':white_circle:',
    WorkflowStatus.in_progress: ':large_yellow_circle:',
    WorkflowStatus.succeeded: ':large_green_circle:',
    WorkflowStatus.failed: ':red_circle:'
}


class WorkflowStep(BaseModel):
    description: str
    status: WorkflowStepStatus
    step_id: str = Field(default_factory=lambda: str(uuid4()))

    def get_message_blocks(self) -> List[SlackBlock]:
        return [
            SlackSectionBlock(
                fields=[
                    SlackBlock(text=(
                        f"Status: *{self.status.value.title()}*\n"
                        f"{self.description}\n"
                        f"———"
                    )),
                    SlackBlock(text=STEP_STATUS_ICONS.get(self.status))
                ]
            )
        ]

    @property
    def context_payload(self):
        result = self.dict()
        result.update({
            'status': self.status.value
        })
        return result


class SlackFormat:
    @staticmethod
    def link(href, text) -> str:
        return f'<{href} | {text}>'


class SlackBlockType(Enum):
    section = 'section'
    mrkdwn = 'mrkdwn'
    divider = 'divider'
    header = 'header'
    image = 'image'
    text = 'plain_text'


class APIModel(BaseModel):
    class Config:
        extra = Extra.allow
        use_enum_values = True
        allow_population_by_field_name = True


class SlackBlock(APIModel):
    block_type: Union[str, SlackBlockType] = Field(default=SlackBlockType.mrkdwn, alias='type')
    text: Optional[Union[str, SlackBlock]]


SlackBlock.update_forward_refs()


class SlackImageBlock(SlackBlock):
    block_type: Union[str, SlackBlockType] = Field('image', const=True, alias='type')
    # Require alt text to encourage accessibility
    text: str = Field(..., alias='alt_text')
    image_url: str


class SlackSectionBlock(SlackBlock):
    block_type: Union[str, SlackBlockType] = Field('section', const=True, alias='type')
    fields: List[SlackBlock] = []


class PostMessageInput(APIModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(tz=timezone('US/Pacific')).isoformat(),
                           alias='ts')
    channel: str
    username: str
    icon_emoji: str
    blocks: List[SlackBlock]
    text: str


class ActionSettings(BaseSettings):
    slack_bot_token: SecretStr = Field(..., env='SLACK_BOT_TOKEN')
    context_storage: str = Field('/tmp/action_context', env='CONTEXT_STORAGE_PATH')


class CreateMessageInput(BaseModel):
    workflow_description: Optional[str]


class Workflow(BaseModel):
    message_id: Optional[str]  # Used to update the workflow canvas
    channel_id: Optional[str]  # Used to update the workflow canvas
    channel_name: Optional[str]
    execution_href: Optional[str]  # Link to actions run
    description: Optional[str]  # e.g., "Prod release workflow"
    event_name: Optional[str]  # e.g., 'push', 'pull_request'
    event_href: Optional[str]  # Link to PR or branch
    status: WorkflowStatus = WorkflowStatus.initializing
    steps: List[WorkflowStep] = []

    @property
    def channel(self) -> str:
        return self.channel_id or self.channel_name

    @property
    def header_block(self) -> SlackBlock:
        icon = WORKFLOW_STATUS_ICONS.get(self.status)
        return SlackBlock(
            block_type=SlackBlockType.header,
            text=SlackBlock(
                block_type=SlackBlockType.text,
                text=f'{icon} [{self.status.value.title()}] {self.description}',
            )
        )

    @property
    def context_payload(self):
        _dict = self.dict(exclude={'steps'})
        _dict.update({
            'status': self.status.value,
            'steps': [
                step.context_payload for step in self.steps
            ]
        })
        return json.dumps(_dict)

    def get_message_blocks(self) -> List[SlackBlock]:
        blocks = [
            self.header_block
        ]

        for step in self.steps:
            blocks.extend(step.get_message_blocks())

        blocks.append(
            SlackBlock(block_type=SlackBlockType.divider)
        )
        return blocks
