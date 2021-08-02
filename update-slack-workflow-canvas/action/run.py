import json
import logging
import os
from typing import List, Optional
from uuid import uuid4

import click

from client import DatastoreClient, WorkflowCanvasClient
from models import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepStatus

MAX_CONTEXT_ELEMENTS = 9


def print_action_output(output_name: str, output_value: str):
    print(f"::set-output name={output_name}::{output_value}")


def sanitize_text(text: Optional[str]) -> Optional[str]:
    """
    Makes sure we don't have wacky whitespace in our output, depending on how
    the text is set.
    :param text: The text to sanitize.
    :return: The sanitized text.

    Example:
        # shell
        DESCRIPTION="
        blahblah
        foobar
            baz
                    bop
        "
        # When the description is read in, it will become:
        "blahblah foobar baz bop"
    """
    if not text:
        return text
    text = text.replace("\n", " ")
    return text.strip()


@click.command(help="Creates a new workflow canvas")
@click.option(
    "--description",
    required=False,
    help="The description of your workflow. Only plain text is allowed.",
)
@click.option("--canvas-id", default=str(uuid4()))
@click.option(
    "--json",
    "workflow_json",
    default=None,
    required=False,
    help="A JSON object containing (at least) the description field, "
    "but that may include also the workflowId, steps, and status fields.",
)
@click.option("--channel", required=False, default=None, help="The channel to send messages to.")
def create_canvas(
    description: str, channel: str, canvas_id: str, workflow_json: Optional[str]
):
    if workflow_json:
        workflow = Workflow.parse_raw(workflow_json)
        logging.info(workflow.dict())
    else:
        args = {
            'description': sanitize_text(description),
            'channel_name': channel,
        }
        # canvas_id has a default generator, so should only
        # be included if it is not blank.
        if canvas_id:
            args['workflow_id'] = 'canvas_id'
        workflow = Workflow(**args)
    canvas_client = WorkflowCanvasClient()
    datastore_client = DatastoreClient()
    canvas_client.create_workflow_canvas(workflow)
    datastore_client.store_workflow(workflow)
    print_action_output("canvas-id", workflow.workflow_id)


@click.command(help="Adds a step to an existing workflow.")
@click.option(
    "--description",
    required=True,
    help="The description of your step. This can include mrkdwn formatting.",
)
@click.option(
    "--step-status",
    default=WorkflowStepStatus.not_started,
    help="The status of the workflow step.",
)
@click.option(
    "--canvas-id", required=True, help="The canvas id you are adding a step to"
)
@click.option(
    "--workflow-status", help="(Optional) A new status for the workflow itself."
)
@click.option(
    "--step-id",
    help="An optional identifier for the step, otherwise this will be autogenerated.",
)
def create_step(
    description: str,
    step_status: WorkflowStepStatus,
    canvas_id: str,
    workflow_status: Optional[WorkflowStatus] = None,
    step_id: Optional[str] = None,
):
    datastore_client = DatastoreClient()

    with datastore_client.lock_workflow(canvas_id, save_on_exit=True) as workflow:
        step = WorkflowStep(
            description=sanitize_text(description),
            status=step_status,
        )
        if step_id:
            step.step_id = step_id

        if workflow_status:
            workflow.status = WorkflowStatus.from_value(workflow_status)
        workflow.steps.append(step)

    WorkflowCanvasClient().update_workflow_canvas(workflow)
    print_action_output("step-id", step.step_id)
    print_action_output("lock-id", datastore_client.lock_id)


@click.command(
    help="Remove an existing step, if it exists. Otherwise, a warning will be logged."
)
@click.option("--canvas-id", required=True, help="Required. The workflow canvas json.")
@click.option(
    "--step-id",
    "step_ids",
    required=True,
    multiple=True,
    help="Required. The step id to remove. You may supply"
    "this multiple times to remove many steps, or "
    'supply the value "*" to remove all of them. ',
)
@click.option(
    "--step-status",
    "-s",
    "status_filter",
    required=False,
    default=None,
    multiple=True,
    type=click.Choice(WorkflowStatus.values()),
    help="Optional, can be supplied multiple times. "
    "Only removes a step if it matches the status provided.",
)
def remove_step(canvas_id: str, step_ids: str, status_filter: List[WorkflowStepStatus]):
    datastore_client = DatastoreClient()

    with datastore_client.lock_workflow(canvas_id, save_on_exit=True) as workflow:
        if step_ids[0] == "*":
            logging.debug(f"Removing all steps matching filter: {status_filter}")
            step_ids = [step.step_id for step in workflow.steps]

        num_removed = 0
        for index, step in enumerate(list(workflow.steps)):
            if step.step_id not in step_ids:
                logging.debug(f"Step {step.step_id} not selected; not removing.")
                continue

            if status_filter and step.status_str not in status_filter:
                logging.debug(
                    f"Step {step.step_id} has status {step.status} "
                    f"which does not match filter: {status_filter}; "
                    "not removing."
                )
                continue
            logging.debug(f"Removing step {step.step_id} from canvas")
            workflow.steps.pop(index - num_removed)
            num_removed += 1

    WorkflowCanvasClient().update_workflow_canvas(workflow)
    print_action_output("lock-id", datastore_client.lock_id)


