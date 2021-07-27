"""
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

import os
from enum import Enum, unique, auto

from open_ce import utils
from open_ce.errors import OpenCEError, Error, show_warning
from open_ce import __version__ as open_ce_version

@unique
class Key(Enum):
    '''Enum for Env Config Keys'''
    builder_version = auto()
    imported_envs = auto()
    conda_build_configs = auto()
    channels = auto()
    packages = auto()
    git_tag_for_env = auto()
    git_tag = auto()
    feedstock = auto()
    recipes = auto()
    external_dependencies = auto()
    patches = auto()
    opence_env_file_path = auto()
    runtime_package = auto()
    recipe_path = auto()

_PACKAGE_SCHEMA ={
    Key.feedstock.name: utils.make_schema_type(str, True),
    Key.git_tag.name: utils.make_schema_type(str),
    Key.recipes.name: utils.make_schema_type([str]),
    Key.channels.name: utils.make_schema_type([str]),
    Key.patches.name: utils.make_schema_type([str]),
    Key.runtime_package.name: utils.make_schema_type(bool),
    Key.recipe_path.name: utils.make_schema_type(str)
}

_ENV_CONFIG_SCHEMA = {
    Key.builder_version.name: utils.make_schema_type(str),
    Key.imported_envs.name: utils.make_schema_type([str]),
    Key.channels.name: utils.make_schema_type([str]),
    Key.git_tag_for_env.name: utils.make_schema_type(str),
    Key.external_dependencies.name: utils.make_schema_type([str]),
    Key.conda_build_configs.name: utils.make_schema_type([str]),
    Key.packages.name: utils.make_schema_type([_PACKAGE_SCHEMA])
}

def _validate_config_file(env_file, variants):
    '''Perform some validation on the environment file after loading it.'''
    # pylint: disable=import-outside-toplevel
    from open_ce import conda_utils

    try:
        original_env_file = env_file
        if utils.is_url(env_file):
            env_file = utils.download_file(env_file)

        # First, partially render yaml to validate builder version number.
        version_check_obj = conda_utils.render_yaml(env_file, permit_undefined_jinja=True)
        if Key.builder_version.name in version_check_obj.keys():
            if not conda_utils.version_matches_spec(version_check_obj.get(Key.builder_version.name)):
                raise OpenCEError(Error.SCHEMA_VERSION_MISMATCH,
                                  original_env_file,
                                  version_check_obj.get(Key.builder_version.name),
                                  open_ce_version)

        meta_obj = None
        try:
            meta_obj = conda_utils.render_yaml(env_file, variants=variants, schema=_ENV_CONFIG_SCHEMA)
            if not (Key.packages.name in meta_obj.keys() or Key.imported_envs.name in meta_obj.keys()):
                raise OpenCEError(Error.CONFIG_CONTENT)
            meta_obj[Key.opence_env_file_path.name] = original_env_file
        except OpenCEError as exc:
            if Key.builder_version.name not in version_check_obj.keys():
                show_warning(Error.SCHEMA_VERSION_NOT_FOUND, original_env_file, Key.builder_version.name)
            raise exc
        return meta_obj
    except (Exception, SystemExit) as exc: #pylint: disable=broad-except
        raise OpenCEError(Error.ERROR, "Error in {}:\n  {}".format(original_env_file, str(exc))) from exc

def load_env_config_files(config_files, variants):
    '''
    Load all of the environment config files, plus any that come from "imported_envs"
    within an environment config file.
    '''
    env_config_files = [os.path.abspath(e) if not utils.is_url(e) else e for e in config_files]
    env_config_data_list = []
    loaded_files = []
    while env_config_files:
        # Load the environment config files using conda-build's API. This will allow for the
        # filtering of text using selectors and jinja2 functions
        env = _validate_config_file(env_config_files[0], variants)

        # Examine all of the imported_envs items and determine if they still need to be loaded.
        new_config_files = []
        imported_envs = env.get(Key.imported_envs.name, [])
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
