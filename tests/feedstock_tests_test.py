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

import os
import pathlib
import pytest
import sys
import shutil
from importlib.util import spec_from_loader, module_from_spec
from importlib.machinery import SourceFileLoader

test_dir = pathlib.Path(__file__).parent.absolute()
sys.path.append(os.path.join(test_dir, "feedstock_tests"))

import check_build_numbers
import check_recipes
import open_ce.utils as utils

repo_name = "test_git_repo"
git_repo = os.path.join(os.getcwd(), repo_name + ".git")

def create_git_repository():
    '''
    Create a local git repository that contains a conda recipe.
    The main branch will contain the meta.yaml file within test-meta1.yaml.
    The new branch will contain the meta.yaml file within test-meta2.yaml.
    '''
    meta_path = os.path.join("recipe", "meta.yaml")

    remove_git_repo()

    os.mkdir(git_repo)
    utils.run_and_log("git init --bare {}".format(git_repo))

    utils.run_and_log("git clone {}".format(git_repo))
    os.chdir(repo_name)
    os.mkdir("recipe")
    shutil.copy(os.path.join(test_dir, "test-meta1.yaml"), meta_path)
    utils.run_and_log("git add {}".format(meta_path))
    utils.run_and_log("git commit -a -m \"Initial Commit\"")
    utils.run_and_log("git push origin HEAD")

    utils.run_and_log("git checkout -b new_test_branch")
    shutil.copy(os.path.join(test_dir, "test-meta2.yaml"), meta_path)
    utils.run_and_log("git commit -a -m \"Test branch commit\"")

def remove_git_repo():
    '''
    Delete the test git repository.
    '''
    shutil.rmtree(git_repo, ignore_errors=True)
    shutil.rmtree(repo_name,  ignore_errors=True)

def test_check_build_numbers():
    '''
    Tests the check_build_number script.
    '''
    create_git_repository()

    # Verify that check passes when version is the same, and build number increases
    check_build_numbers.main(["--python_versions", "2.3", "--build_types", "cuda"])

    # Verify that check fails when version is the same, and build number is the same.
    with pytest.raises(AssertionError) as exc:
        check_build_numbers.main(["--python_versions", "2.3", "--build_types", "cpu"])
    assert "At least one package needs to increase the build number or change the version in at least one variant." in str(exc.value)

    # Verify that check passes when version increases and build number goes back to 1.
    check_build_numbers.main(["--python_versions", "2.4", "--build_types", "cpu"])

    # Verify that check passes when version increase and build number stays the same.
    check_build_numbers.main(["--python_versions", "2.4", "--build_types", "cuda"])

    os.chdir("..")
    remove_git_repo()

def test_check_recipe():
    '''
    Tests the check_recipe script.
    '''
    shutil.rmtree("recipe", ignore_errors=True)
    os.mkdir("recipe")
    meta_path = os.path.join("recipe", "meta.yaml")
    shutil.copy(os.path.join(test_dir, "test-meta2.yaml"), meta_path)

    check_recipes.main(["--python_versions", "2.3,2.4", "--build_types", "cpu,cuda"])

    shutil.rmtree("recipe", ignore_errors=True)

