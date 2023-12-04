# Requirements

Your repository must have **labels** which support semantic versioning.

There are **four necessary for Python/`poetry`** - you can see them [in the identity-UW repo](https://github.com/UWIT-IAM/identity-uw/issues/labels). They are:

1. `semver-guidance:major` - bump the 'x' in `x.y.z`
2. `semver-guidance:minor` - bump the 'y' in `x.y.z`
3. `semver-guidance:patch` - bump the 'z' in `x.y.z`
4. `semver-guidance:no-bump` - change nothing

You can run `add_labels_to_repo.py` to update an existing repo to contain the labels.
