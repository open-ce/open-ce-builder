#!/usr/bin/env python
# *****************************************************************
# (C) Copyright IBM Corp. 2024. All Rights Reserved.
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
Script: create_opence_common_release.py
A script that can be used to cut an open-ce-common release.
*******************************************************************************
"""

import sys
import pathlib
import os
import re
import git_utils
import tag_all_repos

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
from open_ce.inputs import Argument, make_parser # pylint: disable=wrong-import-position
from open_ce.utils import parse_arg_list # pylint: disable=wrong-import-position
from open_ce import env_config # pylint: disable=wrong-import-position
from open_ce import utils # pylint: disable=wrong-import-position

def _make_parser():
    ''' Parser input arguments '''
    parser = make_parser([git_utils.Argument.PUBLIC_ACCESS_TOKEN, git_utils.Argument.REPO_DIR,
                                    git_utils.Argument.BRANCH, git_utils.Argument.SKIPPED_REPOS,
                                    git_utils.Argument.NOT_DRY_RUN, Argument.CONDA_BUILD_CONFIG],
                                    description = 'A script that can be used to cut an open-ce-common release.')

    parser.add_argument(
        '--github-org',
        type=str,
        default="open-ce",
        help="""Org to cut an Open-CE Python release in.""")

    parser.add_argument(
        '--primary-repo',
        type=str,
        default="open-ce-common",
        help="""Primary open-ce-common repo.""")

    parser.add_argument(
        '--code-name',
        type=str,
        default=None,
        help="""Code name for release.""")

    return parser

def _main(arg_strings=None): # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    parser = _make_parser()
    args = parser.parse_args(arg_strings)

    config_file = None
    if args.conda_build_configs:
        config_file = os.path.abspath(args.conda_build_configs)

    primary_repo_path = "./"

    open_ce_py_env_file = os.path.abspath(os.path.join(primary_repo_path, "envs", "python-env.yaml"))
    if not git_utils.has_git_tag_changed(primary_repo_path, args.branch, open_ce_py_env_file):
        print("--->The python-env git_tag has not changed.")
        print("--->No release is needed.")
        return
    print("--->The python-env git_tag has changed!")
    current_tag = git_utils.get_git_tag_from_env_file(open_ce_py_env_file)
    previous_tag = git_utils.get_previous_git_tag_from_env_file(primary_repo_path, args.branch, open_ce_py_env_file)
    version = _git_tag_to_version(current_tag)
    release_number = ".".join(version.split(".")[:-1])
    bug_fix = version.split(".")[-1]
    branch_name = f"open-ce-common-r{release_number}"
    version_msg = f"Open-CE Common Version {version}"
    release_name = f"v{version}"

    variants = utils.ALL_VARIANTS()
    env_file_contents = []
    for variant in variants:
        env_file_contents += env_config.load_env_config_files([open_ce_py_env_file],
                                                          [variant], ignore_urls=True)
    for env_file_content in env_file_contents:
        env_file_tag = env_file_content.get(env_config.Key.git_tag_for_env.name, None)
        if env_file_tag != current_tag:
            message = f"Incorrect {env_config.Key.git_tag_for_env.name} '{env_file_tag}' found " \
                      f"in the following env_file:\n{env_file_content}"
#            raise Exception(message)
            raise ValueError(message)

    if not git_utils.branch_exists(primary_repo_path, branch_name):
        print(f"--->Creating {branch_name} branch in {args.primary_repo}")
        git_utils.create_branch(primary_repo_path, branch_name)
    else:
        print(f"--->Branch {current_tag} already exists in {args.primary_repo}. Not creating it.")

    print("--->Tag Primary Branch")
    git_utils.create_tag(primary_repo_path, current_tag, version_msg)

    if args.not_dry_run:
        print("--->Pushing branch.")
        git_utils.push_branch(primary_repo_path, branch_name)
        print("--->Pushing tag.")
        git_utils.push_branch(primary_repo_path, current_tag)
    else:
        print("--->Skipping pushing branch and tag for dry run.")

    repos = git_utils.get_all_feedstocks(env_files=env_file_contents,
                                github_org=args.github_org,
                                pat=args.pat,
                                skipped_repos=[args.primary_repo, ".github"] + parse_arg_list(args.skipped_repos))

    repos.sort(key=lambda repo: repo["name"])

    tag_all_repos.clone_repos(repos=repos,
                              branch=None,
                              repo_dir=args.repo_dir,
                              prev_tag=previous_tag)
    tag_all_repos.tag_repos(repos=repos,
                            tag=current_tag,
                            tag_msg=version_msg,
                            repo_dir=args.repo_dir)
    if args.not_dry_run:
        tag_all_repos.push_repos(repos=repos,
                                tag=current_tag,
                                repo_dir=args.repo_dir,
                                continue_query=False)
    else:
        print("--->Skipping pushing feedstocks for dry run.")

    print("--->Generating Release Notes.")
    release_notes = _create_release_notes(repos,
                                          version,
                                          release_number,
                                          bug_fix,
                                          current_tag,
                                          previous_tag,
                                          utils.ALL_VARIANTS(),
                                          config_file,
                                          repo_dir=args.repo_dir,)
    print(release_notes)

    if args.not_dry_run:
        print("--->Creating Draft Release.")
        git_utils.create_release(args.github_org,
                                 args.primary_repo,
                                 args.pat,
                                 current_tag,
                                 release_name,
                                 release_notes,
                                 True)
    else:
        print("--->Skipping release creation for dry run.")

def _git_tag_to_version(git_tag):
    version_regex = re.compile("open-ce-common-v(.+)")
    match = version_regex.match(git_tag)
    return match.groups()[0]

def _create_release_notes(repos, version, release_number, bug_fix, current_tag, # pylint: disable=too-many-arguments
                          previous_tag, variants, config_file, repo_dir="./"):
    retval = f"# Open-CE Common Version {version}\n"
    retval += "\n"
    if previous_tag:
        retval += f"This is bug fix {bug_fix} of [release {release_number} of Open Cognitive Environment "
        retval += f"(Open-CE)](https://github.com/open-ce/open-ce-common/releases/tag/open-ce-common-v{release_number}.0).\n"
    else:
        retval += f"This is release {version} of Open-CE Common.\n"
    retval += "\n"
    if previous_tag:
        retval += "## Bug Fix Changes\n"
        retval += "\n"
        try:
            retval += git_utils.get_bug_fix_changes([{"name": "open-ce-common"}], current_tag, previous_tag, "../")
            retval += git_utils.get_bug_fix_changes(repos, current_tag, previous_tag, repo_dir)
        except Exception as exc:# pylint: disable=broad-except
            print("Error trying to find bug fix changes: ", exc)
        retval += "\n"
    retval += "## Python Versions\n"
    retval += "\n"
    retval += "A release of Open-CE Common provides common packages for OpenCE."
    retval += "The following packages are part of this release:\n"
    retval += "\n"
    retval += "| Package          | Version |\n"
    retval += "| :--------------- | :-------- |\n"
    try:
        retval += git_utils.get_package_versions(repos, repo_dir, variants, config_file)
    except Exception as exc:# pylint: disable=broad-except
        print("Error trying to get package versions: ", exc)
    retval += "\n"
    return retval

if __name__ == '__main__':
    _main()
