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
Script: create_opence_release.py
A script that can be used to cut an open-ce release.
*******************************************************************************
"""

import sys
import pathlib
import os
import glob
import re
import git_utils
import tag_all_repos

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
from open_ce import inputs # pylint: disable=wrong-import-position
from open_ce.conda_utils import render_yaml

def _make_parser():
    ''' Parser input arguments '''
    parser = inputs.make_parser([git_utils.Argument.PUBLIC_ACCESS_TOKEN, git_utils.Argument.REPO_DIR,
                                    git_utils.Argument.BRANCH, git_utils.Argument.SKIPPED_REPOS,
                                    git_utils.Argument.NOT_DRY_RUN],
                                    description = 'A script that can be used to cut an open-ce release.')

    parser.add_argument(
        '--github-org',
        type=str,
        default="open-ce",
        help="""Org to cut an Open-CE release in.""")

    parser.add_argument(
        '--primary-repo',
        type=str,
        default="open-ce",
        help="""Primary open-ce repo.""")

    parser.add_argument(
        '--version',
        type=str,
        required=True,
        help="""Release version to cut.""")

    parser.add_argument(
        '--code-name',
        type=str,
        default=None,
        help="""Code name for release.""")

    return parser

def _main(arg_strings=None):
    parser = _make_parser()
    args = parser.parse_args(arg_strings)

    #version_name = "open-ce-v{}".format(args.version)
    #release_number = ".".join(args.version.split(".")[:-1])
    #branch_name = "open-ce-r{}".format(release_number)
    primary_repo_url = "git@github.com:{}/{}.git".format(args.github_org, args.primary_repo)

    #version_msg = "Open-CE Version {}".format(args.version)
    #release_name = "v{}".format(args.version)
    #if args.code_name:
    #    version_msg = "{} Code-named {}".format(version_msg, args.code_name)
    #    release_name = "{} ({})".format(release_name, args.code_name)

    primary_repo_path = os.path.abspath(os.path.join(args.repo_dir, args.primary_repo))
    print("--->Making clone location: " + primary_repo_path)
    os.makedirs(primary_repo_path, exist_ok=True)
    print("--->Cloning {}".format(primary_repo_url))
    git_utils.clone_repo(primary_repo_url, primary_repo_path, args.branch)

    open_ce_env_file = os.path.join(primary_repo_path, "envs", "open-ce-env.yaml")
    if not _has_git_tag_changed(primary_repo_path, open_ce_env_file):
        print("--->No release is needed.")
        return

    version_name = _get_git_tag_from_env_file(open_ce_env_file)
    version = _git_tag_to_version(version_name)
    release_number = ".".join(version.split(".")[:-1])
    branch_name = "open-ce-r{}".format(release_number)
    version_msg = "Open-CE Version {}".format(version)
    release_name = "v{}".format(version)

    print("--->Creating {} branch in {}".format(version_name, args.primary_repo))
    git_utils.create_branch(primary_repo_path, branch_name)

    #print("--->Updating env files.")
    #_update_env_files(primary_repo_path, version_name)

    #print("--->Committing env files.")
    #git_utils.commit_changes(primary_repo_path, "Updates for {}".format(release_number))

    print("--->Tag Primary Branch")
    git_utils.create_tag(primary_repo_path, version_name, version_msg)

    if args.not_dry_run:
        print("--->Pushing branch.")
        git_utils.push_branch(primary_repo_path, branch_name)
        print("--->Pushing tag.")
        git_utils.push_branch(primary_repo_path, version_name)
    else:
        print("--->Skipping pushing for dry run.")

    repos = _get_all_feedstocks(env_file=open_ce_env_file,
                                github_org=args.github_org,
                                pat=args.pat,
                                skipped_repos=[args.primary_repo, ".github"] + inputs.parse_arg_list(args.skipped_repos))
    tag_all_repos.clone_repos(repos=repos,
                              branch=args.branch,
                              repo_dir=args.repo_dir,
                              prev_tag=None)
    tag_all_repos.tag_repos(repos=repos,
                            tag=version_name,
                            tag_msg=version_msg,
                            repo_dir=args.repo_dir)
    if args.not_dry_run:
        tag_all_repos.push_repos(repos=repos,
                                tag=version_name,
                                repo_dir=args.repo_dir,
                                continue_query=False)
    else:
        print("--->Skipping pushing feedstocks.")

    if args.not_dry_run:
        print("--->Creating Draft Release.")
        git_utils.create_release(args.github_org, args.primary_repo, args.pat, version_name, release_name, version_msg, True)
    else:
        print("--->Skipping release creation.")

def _get_git_tag_from_env_file(env_file):
    rendered_env_file = render_yaml(env_file, permit_undefined_jinja=True)
    if "git_tag_for_env" in rendered_env_file:
        return rendered_env_file["git_tag_for_env"]
    return None

def _has_git_tag_changed(repo_path, env_file):
    current_commit = git_utils.get_current_branch(repo_path)

    git_utils.checkout(repo_path, "HEAD~")
    previous_tag = _get_git_tag_from_env_file(env_file)

    git_utils.checkout(repo_path, current_commit)
    current_tag = _get_git_tag_from_env_file(env_file)

    return previous_tag == current_tag

def _git_tag_to_version(git_tag):
    version_regex = re.compile("open-ce-v(.+)")
    match = version_regex.match(git_tag)
    return match.groups()[1]

def _get_all_feedstocks(env_file, github_org, pat, skipped_repos):
    org_repos = git_utils.get_all_repos(github_org, pat)
    org_repos = [repo for repo in org_repos if repo["name"] not in skipped_repos]

    return org_repos

def _update_env_files(open_ce_path, new_git_tag):
    for env_file in glob.glob(os.path.join(open_ce_path, "envs", "*.yaml")):
        print("--->Updating {}".format(env_file))
        with open(env_file, 'r') as content_file:
            env_file_contents = content_file.read()
        if not "git_tag_for_env" in env_file_contents:
            env_file_contents = """{}
git_tag_for_env: {}
""".format(env_file_contents, new_git_tag)

        with open(env_file, 'w') as content_file:
            content_file.write(env_file_contents)

if __name__ == '__main__':
    try:
        _main()
        sys.exit(0)
    except Exception as exc:# pylint: disable=broad-except
        print("Error: ", exc)
        sys.exit(1)
