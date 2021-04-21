#!/usr/bin/env bash

# ENV args set by action.yml
ACTION_ARGS=""
ACTION_COMMAND="${ACTION_COMMAND}"
ACTION_CHANNEL="${ACTION_CHANNEL}"
ACTION_DESCRIPTION="${ACTION_DESCRIPTION}"
ACTION_WF_STATUS="${ACTION_WF_STATUS:-initializing}"
ACTION_STEP_STATUS="${ACTION_STEP_STATUS:-not started}"
ACTION_STEP_ID="${ACTION_STEP_ID}"
ACTION_CONTEXT="${ACTION_CONTEXT}"
CONTEXT="$ACTION_CONTEXT"

CMD="python -m run $ACTION_COMMAND"

function update_workflow_status_arg() {
    if [[ -n "$ACTION_WF_STATUS" ]]
    then
      ACTION_ARGS+=" --workflow-status '${ACTION_WF_STATUS}'"
    fi
}

function update_step_id_arg() {
    if [[ -n "$ACTION_STEP_ID" ]]
    then
      ACTION_ARGS+=" --step-id '${ACTION_STEP_ID}'"
    fi
}

case "$ACTION_COMMAND" in
  initialize-workflow)
    ACTION_ARGS+=" --description '${ACTION_DESCRIPTION}'"
    ACTION_ARGS+=" --channel '${ACTION_CHANNEL}'"
    ;;
  initialize-step)
    update_workflow_status_arg
    update_step_id_arg
    ACTION_ARGS+=" --description '${ACTION_DESCRIPTION}'"
    ACTION_ARGS+=" --step-status '${ACTION_STEP_STATUS}'"
    ACTION_ARGS+=" --context-token '${ACTION_CONTEXT}'"
    ;;
  update-workflow)
    update_workflow_status_arg
    update_step_id_arg
    test -n "${ACTION_STEP_STATUS}" && \
      ACTION_ARGS+=" --step-status '${ACTION_STEP_STATUS}'"
    ;;
esac

CONTEXT=$(eval "$CMD $ACTION_ARGS" | tail -n 1)
if [[ "${CONTEXT}" == "${ACTION_CONTEXT}" ]]
then
  echo "WARNING: Workflow context did not change."
fi

if [[ -n "${CI}" ]]
then
  echo "::set-output name=context::$CONTEXT"
  echo "WORKFLOW_SLACK_CONTEXT=$CONTEXT" >> $GITHUB_ENV
else
  echo $CONTEXT
fi

if [[ -n "${DEBUG}" ]]
then
  echo $CONTEXT | base64 -d
fi
