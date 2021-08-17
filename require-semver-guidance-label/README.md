# uwit-iam/actions/require-semver-guidance-label

This action requires that a pull request have a 
label in the format off `semver-guidance:foo`, where `foo`
is either an explicit version (e.g., `1.2.3`) or a 
guidance directive such as `prerelease`, `patch`, `minor`, `major`. 

If you include this action in your pull request workflow, your validations will fail until 
an authorized user (or some automated task) sets version guidance for a pull request as part of the change review process.

The intended use is that you can require a pull request to have one of these 
labels before it can be approved, so that your CICD workflow can automatically
set the version for the change when it is merged into your default branch.

The label can either be set by some automated process, or by
a reviewer with requisite access to apply the label.

**Inputs:**
- [github-token](#github-token)*

**Outputs:**
- [pr-number](#pr-number)
- [guidance](#guidance)

## Example Use


**Basic use:**
```yaml
- uses: uwit-iam/actions/require-semver-guidance-label@1.0.0
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

**Full example:**

This example shows how you might use a tool like poetry 
to update the version of a pull request branch.

```yaml
# ./github/workflows/bump-version.yml
on:
  pull_request:
    types: [opened, labeled, unlabeled, synchronize]

jobs:
  bump-version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: uwit-iam/actions/require-semver-guidance-label@1.0.0
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
        id: semver
      # Everything below shows how you might use this output. 
      - uses: abatilo/actions-poetry@v2.1.0
      - run: |
          poetry version ${{ steps.semver.outputs.guidance }}
          version=$(poetry version -s)
          echo ::set-output name=new-version::$version
        id: poetry
      - run: |
          docker build -t $image
          docker push $image
        env:
          image: ghcr.io/my-project/my-repo:${{ steps.poetry.outputs.new-version }}
      - uses: EndBug/add-and-commit@v7.2.1
        with:
          add: pyproject.toml
          default_author: github_actions
          signoff: true
          message: "[auto-commit] Update app version to ${{ steps.poetry.outputs.new-version }}"
```

## Inputs

### `github-token`*

**REQUIRED**. The github token for the current workflow run.

## Outputs

### `pr-number`

The PR number whose labels were validated.

### `guidance`

The guidance string derived from the label.
