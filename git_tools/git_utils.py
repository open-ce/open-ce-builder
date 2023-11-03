#!/usr/bin/env python
"""
# *****************************************************************
# (C) Copyright IBM Corp. 2020, 2023. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# *****************************************************************
"""

import os
import sys
import pathlib
import subprocess
from enum import Enum, unique
import tempfile
import yaml
import requests
from create_version_branch import _get_repo_version   #pylint: disable=cyclic-import

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
from open_ce import utils, env_config # pylint: disable=wrong-import-position
from open_ce.conda_utils import render_yaml # pylint: disable=wrong-import-position

GITHUB_API = "https://api.github.com"

@unique
class Argument(Enum):
    '''Enum for Arguments'''
    PUBLIC_ACCESS_TOKEN = (lambda parser: parser.add_argument(
                                          '--pat',
                                          type=str,
                                          required=False,
                                          help="""Github public access token."""))

    REPO_DIR = (lambda parser: parser.add_argument(
                              '--repo-dir',
                              type=str,
                              default="./",
                              help="""Directory to store repos."""))

    BRANCH = (lambda parser: parser.add_argument(
                            '--branch',
                            type=str,
                            default=None,
                            help="""Branch to work from."""))

    ORG = (lambda parser: parser.add_argument(
                            'github_org',
                            type=str,
                            help="""Github org to tag."""))

    SKIPPED_REPOS = (lambda parser: parser.add_argument(
                            '--skipped_repos',
                            type=str,
                            default="",
                            help="""Comma delimitted list of repos to skip tagging."""))

    REVIEWERS = (lambda parser: parser.add_argument(
                            '--reviewers',
                            type=str,
                            default="",
                            help="""Comma delimitted list of PR reviewers."""))

    TEAM_REVIEWERS = (lambda parser: parser.add_argument(
                            '--team_reviewers',
                            type=str,
                            default="",
                            help="""Comma delimitted list of PR review teams."""))

    PARAMS = (lambda parser: parser.add_argument(
                            '--params',
                            type=str,
                            default="",
                            help="""Comma delimitted list of <key>:<val> param pairs."""))

    NOT_DRY_RUN = (lambda parser: parser.add_argument(
                             '--not_dry_run',
                             action='store_true',
                             required=False,
                             help="""Perform all steps locally, but don't push any changes."""))

def get_all_repos(github_org, token):
    '''
    Use the github API to get all repos for an org.
    https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#list-organization-repositories
    '''
    retval = []
    page_index = 1
    while True:
        options = f"sort=full_name&order=asc&page={page_index}&per_page=100"
        result = requests.get(f"{GITHUB_API}/orgs/{github_org}/repos?{options}",
                              headers={'Authorization' : f'token {token}'},timeout=300)
        if result.status_code != 200:
            raise ValueError("Error loading repos.")
        yaml_result = yaml.safe_load(result.content)
        if not yaml_result:
            return retval
        retval += yaml_result
        page_index += 1

def create_release(github_org, repo, token, tag_name, name, body, draft):# pylint: disable=too-many-arguments
    '''
    Use the github API to create an actual release on github.
    https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#create-a-release
    '''
    result = requests.post(f"{GITHUB_API}/repos/{github_org}/{repo}/releases",
                            headers={'Authorization' : f'token {token}'},
                            json={
                            "tag_name": tag_name,
                            "name": name,
                            "body": body,
                            "draft": draft
                            },timeout=300)
    if result.status_code != 201:
        raise ValueError("Error creating github release.")
    return yaml.safe_load(result.content)

def rename_branch(github_org, repo, token, old_name, new_name):# pylint: disable=too-many-arguments
    '''
    Use the github API to rename a branch
    https://docs.github.com/en/rest/reference/repos#rename-a-branch
    '''
    result = requests.post(f"{GITHUB_API}/repos/{github_org}/{repo}/branches/{old_name}/rename",
                            headers={'Authorization' : f'token {token}'},
                            json={
                            "new_name": new_name
                            },timeout=300)
    if result.status_code != 201:
        raise ValueError("Error renaming github release.")
    return yaml.safe_load(result.content)

