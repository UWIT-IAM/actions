FROM ghcr.io/uwit-iam/poetry AS action-base
WORKDIR /action
ENV PATH="${POETRY_HOME}/bin:${PATH}"
COPY poetry.lock pyproject.toml ./
RUN poetry install

FROM action-base AS action
ARG FINGERPRINT
ENV FINGERPRINT="$FINGERPRINT"
COPY action/ ./
ENTRYPOINT /action/entrypoint.sh
