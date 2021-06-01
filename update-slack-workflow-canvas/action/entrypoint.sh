#!/usr/bin/env bash
# This translates environment variables into CLI
# arguments that are provided to `run.py`, allowing
# this app to be used as a CLI or as an image base
# for some other image.
#
# However, you don't have to use this at all, you can simply
# run the docker image with `run.py` instead of the default entrypoint.

test -n "$ACTION_DEBUG" && set -x

# ENV args set by action.yml
ACTION_ARGS=""

# ENV args set by action.yml, or whatever
# is invoking the docker image.
ACTION_COMMAND="${ACTION_COMMAND}"
ACTION_CHANNEL="${ACTION_CHANNEL}"
ACTION_DESCRIPTION="${ACTION_DESCRIPTION}"
ACTION_WF_STATUS="${ACTION_WF_STATUS}"
ACTION_STEP_STATUS="${ACTION_STEP_STATUS}"
ACTION_STEP_ID="${ACTION_STEP_ID}"
ACTION_CANVAS="${ACTION_CANVAS}"
ACTION_JSON="${ACTION_JSON}"

CMD="python /action/run.py $ACTION_COMMAND"

function add-arg-if-exists() {
  if [[ -n "$2" ]]
  then
    ACTION_ARGS+=" --$1 '$(get_value_from_arg $2)'"
  fi
}

# Actions doesn't inherently allow an environment
# variable as a default, which puts more strain on the
# person writing the actions to have to paste the
# same thing over and over. This will allow us to set
# values as "use_env(foo)" which will extract the env
# value at _runtime_, as opposed to during the action's
# "compile" time. This does so in a way that is safe to use
# and does not execute arbitrary code using eval.
# Example:
#   CANVAS_ID=12345 ACTION_CANVAS="use_env(CANVAS_ID)" ./entrypoint.sh
function get_value_from_arg() {
  provided_value="$@"
   if [[ $provided_value =~ ^use_env\((.*)\)$ ]]
   then
       echo "${!BASH_REMATCH[1]}"
   else
       echo "$provided_value"
   fi
}

case "$ACTION_COMMAND" in
  create-canvas)
    add-arg-if-exists canvas-id "${ACTION_CANVAS}"
    add-arg-if-exists description "${ACTION_DESCRIPTION}"
    add-arg-if-exists channel "${ACTION_CHANNEL}"
    add-arg-if-exists json "${ACTION_JSON}"
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
