# Mimics the behavior of the github action by
# running the container locally using the same environment
# variables
set -ex


while (($#))
do
  case $1 in
    --build)
      docker build -t action .
      ;;
  esac
  shift
done
MOUNT_PATH=$(dirname $GOOGLE_APPLICATION_CREDENTIALS)
CREDENTIALS_FILE=$(basename $GOOGLE_APPLICATION_CREDENTIALS)

if [[ -n "${SLACK_CANVAS_ID}" ]]
then
  export ACTION_CANVAS=$SLACK_CANVAS_ID
fi
docker run \
  --mount type=bind,source=$MOUNT_PATH,target=/secrets \
  -e ACTION_DEBUG \
  -e ACTION_COMMAND \
  -e ACTION_CHANNEL \
  -e ACTION_DESCRIPTION \
  -e SLACK_BOT_TOKEN \
  -e ACTION_STEP_ID \
  -e ACTION_WF_STATUS \
  -e ACTION_STEP_STATUS \
  -e ACTION_CANVAS \
  -e CI \
  -e GOOGLE_APPLICATION_CREDENTIALS="/secrets/$CREDENTIALS_FILE" \
  action .
