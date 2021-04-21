FROM gcr.io/uwit-mci-iam/poetry AS action-base
WORKDIR /action
ENV PATH="${POETRY_HOME}/bin:${PATH}"
COPY poetry.lock pyproject.toml ./
RUN poetry install

FROM action-base AS action
ARG SLACK_BOT_TOKEN
ENV SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN
COPY action/ ./
ENTRYPOINT /action/entrypoint.sh
