#!/usr/bin/env python

import re
from typing import Any

from github import Github
from argparse import ArgumentParser
import os


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        'Verify labels attached to a pull request.'
    )
    parser.add_argument('--github-ref', default=os.environ.get('GITHUB_REF'))
    parser.add_argument('--github-token', default=os.environ.get('GITHUB_TOKEN'))
    parser.add_argument('--github-repository', default=os.environ.get('GITHUB_REPOSITORY'))
    return parser


def get_pr_number(github_ref: str) -> int:
    try:
        return int(re.search('refs/pull/([0-9]+)/merge', github_ref).group(1))
    except Exception:
        raise ValueError(
            f'Could not determine pull request number from GITHUB_REF "{github_ref}"'
        )


def set_ci_output(key: str, val: Any):
    print(f'::set-output name={key}::{val}')


if __name__ == "__main__":
    args = get_parser().parse_args()
    repo = Github(args.github_token).get_repo(args.github_repository)
    pr_number = get_pr_number(args.github_ref)
    guidance = [
        label.name.split(':')[-1] for label in repo.get_pull(pr_number).labels
        if label.name.startswith('semver-guidance:')
    ]
    if len(guidance) > 1:
        raise ValueError('Too many guidance labels applied! '
                         'Please remove extraneous "semver-guidance" labels '
                         f'from PR#{pr_number}')
    elif not guidance:
        raise ValueError(
            'No guidance labels provided. Please add a label to '
            f'pull request #{pr_number} in the format of '
            f"'semver-guidance:foo' where 'foo' is one of "
            "prerelease, patch, minor, major, or some explicit "
            "version string."
        )

    set_ci_output('pr-number', pr_number)
    set_ci_output('guidance', guidance[0])
