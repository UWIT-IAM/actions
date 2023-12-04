# pip install pygithub
from github import (
    Auth,
    Github,
    UnknownObjectException,
)

# Personal access token suitable for updating repo labels
GH_PAT = "ghp_"
# repo to update
GH_REPO = "UWIT-IAM/test-update-pr-branch-version-python"

# recreate existing labels? useful to synchronize description and/or color
recreate = True

# These values taken from https://github.com/UWIT-IAM/identity-uw/labels
REQUIRED_LABELS = [
    # (name, color, description)
    ('semver-guidance:major', 'DE1C95', "The 'x' in x.y.z"),
    ('semver-guidance:minor', 'A3B4DB', "The 'y' in x.y.z"),
    ('semver-guidance:patch', 'E4B02D', "The 'z' in x.y.z"),
    ('semver-guidance:no-bump', '5319e7', "Use this to indicate a change that should not bump the version"),
]


# Authenticate. You do not have to use a PAT
# https://pygithub.readthedocs.io/en/stable/examples/Authentication.html
auth = Auth.Token(GH_PAT)

# Create main Github object
g = Github(auth=auth)

repo = g.get_repo(GH_REPO)
print(f"Updating semver-guidance labels on {repo.name}")

for name, color, desc in REQUIRED_LABELS:
    try:
        label = repo.get_label(name=name)
    except UnknownObjectException:  # 404, basically
        defined = False
    else:
        defined = True

    if not defined:
        repo.create_label(name=name, color=color, description=desc)
        print(f"Created label {name}")
    elif recreate:
        # NOTE: name required positional arg
        label.edit(name=name, color=color, description=desc)
        print(f"Updated label {name}")
