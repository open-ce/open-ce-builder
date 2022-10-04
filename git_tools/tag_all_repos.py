#!/usr/bin/env python
# *****************************************************************
# (C) Copyright IBM Corp. 2020, 2021. All Rights Reserved.
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
*******************************************************************************
Script: tag_all_repos.py
A script that can be used to create the same annotated git tag in all
repos within an organization.

To tag all of the feedstocks in the open-ce org with the tag `open-ce-v1.0.0`,
the following command can be used:
./git_tools/tag_all_repos.py open-ce \\
                             --tag open-ce-v1.0.0 \\
                             --tag-msg "Open-CE Release Version 1.0.0" \\
                             --pat ${YOUR_PUBLIC_ACCESS_TOKEN} \\
                             --repo-dir ./repos \\
                             --branch main \\
                             --skipped_repos open-ce
*******************************************************************************
"""

import os
import sys
import pathlib
import git_utils

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
from open_ce import inputs # pylint: disable=wrong-import-position

def _make_parser():
    ''' Parser input arguments '''
    parser = inputs.make_parser([git_utils.Argument.PUBLIC_ACCESS_TOKEN, git_utils.Argument.REPO_DIR,
                                    git_utils.Argument.BRANCH, git_utils.Argument.ORG, git_utils.Argument.SKIPPED_REPOS],
                                    description = """
                                    Tag all repos in an organization using the following logic:
                                    1- If the branch argument is passed in and that branch exists in the repo, the tag will be made at the tip of that branch.
                                    2- Otherwise, if a previous-tag is passed, the tag will be made at the tip of the latest branch which contains that tag.
                                    3- Finally, if none of these cases hold, the tag is made at the tip of the default branch.
                                    """)

    parser.add_argument(
        '--tag',
        type=str,
        required=True,
        help="""Tag to create.""")

    parser.add_argument(
        '--tag-msg',
        type=str,
        required=True,
        help="""Tag message to use.""")

    parser.add_argument(
        '--previous-tag',
        '--prev-tag',
        type=str,
        default=None,
        help="""Previous tag to find the branch to tag.""")

    return parser

def tag_all_repos(github_org, tag, tag_msg, branch, repo_dir, pat, skipped_repos, prev_tag): # pylint: disable=too-many-arguments
    '''
    Clones, then tags all repos with a given tag, and pushes back to remote.
    These steps are performed in separate loops to make debugging easier.
    '''
    skipped_repos = inputs.parse_arg_list(skipped_repos)
    repos = git_utils.get_all_repos(github_org, pat)
    repos = [repo for repo in repos if repo["name"] in skipped_repos ]

    clone_repos(repos, branch, repo_dir, prev_tag)

    tag_repos(repos, tag, tag_msg, repo_dir)

    push = git_utils.ask_for_input("Would you like to push all tags to remote?")
    if not push.startswith("y"):
        return

    push_repos(repos, tag, repo_dir)

def clone_repos(repos, branch, repo_dir, prev_tag):
    '''
    Clones a list of repos.
    '''
    print("---------------------------Cloning all Repos")
    for repo in repos:
        repo_path = os.path.abspath(os.path.join(repo_dir, repo["name"]))
        print("--->Making clone location: " + repo_path)
        os.makedirs(repo_path, exist_ok=True)
        print(f"--->Cloning {repo['name']}")
        git_utils.clone_repo(repo["ssh_url"], repo_path)
        if branch and git_utils.branch_exists(repo_path, branch):
            print(f"--->Branch '{branch}' exists, checking it out.")
            git_utils.checkout(repo_path, branch)
        elif prev_tag:
            repo_branch = git_utils.get_tag_branch(repo_path, prev_tag)
            print(f"-->Repo branch is: {repo_branch}")
            if git_utils.branch_exists(repo_path, os.path.basename(repo_branch)):
                print(f"--->Checking out branch '{repo_branch}' which contains tag '{prev_tag}'.")
                git_utils.checkout(repo_path, repo_branch)

def tag_repos(repos, tag, tag_msg, repo_dir):
    '''
    Tags a list of repos.
    '''
    print("---------------------------Tagging all Repos")
    for repo in repos:
        repo_path = os.path.abspath(os.path.join(repo_dir, repo["name"]))
        print(f"--->Tagging {repo['name']}")
        git_utils.create_tag(repo_path, tag, tag_msg)

def push_repos(repos, tag, repo_dir, continue_query=True):
    '''
    Pushes a list of repos.
    '''
    print("---------------------------Pushing all Repos")
    for repo in repos:
        try:
            repo_path = os.path.abspath(os.path.join(repo_dir, repo["name"]))
            print(f"--->Pushing {repo['name']}")
            git_utils.push_branch(repo_path, tag)
        except Exception as ex:# pylint: disable=broad-except
            print(f"Error encountered when trying to push {repo['name']}")
            print(ex)
            if not continue_query:
                continue
            cont_tag = git_utils.ask_for_input("Would you like to continue tagging other repos?")
            if cont_tag.startswith("y"):
                continue
            raise

def _main(arg_strings=None):
    parser = _make_parser()
    args = parser.parse_args(arg_strings)
    tag_all_repos(args.github_org,
                  args.tag,
                  args.tag_msg,
                  args.branch,
                  args.repo_dir,
                  args.pat,
                  args.skipped_repos,
                  args.previous_tag)

if __name__ == '__main__':
    try:
        _main()
    except Exception as exc:# pylint: disable=broad-except
        print("Error: ", exc)
        sys.exit(1)
