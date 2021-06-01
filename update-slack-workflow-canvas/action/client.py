from __future__ import annotations

import logging
import random
import time
from contextlib import contextmanager
from uuid import uuid4

from google.cloud import datastore
from slack_sdk import WebClient

from models import ActionSettings, PostMessageInput, Workflow


class DatastoreClient:
    def __init__(self):
        self.client = datastore.Client(namespace='github-actions')
        self.lock_id = str(uuid4())
        self.workflow_kind = 'SlackWorkflowCanvas'
        self.lock_kind = 'SlackWorkflowLock'

    @contextmanager
    def lock_workflow(self, workflow_id: str, save_on_exit: bool = False) -> Workflow:
        lock_acquired = False
        key = self.client.key(self.lock_kind, workflow_id)
        lock_entity = None
        while not lock_acquired:
            lock_entity = self.client.get(key) or datastore.Entity(key=key)
            lock_id = lock_entity.get("lock_id")
            if lock_id and lock_id != self.lock_id:
                logging.warning(f"Entity {workflow_id} is locked by instance {lock_id}")
                jitter = random.randrange(1000, 2000)
                timeout = jitter / 1000.0
                time.sleep(timeout)
            else:
                lock_entity["lock_id"] = self.lock_id
                self.client.put(lock_entity)
                lock_acquired = True
        workflow = self.load_workflow(workflow_id)
        try:
            yield workflow
            if save_on_exit:
                self.store_workflow(workflow)
        finally:
            lock_entity["lock_id"] = None
            self.client.put(lock_entity)

    def load_workflow(self, workflow_id: str) -> Workflow:
        key = self.get_workflow_key(workflow_id)
        entity = self.client.get(key)
        return Workflow.parse_obj(entity)

    def get_workflow_key(self, workflow_id) -> datastore.Key:
        return self.client.key(self.workflow_kind, workflow_id)

    def store_workflow(self, workflow: Workflow):
        data = workflow.canvas_payload
        key = self.get_workflow_key(workflow.workflow_id)
        entity = datastore.Entity(key=key)
        entity.update(**data)
        self.client.put(entity)

    def delete_workflow(self, workflow_id):
        self.client.delete(self.get_workflow_key(workflow_id))

    def delete_lock(self, workflow_id):
        self.client.delete(self.client.key(self.lock_kind, workflow_id))


class WorkflowCanvasClient:
    def __init__(self):
        self._settings = ActionSettings()
        self._slack_client = WebClient(self._settings.slack_bot_token.get_secret_value())
        self._input_template = PostMessageInput.construct(
            channel_name='#tom-integration-sandbox',
        )

    @property
    def slack_client(self) -> WebClient:
        return self._slack_client

    def create_workflow_canvas(self, workflow: Workflow):
        workflow.artifacts.append('INCOMPLETE')
        post_message_input = self._input_template.copy(
            update=dict(
                text=workflow.description,
                blocks=[b.dict(by_alias=True, exclude_none=True) for b in workflow.get_message_blocks()]
            )
        )
        message_input = post_message_input.dict(by_alias=True, exclude_none=True)
        message_input['channel'] = workflow.channel
        response = self.slack_client.chat_postMessage(**message_input)
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
        self.slack_client.chat_update(**update_message_input)