@click.command(
    help="Update an already initialized step, or the workflow status itself."
)
@click.option("--canvas-id", required=True, help="Required. The workflow canvas json.")
@click.option(
    "--step-status",
    "statuses",
    default=None,
    multiple=True,
    type=click.Choice(WorkflowStatus.values()),
    help="The new status for the step. You may supply this multiple times to "
    "update multiple steps at once.",
)
@click.option(
    "--workflow-status",
    default=None,
    type=click.Choice(WorkflowStatus.values()),
    required=False,
    help="The new status for the workflow.",
)
@click.option(
    "--step-id",
    "step_ids",
    multiple=True,
    help="Required for each step-status is provided. " "The id of the step to update. ",
)
def update_workflow(
    statuses: List[WorkflowStepStatus],
    workflow_status: Optional[WorkflowStatus],
    canvas_id: str,
    step_ids: List[str],
):
    datastore_client = DatastoreClient()
    if len(step_ids) != len(statuses):
        raise ValueError(
            f"Mismatch in number of steps "
            f"({len(step_ids)}) and statuses ({len(statuses)})."
        )

    with datastore_client.lock_workflow(canvas_id, save_on_exit=True) as workflow:
        if workflow_status:
            workflow.status = workflow_status

        wf_step_ids = [s.step_id for s in workflow.steps]
        for step_id_index, step_id in enumerate(step_ids):
            try:
                step_index = wf_step_ids.index(step_id)
            except IndexError:
                raise ValueError(f"No step named {step_id}")

            step_status = statuses[step_id_index]
            workflow.steps[step_index].status = step_status

    WorkflowCanvasClient().update_workflow_canvas(workflow)
    print_action_output("lock-id", datastore_client.lock_id)


@click.command(help="Add a context artifact to the workflow canvas")
@click.option("--description", help="The mrkdwn for your context artifact.")
@click.option("--canvas-id", help="Your b64-encoded canvas.")
def add_artifact(description: str, canvas_id: str):
    datastore_client = DatastoreClient()
    with datastore_client.lock_workflow(canvas_id, save_on_exit=True) as workflow:
        if len(workflow.artifacts) >= MAX_CONTEXT_ELEMENTS:
            raise IndexError(
                f"A maximum of {MAX_CONTEXT_ELEMENTS} artifacts per canvas can be attached."
            )
        workflow.artifacts.append(f"> {sanitize_text(description)}")
    WorkflowCanvasClient().update_workflow_canvas(workflow)
    print_action_output("lock-id", datastore_client.lock_id)


@click.command(
    help="Mark a workflow is complete and delete its context from Datastore."
    "Please always call this at the end of your workflow!"
)
@click.option("--canvas-id", help="Required.", required=True)
@click.option(
    "--workflow-status", help="Optional: the final workflow status to set", default=None
)
def finalize_workflow(canvas_id: str, workflow_status: str):
    if workflow_status:
        workflow_status = WorkflowStatus.from_value(workflow_status)
    datastore_client = DatastoreClient()
    try:
        with datastore_client.lock_workflow(canvas_id) as workflow:
            workflow = datastore_client.load_workflow(canvas_id)
            workflow.artifacts[0] = "COMPLETE"
            if workflow_status:
                workflow.status = workflow_status
            datastore_client.delete_workflow(workflow.workflow_id)
        WorkflowCanvasClient().update_workflow_canvas(workflow)
    finally:
        datastore_client.delete_lock(workflow.workflow_id)


@click.command(help="Simply dump workflow json and exit.")
@click.option("--canvas-id", help="Required.", required=True)
def get_canvas_json(canvas_id: str):
    datastore_client = DatastoreClient()
    workflow = datastore_client.load_workflow(canvas_id)
    payload = json.dumps(WorkflowCanvasClient().get_slack_payload(workflow), indent=4)
    print(payload)
    print_action_output("canvas-json", payload)


@click.group(help="Creates and maintains a slack workflow canvas.")
def cli():
    pass


cli.add_command(create_canvas)
cli.add_command(create_step)
cli.add_command(remove_step)
cli.add_command(update_workflow)
cli.add_command(add_artifact)
cli.add_command(finalize_workflow)
cli.add_command(get_canvas_json)


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    cli()
    print_action_output("fingerprint", os.environ.get("FINGERPRINT"))