def create_pr(github_org, repo, token, title, body, head, base):# pylint: disable=too-many-arguments
    '''
    Create a PR in the given Repo.
    https://docs.github.com/en/free-pro-team@latest/rest/reference/pulls#create-a-pull-request
    '''
    result = requests.post(f"{GITHUB_API}/repos/{github_org}/{repo}/pulls",
                           headers={'Authorization' : f'token {token}'},
                           json={
                               "title": title,
                               "body": body,
                               "head": head,
                               "base": base
                               },timeout=300)
    if result.status_code != 201:
        raise ValueError("Error creating PR.")
    return yaml.safe_load(result.content)

def request_pr_review(github_org, repo, token, pull_number, reviewers=None, team_reviewers=None):# pylint: disable=too-many-arguments
    '''
    Request reviewers for a pull request
    https://docs.github.com/en/rest/reference/pulls#request-reviewers-for-a-pull-request
    '''
    if not reviewers:
        reviewers = []
    if not team_reviewers:
        team_reviewers = []
    result = requests.post(f"{GITHUB_API}/repos/{github_org}/{repo}/pulls/{pull_number}/requested_reviewers",
                           headers={'Authorization' : f'token {token}'},
                           json={
                               "reviewers": reviewers,
                               "team_reviewers": team_reviewers
                               },timeout=300)
    if result.status_code != 201:
        raise ValueError(f"Error requesting PR review.:\n{result.content}")
    return yaml.safe_load(result.content)

def clone_repo(git_url, repo_dir, git_tag=None):
    '''Clone a repo to the given location.'''
    utils.git_clone(git_url, git_tag, repo_dir)

def get_tag_branch(repo_path, git_tag):
    """
    Find the most recent branch that contains git_tag.
    """
    saved_working_directory = os.getcwd()
    os.chdir(repo_path)
    retval = utils.get_branch_of_tag(git_tag)
    os.chdir(saved_working_directory)
    return retval

def _execute_git_command(repo_path, git_cmd):
    saved_working_directory = os.getcwd()
    os.chdir(repo_path)
    print(f"--->{git_cmd}")
    result,std_out,_ = utils.run_command_capture(git_cmd, stderr=subprocess.STDOUT)
    os.chdir(saved_working_directory)
    if not result:
        raise ValueError(f"Git command failed: {git_cmd}\n{std_out}")
    return std_out

def create_tag(repo_path, tag_name, tag_msg):
    '''Create an annotated tag in the given repo.'''
    _execute_git_command(repo_path, f"git tag -a {tag_name} -m \'{tag_msg}\'")

def create_branch(repo_path, branch_name):
    '''Create a branch in the given repo.'''
    _execute_git_command(repo_path, f"git checkout -b {branch_name}")

def branch_exists(repo_path, branch_name):
    '''Returns true if branch already exists.'''
    return _execute_git_command(repo_path, f"git ls-remote --heads origin {branch_name}") != ""

def commit_changes(repo_path, commit_msg):
    '''Commit the outstanding changes in the given repo.'''
    _execute_git_command(repo_path, "git add ./*")
    _execute_git_command(repo_path, f"git commit -avm \'{commit_msg}\'")

def push_branch(repo_path, branch_name, remote="origin"):
    '''Push the given repo to the remote branch.'''
    _execute_git_command(repo_path, f"git push {remote} {branch_name}")

def checkout(repo_path, commit):
    '''Checkout a commit of a given repo.'''
    _execute_git_command(repo_path, f"git checkout {commit}")

def ask_for_input(message, acceptable=None):
    '''Repeatedly ask for user input until an acceptable response is given.'''
    if not acceptable:
        acceptable = ["yes", "y", "no", "n"]
    display_message = f"{message} ({'/'.join(acceptable)}) > "
    user_input = input(display_message)
    while user_input.lower() not in acceptable:
        print(f"{user_input} is not a valid selection.")
        user_input = input(display_message)
    return user_input.lower()

def get_current_branch(repo_path):
    '''Retrieve the active branch of the given repo.'''
    return _execute_git_command(repo_path, "git rev-parse --abbrev-ref HEAD").strip()

def get_current_commit(repo_path):
    '''Retrieve the active branch of the given repo.'''
    return _execute_git_command(repo_path, "git rev-parse HEAD").strip()

def apply_patch(repo_path, patch_path):
    '''Apply a patch to the given repo.'''
    _execute_git_command(repo_path, f"cat \'{patch_path}\' | git am -3 -k")

