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
from create_version_branch import _get_repo_version

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
from open_ce import inputs # pylint: disable=wrong-import-position
from open_ce import env_config # pylint: disable=wrong-import-position
from open_ce import utils # pylint: disable=wrong-import-position
from open_ce.conda_utils import render_yaml # pylint: disable=wrong-import-position

def _make_parser():
    ''' Parser input arguments '''
    parser = inputs.make_parser([git_utils.Argument.PUBLIC_ACCESS_TOKEN, git_utils.Argument.REPO_DIR,
                                    git_utils.Argument.BRANCH, git_utils.Argument.SKIPPED_REPOS,
                                    git_utils.Argument.NOT_DRY_RUN, inputs.Argument.CONDA_BUILD_CONFIG] +
                                    inputs.VARIANT_ARGS,
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

def _main(arg_strings=None): # pylint: disable=too-many-locals, too-many-statements
    parser = _make_parser()
    args = parser.parse_args(arg_strings)

    variants = utils.make_variants(args.python_versions, args.build_types,
                                   args.mpi_types, args.cuda_versions)
    config_file = None
    if args.conda_build_configs:
        config_file = os.path.abspath(args.conda_build_configs)

    primary_repo_path = "./"

    open_ce_env_file = os.path.abspath(os.path.join(primary_repo_path, "envs", "opence-env.yaml"))
    if not _has_git_tag_changed(primary_repo_path, args.branch, open_ce_env_file):
        print("--->The opence-env git_tag has not changed.")
        print("--->No release is needed.")
        return
    print("--->The opence-env git_tag has changed!")
    current_tag = _get_git_tag_from_env_file(open_ce_env_file)
    previous_tag = _get_previous_git_tag_from_env_file(primary_repo_path, args.branch, open_ce_env_file)
    version = _git_tag_to_version(current_tag)
    release_number = ".".join(version.split(".")[:-1])
    branch_name = "open-ce-r{}".format(release_number)
    version_msg = "Open-CE Version {}".format(version)
    release_name = "v{}".format(version)

    env_file_contents = env_config.load_env_config_files([open_ce_env_file], variants, ignore_urls=True)
    for env_file_content in env_file_contents:
        env_file_tag = env_file_content.get(env_config.Key.git_tag_for_env.name, None)
        if env_file_tag != current_tag:
            message = "Incorrect {} '{}' found in the following env_file:\n{}".format(env_config.Key.git_tag_for_env.name,
                                                                                      env_file_tag,
                                                                                      env_file_content)
            raise Exception(message)

    if not git_utils.branch_exists(primary_repo_path, branch_name):
        print("--->Creating {} branch in {}".format(current_tag, args.primary_repo))
        git_utils.create_branch(primary_repo_path, branch_name)
    else:
        print("--->Branch {} already exists in {}. Not creating it.".format(current_tag, args.primary_repo))

    print("--->Tag Primary Branch")
    git_utils.create_tag(primary_repo_path, current_tag, version_msg)

    if args.not_dry_run:
        print("--->Pushing branch.")
        git_utils.push_branch(primary_repo_path, branch_name)
        print("--->Pushing tag.")
        git_utils.push_branch(primary_repo_path, current_tag)
    else:
        print("--->Skipping pushing branch and tag for dry run.")

    repos = _get_all_feedstocks(env_files=env_file_contents,
                                github_org=args.github_org,
                                pat=args.pat,
                                skipped_repos=[args.primary_repo, ".github"] + inputs.parse_arg_list(args.skipped_repos))

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
                                          current_tag,
                                          previous_tag,
                                          variants,
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

def _get_git_tag_from_env_file(env_file):
    '''
    The way this function copies the env_file to a new location before it reads the env file
    is to get around an issue with the python jinja library used by conda build which seems
    to cache the file the first time it is read, even if the file is changed by checking out
    a new git commit.
    '''
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

def _create_release_notes(repos, version, current_tag, previous_tag, variants, config_file, repo_dir="./"): # pylint: disable=too-many-arguments
    retval = "# Open-CE Version {}\n".format(version)
    retval += "\n"
    retval += "Release Description\n"
    retval += "\n"
    if previous_tag:
        retval += "## Bug Fix Changes\n"
        retval += "\n"
        try:
            retval += _get_bug_fix_changes([{"name": "open-ce"}], current_tag, previous_tag, "../")
            retval += _get_bug_fix_changes(repos, current_tag, previous_tag, repo_dir)
        except Exception as exc:# pylint: disable=broad-except
            print("Error trying to find bug fix changes: ", exc)
        retval += "\n"
    retval += "## Package Versions\n"
    retval += "\n"
    retval += "A release of Open-CE consists of the environment files within the `open-ce` repository and a collection of "
    retval += "feedstock repositories. The feedstock repositories contain recipes for various python packages. The "
    retval += "following packages (among others) are part of this release:\n"
    retval += "\n"
    retval += "| Package          | Version |\n"
    retval += "| :--------------- | :-------- |\n"
    try:
        retval += _get_package_versions(repos, repo_dir, variants, config_file)
    except Exception as exc:# pylint: disable=broad-except
        print("Error trying to get package versions: ", exc)
    retval += "\n"
    retval += "This release of Open-CE supports NVIDIA's CUDA version 10.2 and 11.2 as well as Python 3.7, 3.8 and 3.9.\n"
    retval += "\n"
    retval += "## Getting Started"
    retval += "\n"
    retval += "To get started with this release, see [the main readme]"
    retval += "(https://github.com/open-ce/open-ce/blob/{}/README.md)\n".format(current_tag)
    return retval

def _get_bug_fix_changes(repos, current_tag, previous_tag, repo_dir="./"):
    retval = ""
    for repo in repos:
        repo_path = os.path.abspath(os.path.join(repo_dir, repo["name"]))
        print("--->Retrieving bug_fix_changes for {}".format(repo))
        changes = git_utils.get_commits(repo_path, previous_tag, current_tag, commit_format="* %s")
        if changes:
            retval += "### Changes For {}\n".format(repo["name"])
            retval += "\n"
            retval +=  changes
            retval += "\n"
            retval += "\n"
    return retval

def _get_package_versions(repos, repo_dir, variants, config_file):
    retval = ""
    for repo in repos:
        repo_path = os.path.abspath(os.path.join(repo_dir, repo["name"]))
        print("--->Getting version info for {}".format(repo))
        version, name = _get_repo_version(repo_path, variants, config_file)
        retval += "| {} | {} |\n".format(name, version)
    return retval

if __name__ == '__main__':
    _main()
