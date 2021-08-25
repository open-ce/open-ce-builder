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
import re
import tempfile
import git_utils
import tag_all_repos

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
from open_ce import inputs # pylint: disable=wrong-import-position
from open_ce import env_config # pylint: disable=wrong-import-position
from open_ce import utils # pylint: disable=wrong-import-position
from open_ce.conda_utils import render_yaml # pylint: disable=wrong-import-position

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
    current_tag = _get_git_tag_from_env_file(open_ce_env_file)
    previous_tag = _get_previous_git_tag_from_env_file(primary_repo_path, args.branch, open_ce_env_file)
    version_name = _get_git_tag_from_env_file(open_ce_env_file)
    version = _git_tag_to_version(version_name)
    release_number = ".".join(version.split(".")[:-1])
    branch_name = "open-ce-r{}".format(release_number)
    version_msg = "Open-CE Version {}".format(version)
    release_name = "v{}".format(version)

    if not git_utils.branch_exists(primary_repo_path, branch_name):
        print("--->Creating {} branch in {}".format(version_name, args.primary_repo))
        git_utils.create_branch(primary_repo_path, branch_name)
    else:
        print("--->Branch {} already exists in {}. Not creating it.".format(version_name, args.primary_repo))

    print("--->Tag Primary Branch")
    git_utils.create_tag(primary_repo_path, version_name, version_msg)

    if args.not_dry_run:
        print("--->Pushing branch.")
        git_utils.push_branch(primary_repo_path, branch_name)
        print("--->Pushing tag.")
        git_utils.push_branch(primary_repo_path, version_name)
    else:
        print("--->Skipping pushing branch and tag for dry run.")

    env_file_contents = _load_env_config_files(open_ce_env_file, variants)
    for env_file_content in env_file_contents:
        env_file_tag = env_file_content.get(env_config.Key.git_tag_for_env.name, None)
        if env_file_tag != current_tag:
            raise Exception("Incorrect git_tag '{}' found in the following env_file:\n{}".format(env_file_tag, env_file_content))

    repos = _get_all_feedstocks(env_files=env_file_contents,
                                github_org=args.github_org,
                                pat=args.pat,
                                skipped_repos=[args.primary_repo, ".github"] + inputs.parse_arg_list(args.skipped_repos))

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

def _get_git_tag_from_env_file(env_file):
    with open(env_file, mode='r') as file:
        file_contents = file.read()
    with tempfile.NamedTemporaryFile(suffix=os.path.basename(env_file), delete=True, mode='w') as renamed_env_file:
        renamed_env_file.write(file_contents)
        renamed_env_file.flush()
        rendered_env_file = render_yaml(renamed_env_file.name, permit_undefined_jinja=True)
    return rendered_env_file.get(env_config.Key.git_tag_for_env.name, None)

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
    return (current_tag is not None) and previous_tag != current_tag

def _git_tag_to_version(git_tag):
    version_regex = re.compile("open-ce-v(.+)")
    match = version_regex.match(git_tag)
    return match.groups()[0]

def _get_all_feedstocks(env_files, github_org, skipped_repos, pat=None):
    feedstocks = set()
    for env in env_files:
        for package in env.get(env_config.Key.packages.name, []):
            feedstock = package.get(env_config.Key.feedstock.name, "")
            if not utils.is_url(feedstock):
                feedstocks.add(feedstock)

    org_repos = [{"name": "{}-feedstock".format(feedstock),
                  "ssh_url": "https://{}github.com/{}/{}-feedstock.git".format(pat + "@" if pat else "",
                                                                               github_org,
                                                                               feedstock)}
                        for feedstock in feedstocks]

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
    _main()
