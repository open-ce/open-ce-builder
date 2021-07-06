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

# Disabling pylint warning "cyclic-import" locally here doesn't work. So, added it in .pylintrc
# according to https://github.com/PyCQA/pylint/issues/59
from open_ce.utils import validate_dict_schema, check_if_package_exists, generalize_version # pylint: disable=cyclic-import
from open_ce.errors import OpenCEError, Error
import open_ce.yaml_utils
from open_ce import __version__ as open_ce_version

check_if_package_exists('conda-build')

# pylint: disable=wrong-import-position,wrong-import-order
import conda_build.api
from conda_build.config import get_or_merge_config
import conda_build.metadata
import conda.cli.python_api
from conda.models.match_spec import MatchSpec
from conda.models.version import VersionOrder
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
    Get the latest conda package info with the following priority:
      1. Most Specific Channel
      2. Latest Version
      3. Largest Build Number
      4. Latest Timestamp
    '''

    # Skip virtual packages (these have leading "__" in the name)
    if package.startswith("__"):
        return ""

    channel_args = sum(([["--override-channels", "-c", channel]] for channel in channels), [])
    channel_args += [[]] # use defaults for last search
    all_std_out = ""
    for channel_arg in channel_args:
        search_args = ["--info", generalize_version(package)] + channel_arg
        # Setting the logging level allows us to ignore unnecessary output
        getLogger("conda.common.io").setLevel(ERROR)
        # Call "conda search --info" through conda's cli.python_api
        std_out, _, _ = conda.cli.python_api.run_command(conda.cli.python_api.Commands.SEARCH,
                                search_args, use_exception_handler=True)
        all_std_out += std_out
        # Parsing the normal output from "conda search --info" instead of using the json flag. Using the json
        # flag adds a lot of extra time due to a slow regex in the conda code that is attempting to parse out
        # URL tokens
        entries = list()
        for entry in std_out.split("\n\n"):
            _, file_name, rest = entry.partition("file name")
            if file_name:
                entry = open_ce.yaml_utils.load(file_name + rest)
                # Convert time string into a timestamp (if there is a timestamp)
                if "timestamp" in entry:
                    entry["timestamp"] = datetime.timestamp(datetime.strptime(entry["timestamp"], '%Y-%m-%d %H:%M:%S %Z'))
                else:
                    entry["timestamp"] = 0
                if not entry["dependencies"]:
                    entry["dependencies"] = []
                entry["version_order"] = VersionOrder(str(entry["version"]))
                entries.append(entry)
        if entries:
            retval = entries[0]
            for package_info in entries:
                if package_info["version_order"] < retval["version_order"]:
                    continue
                if package_info["build number"] < retval["build number"]:
                    continue
                if package_info["timestamp"] < retval["timestamp"]:
                    continue
                retval = package_info
            return retval
    raise OpenCEError(Error.CONDA_PACKAGE_INFO, "conda search --info " + generalize_version(package), all_std_out)

def version_matches_spec(spec_string, version=open_ce_version):
    '''
    Uses conda version specification syntax to check if version matches spec_string.
    e.g.
    version_matches_spec(">=1.2,<1.3", "1.2.1") -> True
    version_matches_spec(">=1.2,<1.3", "1.3.0") -> False
    '''
    match_spec = MatchSpec("test[version='{}']".format(spec_string))
    query_pkg = {"name": "test", "version": version, "build": "", "build_number": 0}
    return match_spec.match(query_pkg)

def output_file_to_string(output_file):
    '''
    Given a package file name,
    returns a string that can be used within a conda environment file to reference the package specifically.
    '''
    match_spec = MatchSpec.from_dist_str(os.path.basename(output_file))
    return "{} {} {}".format(match_spec.get("name", ""), match_spec.get("version", ""), match_spec.get("build", "")).strip()
