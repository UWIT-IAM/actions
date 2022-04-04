# actions/configure-gcloud-docker

Sets up the `gcloud` CLI, activates a service account
from a credential token, and logs in to gcr.io via docker
using the credentials.

The `google-github-actions/auth` action will set appropriate environment 
variables (like `GOOGLE_APPLICATION_CREDENTIALS`) to be used by other steps
in your workflow.

## Usage

```yaml
jobs:
  my-job:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v3
      - uses: UWIT-IAM/actions/configure-gcloud-docker@v0.1
        with: 
          gcloud-token: ${{ secrets.IAM_GCR_TOKEN }}
```
