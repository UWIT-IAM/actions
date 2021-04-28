#!/usr/bin/env bash
set -e

# ENV args set by action.yml
ACTION_ARGS=""
ACTION_COMMAND="${ACTION_COMMAND}"
ACTION_CHANNEL="${ACTION_CHANNEL}"
ACTION_DESCRIPTION="${ACTION_DESCRIPTION}"
ACTION_WF_STATUS="${ACTION_WF_STATUS}"
ACTION_STEP_STATUS="${ACTION_STEP_STATUS}"
ACTION_STEP_ID="${ACTION_STEP_ID}"
ACTION_CANVAS="${ACTION_CANVAS}"

CMD="python -m run $ACTION_COMMAND"

function add-arg-if-exists() {
  if [[ -n "$2" ]]
  then
    ACTION_ARGS+=" --$1 '$2'"
  fi
}

case "$ACTION_COMMAND" in
  create-canvas)
    add-arg-if-exists canvas-id "${ACTION_CANVAS}"
    add-arg-if-exists description "${ACTION_DESCRIPTION}"
    add-arg-if-exists channel "${ACTION_CHANNEL}"
    ;;
  create-step)
    add-arg-if-exists workflow-status "${ACTION_WF_STATUS}"
    add-arg-if-exists step-status "${ACTION_STEP_STATUS}"
    add-arg-if-exists step-id "${ACTION_STEP_ID}"
    add-arg-if-exists canvas-id "${ACTION_CANVAS}"
    add-arg-if-exists description "${ACTION_DESCRIPTION}"
    ;;
  update-workflow)
    add-arg-if-exists workflow-status "${ACTION_WF_STATUS}"
    add-arg-if-exists step-status "${ACTION_STEP_STATUS}"
    add-arg-if-exists step-id "${ACTION_STEP_ID}"
    add-arg-if-exists canvas-id "${ACTION_CANVAS}"
    ;;
  add-artifact)
    add-arg-if-exists canvas-id "${ACTION_CANVAS}"
    add-arg-if-exists description "${ACTION_DESCRIPTION}"
    ;;
  finalize-workflow)
    add-arg-if-exists canvas-id "${ACTION_CANVAS}"
    add-arg-if-exists workflow-status "${ACTION_WF_STATUS}"
    ;;
  get-canvas-json)
    add-arg-if-exists canvas-id "${ACTION_CANVAS}"
    ;;
esac

echo "$CMD $ACTION_ARGS"
eval "$CMD $ACTION_ARGS"
