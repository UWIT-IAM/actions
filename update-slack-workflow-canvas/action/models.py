from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, BaseSettings, Extra, Field, SecretStr, validator
from pytz import timezone


def to_mixed_case(string: str):
    """
    foo_bar_baz becomes fooBarBaz. Based on
    pydantic's `to_camel` utility, except without
    the initial capital letter.
    """
    words = string.split("_")
    return "".join([words[0]] + [w.capitalize() for w in words[1:]])


class ActionBaseModel(BaseModel):
    class Config:
        alias_generator = to_mixed_case
        allow_population_by_field_name = True
        use_enum_values = True


class WorkflowStepStatus(Enum):
    not_started = "not started"
    in_progress = "in progress"
    skipped = "skipped"
    succeeded = "succeeded"
    failed = "failed"


class WorkflowStatus(Enum):
    initializing = "initializing"
    in_progress = "in progress"
    succeeded = "succeeded"
    failed = "failed"


STEP_STATUS_ICONS = {
    WorkflowStepStatus.succeeded: ":white_check_mark:",
    WorkflowStepStatus.failed: ":octagonal_sign:",
    WorkflowStepStatus.not_started: ":double_vertical_bar:",
    WorkflowStepStatus.in_progress: ":arrow_forward:",
    WorkflowStepStatus.skipped: ":fast_forward:",
}

WORKFLOW_STATUS_ICONS = {
    WorkflowStatus.initializing: ":white_circle:",
    WorkflowStatus.in_progress: ":large_yellow_circle:",
    WorkflowStatus.succeeded: ":large_green_circle:",
    WorkflowStatus.failed: ":red_circle:",
}


class WorkflowStep(BaseModel):
    description: str
    status: WorkflowStepStatus
    step_id: str = Field(default_factory=lambda: str(uuid4()))

    def get_message_blocks(self) -> List[Block]:
        icon = STEP_STATUS_ICONS.get(self.status)
        return [
            SectionBlock(
                fields=[
                    Block(text=self.description),
                    Block(text=f"{icon} {self.status.value.title()}"),
                ]
            )
        ]

    @property
    def canvas_payload(self):
        result = self.dict()
        result.update({"status": self.status.value})
        return result


class SlackFormat:
    @staticmethod
    def link(href, text) -> str:
        return f"<{href} | {text}>"


class SlackBlockType(Enum):
    section = "section"
    mrkdwn = "mrkdwn"
    divider = "divider"
    header = "header"
    image = "image"
    text = "plain_text"
    context = "context"


class APIModel(BaseModel):
    class Config:
        extra = Extra.allow
        use_enum_values = True
        allow_population_by_field_name = True


class Block(APIModel):
    block_type: Union[str, SlackBlockType] = Field(
        default=SlackBlockType.mrkdwn, alias="type"
    )
    text: Optional[Union[str, Block]]


Block.update_forward_refs()


class ImageBlock(Block):
    block_type: Union[str, SlackBlockType] = Field("image", const=True, alias="type")
    # Require alt text to encourage accessibility
    text: str = Field(..., alias="alt_text")
    image_url: str


class ContextBlock(Block):
    block_type: Union[str, SlackBlockType] = Field("context", const=True, alias="type")
    elements: List[Block]

    @validator("elements", each_item=True)
    def validate_elements(cls, item: Block) -> Block:
        if SlackBlockType(item.block_type) not in (
            SlackBlockType.mrkdwn,
            SlackBlockType.text,
            SlackBlockType.image,
        ):
            raise ValueError("context blocks can only contain image and text elements")
        return item


class SectionBlock(Block):
    block_type: Union[str, SlackBlockType] = Field("section", const=True, alias="type")
    fields: List[Block] = []


class PostMessageInput(APIModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.now(tz=timezone("US/Pacific")).isoformat(),
        alias="ts",
    )
    channel: str
    username: str
    icon_emoji: str
    blocks: List[Block]
    text: str


class ActionSettings(BaseSettings):
    slack_bot_token: SecretStr = Field(..., env="SLACK_BOT_TOKEN")
    context_storage: str = Field("/tmp/action_context", env="CONTEXT_STORAGE_PATH")


class CreateMessageInput(BaseModel):
    workflow_description: Optional[str]


class Workflow(ActionBaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    message_id: Optional[str]  # Used to update the workflow canvas
    channel_id: Optional[str]  # Used to update the workflow canvas
    channel_name: Optional[str] = Field(None, alias="channel")
    execution_href: Optional[str]  # Link to actions run
    description: Optional[str]  # e.g., "Prod release workflow"
    event_name: Optional[str]  # e.g., 'push', 'pull_request'
    event_href: Optional[str]  # Link to PR or branch
    status: WorkflowStatus = WorkflowStatus.initializing
    steps: List[WorkflowStep] = []
    artifacts: List[str] = []

    @property
    def channel(self) -> str:
        return self.channel_id or self.channel_name

    @property
    def artifact_blocks(self) -> List[Block]:
        return [
            ContextBlock(
                block_type=SlackBlockType.context, elements=[Block(text=artifact)]
            )
            for artifact in self.artifacts
        ]

    @property
    def header_block(self) -> Block:
        icon = WORKFLOW_STATUS_ICONS.get(self.status)
        return Block(
            block_type=SlackBlockType.header,
            text=Block(
                block_type=SlackBlockType.text,
                text=f"{icon} [{self.status.value.title()}] {self.description}",
            ),
        )

    @property
    def canvas_payload(self):
        _dict = self.dict(exclude={"steps"})
        _dict.update(
            {
                "status": self.status.value,
                "steps": [step.canvas_payload for step in self.steps],
            }
        )
        return _dict

    def get_message_blocks(self) -> List[Block]:
        blocks = [self.header_block]

        for step in self.steps:
            blocks.extend(step.get_message_blocks())

        blocks.extend(self.artifact_blocks)

        blocks.append(Block(block_type=SlackBlockType.divider))

        return blocks


class WorkflowJSONInput(Workflow):
    """
    A subclass of the Workflow that simply marks
    some fields as required.
    """

    description: str
    channel_name: str
