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
from open_ce import env_config # pylint: disable=wrong-import-position
from open_ce import utils # pylint: disable=wrong-import-position
from open_ce.conda_utils import render_yaml

def _make_parser():
    ''' Parser input arguments '''
    parser = inputs.make_parser([git_utils.Argument.PUBLIC_ACCESS_TOKEN, git_utils.Argument.REPO_DIR,
                                    git_utils.Argument.BRANCH, git_utils.Argument.SKIPPED_REPOS,
                                    git_utils.Argument.NOT_DRY_RUN] + inputs.VARIANT_ARGS,
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
        '--code-name',
        type=str,
        default=None,
        help="""Code name for release.""")

    return parser

def _main(arg_strings=None):
    parser = _make_parser()
    args = parser.parse_args(arg_strings)

    variants = utils.make_variants(args.python_versions, args.build_types,
                                   args.mpi_types, args.cuda_versions)

    primary_repo_path = "./"

    open_ce_env_file = os.path.abspath(os.path.join(primary_repo_path, "envs", "opence-env.yaml"))
    if not _has_git_tag_changed(primary_repo_path, args.branch, open_ce_env_file):
        print("--->The opence-env git_tag has not changed.")
        print("--->No release is needed.")
        return
    print("--->The opence-env git_tag has changed!")
    previous_tag = _get_previous_git_tag_from_env_file(primary_repo_path, args.branch, open_ce_env_file)
    print("previous_tag: ", previous_tag)
    version_name = _get_git_tag_from_env_file(open_ce_env_file)
    print("version_name: ", version_name)
    version = _git_tag_to_version(version_name)
    print("version: ", version)
    release_number = ".".join(version.split(".")[:-1])
    print("release_number: ", release_number)
    branch_name = "open-ce-r{}".format(release_number)
    print("branch_name: ", branch_name)
    version_msg = "Open-CE Version {}".format(version)
    print("version_msg: ", version_msg)
    release_name = "v{}".format(version)
    print("release_name: ", release_name)

    #Need if branch doesn't exist
    print("--->Creating {} branch in {}".format(version_name, args.primary_repo))
    git_utils.create_branch(primary_repo_path, branch_name)

    print("--->Tag Primary Branch")
    git_utils.create_tag(primary_repo_path, version_name, version_msg)

    if args.not_dry_run:
        print("--->Pushing branch.")
        git_utils.push_branch(primary_repo_path, branch_name)
        print("--->Pushing tag.")
        git_utils.push_branch(primary_repo_path, version_name)
    else:
        print("--->Skipping pushing branch and tag for dry run.")

    repos = _get_all_feedstocks(env_file=open_ce_env_file,
                                github_org=args.github_org,
                                pat=args.pat,
                                skipped_repos=[args.primary_repo, ".github"] + inputs.parse_arg_list(args.skipped_repos),
                                variants=variants)

    tag_all_repos.clone_repos(repos=repos,
                              branch=None,
                              repo_dir=args.repo_dir,
                              prev_tag=previous_tag)
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
        print("--->Skipping pushing feedstocks for dry run.")

    if args.not_dry_run:
        print("--->Creating Draft Release.")
        git_utils.create_release(args.github_org, args.primary_repo, args.pat, version_name, release_name, version_msg, True)
    else:
        print("--->Skipping release creation for dry run.")

counter = 0

def _get_git_tag_from_env_file(env_file):
    print("Env File: ", env_file)
    print("Env File Contents:")
    with open(env_file, mode='r') as file:
        file_contents = file.read()
        print(file_contents)
    global counter
    env_file = env_file + str(counter)
    counter += 1
    with open(env_file, mode='w') as file:
        file.write(file_contents)
    rendered_env_file = render_yaml(env_file, permit_undefined_jinja=True)
    os.remove(env_file)
    print("Rendered Env File: ")
    print(rendered_env_file)
    if "git_tag_for_env" in rendered_env_file:
        return rendered_env_file["git_tag_for_env"]
    return None

def _get_previous_git_tag_from_env_file(repo_path, previous_branch, env_file):
    current_commit = git_utils.get_current_commit(repo_path)

    git_utils.checkout(repo_path, previous_branch)
    previous_tag = _get_git_tag_from_env_file(env_file)

    git_utils.checkout(repo_path, current_commit)

    return previous_tag

def _has_git_tag_changed(repo_path, previous_branch, env_file):
    current_commit = git_utils.get_current_commit(repo_path)

    git_utils.checkout(repo_path, previous_branch)
    previous_tag = _get_git_tag_from_env_file(env_file)

    git_utils.checkout(repo_path, current_commit)
    current_tag = _get_git_tag_from_env_file(env_file)
    print("Previous Tag: ", previous_tag)
    print("Current Tag:  ", current_tag)
    return (current_tag is not None) and previous_tag != current_tag

def _git_tag_to_version(git_tag):
    version_regex = re.compile("open-ce-v(.+)")
    match = version_regex.match(git_tag)
    return match.groups()[0]

def _get_all_feedstocks(env_file, github_org, pat, skipped_repos, variants):
    env_files = _load_env_config_files(env_file, variants)
    org_repos = set()
    for env in env_files:
        for package in env.get(env_config.Key.packages.name, []):
            feedstock = package.get(env_config.Key.feedstock.name, "")
            if not utils.is_url(feedstock):
                org_repos.add({"name": feedstock,
                               "ssh_url": "https://github.com/{}/{}-feedstock.git".format(github_org, feedstock)})
    org_repos = [repo for repo in org_repos if repo["name"] not in skipped_repos]

    return org_repos

def _load_env_config_files(config_file, variants):
    '''
    Load all of the environment config files, plus any that come from "imported_envs"
    within an environment config file.
    '''
    env_config_files = [config_file]
    env_config_data_list = []
    loaded_files = []
    while env_config_files:
        for variant in variants:
            # Load the environment config files using conda-build's API. This will allow for the
            # filtering of text using selectors and jinja2 functions
            env = render_yaml(env_config_files[0], variants=variant, permit_undefined_jinja=True)

            # Examine all of the imported_envs items and determine if they still need to be loaded.
            new_config_files = []
            imported_envs = env.get(env_config.Key.imported_envs.name, [])
            if not imported_envs:
                imported_envs = []
            for imported_env in imported_envs:
                if not utils.is_url(imported_env):
                    imported_env = utils.expanded_path(imported_env, relative_to=env_config_files[0])
                    if not imported_env in env_config_files and not imported_env in loaded_files:
                        new_config_files += [imported_env]
        # If there are new files to load, add them to the env_conf_files list.
        # Otherwise, remove the current file from the env_conf_files list and
        # add its data to the env_config_data_list.
        if new_config_files:
            env_config_files = new_config_files + env_config_files
        else:
            env_config_data_list += [env]
            loaded_files += [env_config_files.pop(0)]

    return env_config_data_list

if __name__ == '__main__':
    #try:
    _main()
    sys.exit(0)
    #except Exception as exc:# pylint: disable=broad-except
    #    print("Error: ", exc)
    #    sys.exit(1)
