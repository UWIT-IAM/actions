FROM ghcr.io/uwit-iam/poetry:latest
WORKDIR /
RUN pip install pygithub
COPY require_semver_guidance_label.py ./
ENTRYPOINT ["/require_semver_guidance_label.py"]