def get_commits(repo_path, previous_tag, current_tag="HEAD", commit_format=None):
    '''Get a list of commits between made between 2 tags.'''
    format_option = ""
    if commit_format:
        format_option = f"--pretty=format:'{commit_format}'"
    return _execute_git_command(repo_path, f"git log {format_option} {previous_tag}..{current_tag}")

def fill_in_params(filename, params=None, **kwargs):
    '''
    Replace occurrences of `${key}` with `val`.
    '''
    with open(filename,mode='r',encoding='utf8') as text_file:
        text = text_file.read()

    if not params:
        params = {}

    for key, value in params:
        text = text.replace(f"${{{key}}}", value)

    for key, value in kwargs.items():
        text = text.replace("${{{key}}}", value)

    with tempfile.NamedTemporaryFile(suffix=os.path.basename(filename), delete=False).name as replaced_filename:
        with open(replaced_filename,mode='w',encoding='utf8') as text_file:
            text_file.write(text)

    return replaced_filename

def get_git_tag_from_env_file(env_file):
    '''
    The way this function copies the env_file to a new location before it reads the env file
    is to get around an issue with the python jinja library used by conda build which seems
    to cache the file the first time it is read, even if the file is changed by checking out
    a new git commit.
    '''
    with open(env_file, mode='r', encoding='utf8') as file:
        file_contents = file.read()
    with tempfile.NamedTemporaryFile(suffix=os.path.basename(env_file), delete=True, mode='w') as renamed_env_file:
        renamed_env_file.write(file_contents)
        renamed_env_file.flush()
        rendered_env_file = render_yaml(renamed_env_file.name, permit_undefined_jinja=True)
    return rendered_env_file.get(env_config.Key.git_tag_for_env.name, None)

def get_previous_git_tag_from_env_file(repo_path, previous_branch, env_file):
    '''
    This function returns git tag from previous branch of given repo, specified in env_file
    '''
    current_commit = get_current_commit(repo_path)

    checkout(repo_path, previous_branch)
    previous_tag = get_git_tag_from_env_file(env_file)

    checkout(repo_path, current_commit)

    return previous_tag

def has_git_tag_changed(repo_path, previous_branch, env_file):
    '''
    This function returns boolean value if git_tag has changed
    '''
    current_commit = get_current_commit(repo_path)

    checkout(repo_path, previous_branch)
    previous_tag = get_git_tag_from_env_file(env_file)

    checkout(repo_path, current_commit)
    current_tag = get_git_tag_from_env_file(env_file)
    return (current_tag is not None) and previous_tag != current_tag

def get_all_feedstocks(env_files, github_org, skipped_repos, pat=None):
    '''
    This function returns all the feedstocks specified in env_files
    '''
    feedstocks = set()
    for env in env_files:
        packages = env.get(env_config.Key.packages.name, [])
        if packages is None:
            packages = []
        for package in packages:
            feedstock = package.get(env_config.Key.feedstock.name, "")
            if not utils.is_url(feedstock):
                feedstocks.add(feedstock)

    org_repos = [{"name": f"{feedstock}-feedstock",
                  "ssh_url": f"https://{pat + '@' if pat else ''}github.com/{github_org}/{feedstock}-feedstock.git"}
                     for feedstock in feedstocks]

    org_repos = [repo for repo in org_repos if repo["name"] not in skipped_repos]

    return org_repos

def get_bug_fix_changes(repos, current_tag, previous_tag, repo_dir="./"):
    '''
    This function returns the list of bug fix changes
    '''
    retval = ""
    for repo in repos:
        repo_path = os.path.abspath(os.path.join(repo_dir, repo["name"]))
        print(f"--->Retrieving bug_fix_changes for {repo}")
        changes = get_commits(repo_path, previous_tag, current_tag, commit_format="* %s")
        if changes:
            retval += f"### Changes For {repo['name']}\n"
            retval += "\n"
            retval +=  changes
            retval += "\n"
            retval += "\n"
    return retval

def get_package_versions(repos, repo_dir, variants, config_file):
    '''
    This function returns package versions of repos
    '''
    retval = ""
    for repo in repos:
        repo_path = os.path.abspath(os.path.join(repo_dir, repo["name"]))
        print(f"--->Getting version info for {repo}")
        version, name = _get_repo_version(repo_path, variants, config_file)
        retval += f"| {name} | {version} |\n"
    return retval
