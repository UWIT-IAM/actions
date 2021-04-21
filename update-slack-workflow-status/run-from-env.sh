# Mimics the behavior of the github action by
# running the container locally using the same environment
# variables

while (($#))
do
  case $1 in
    --build)
      docker build -t action .
      ;;
  esac
  shift
done

docker run \
  -e ACTION_COMMAND \
  -e ACTION_CHANNEL \
  -e ACTION_DESCRIPTION \
  -e SLACK_BOT_TOKEN \
  -e ACTION_STEP_ID \
  -e ACTION_WF_STATUS \
  -e ACTION_STEP_STATUS \
  -e ACTION_CONTEXT \
  action
