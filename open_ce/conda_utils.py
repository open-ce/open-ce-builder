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
import pathlib
from logging import ERROR, getLogger
from datetime import datetime
import functools

import yaml

# Disabling pylint warning "cyclic-import" locally here doesn't work. So, added it in .pylintrc
# according to https://github.com/PyCQA/pylint/issues/59
from open_ce.utils import validate_dict_schema, check_if_conda_build_exists, generalize_version # pylint: disable=cyclic-import
from open_ce.errors import OpenCEError, Error

check_if_conda_build_exists()

# pylint: disable=wrong-import-position,wrong-import-order
import conda_build.api
from conda_build.config import get_or_merge_config
import conda_build.metadata
import conda.cli.python_api
# pylint: enable=wrong-import-position,wrong-import-order

def render_yaml(path, variants=None, variant_config_files=None, schema=None, permit_undefined_jinja=False):
    """
    Call conda-build's render tool to get a list of dictionaries of the
    rendered YAML file for each variant that will be built.
    """
    config = get_or_merge_config(None, variant=variants)
    config.variant_config_files = variant_config_files
    config.verbose = False

    if not os.path.isfile(path):
        metas = conda_build.api.render(path,
                                       config=config,
                                       bypass_env_check=True,
                                       finalize=False)
    else:
        # api.render will only work if path is pointing to a meta.yaml file.
        # For other files, use the MetaData class directly.
        # The absolute path is needed because MetaData seems to do some caching based on file name.
        metas = conda_build.metadata.MetaData(
                            os.path.abspath(path),
                            config=config).get_rendered_recipe_text(permit_undefined_jinja=permit_undefined_jinja)
    if schema:
        validate_dict_schema(metas, schema)
    return metas

def get_output_file_paths(meta, variants):
    """
    Get the paths of all of the generated packages for a recipe.
    """
    config = get_or_merge_config(None, variant=variants)
    config.verbose = False

    out_files = conda_build.api.get_output_file_paths(meta, config=config)

    # Only return the package name and the parent directory. This will show where within the output
    # directory the package should be.
    result = []
    for out_file in out_files:
        path = pathlib.PurePath(out_file)
        result.append(os.path.join(path.parent.name, path.name))

    return result

def conda_package_info(channels, package):
    '''
    Get conda package info.
    '''

    # Call "conda search --info" through conda's cli.python_api
    channel_args = sum((["-c", channel] for channel in channels), [])
    search_args = ["--info", generalize_version(package)] + channel_args
    # Setting the logging level allows us to ignore unnecessary output
    conda_logger = getLogger("conda.common.io")
    conda_logger.setLevel(ERROR)
    std_out, _, ret_code = conda.cli.python_api.run_command(conda.cli.python_api.Commands.SEARCH,
                               search_args, use_exception_handler=True, stderr=None)

    # Parsing the normal output from "conda search --info" instead of using the json flag. Using the json
    # flag adds a lot of extra time due to a slow regex in the conda code that is attempting to parse out
    # URL tokens.
    entries = []
    for entry in std_out.split("\n\n"):
        _, file_name, rest = entry.partition("file name")
        if file_name:
            entry = yaml.safe_load(file_name + rest)
            # Convert time string into a timestamp
            entry["timestamp"] = datetime.timestamp(datetime.strptime(entry["timestamp"], '%Y-%m-%d %H:%M:%S %Z'))
            if not entry["dependencies"]:
                entry["dependencies"] = []
            entries.append(entry)
    if ret_code:
        raise OpenCEError(Error.CONDA_PACKAGE_INFO, str(search_args), std_out)
    return entries

# Turn the channels argument into a tuple so that it can be hashable. This will allow the results
# of get_latest_package_info to be memoizable using lru_cache.
def _make_hashable_args(function):
    def wrapper(channels, package):
        return function(tuple(channels), package)
    return wrapper

@_make_hashable_args
@functools.lru_cache(maxsize=1024)
def get_latest_package_info(channels, package):
    '''
    Get the conda package info for the most recent search result.
    '''
    package_infos = conda_package_info(channels, package)
    retval = package_infos[0]
    for package_info in package_infos:
        if package_info["timestamp"] > retval["timestamp"]:
            retval = package_info
    return retval
