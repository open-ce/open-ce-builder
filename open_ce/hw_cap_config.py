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
from open_ce.errors import OpenCEError, Error, show_warning, log
from open_ce import __version__ as open_ce_version

@unique
class Key(Enum):
    '''Enum for HW Capabilities Config Keys'''
    builder_version = auto()
    cpu_capabilities = auto()
    cuda_capabilities = auto()
    compute_levels = auto()
    sm_levels = auto()
    vector_settings = auto()
    cpu_tune= auto()
    cpu_arch = auto()
    hw_cap_config_file_path = auto()

_CPU_CAPABILITIES_SCHEMA ={
    Key.cpu_arch.name: utils.make_schema_type(str),
    Key.cpu_tune.name: utils.make_schema_type(str),
    Key.vector_settings.name: utils.make_schema_type([str])
}

_CUDA_CAPABILITIES_SCHEMA ={
    Key.sm_levels.name: utils.make_schema_type([int]),
    Key.compute_levels.name: utils.make_schema_type([int])
}

_HW_CAP_CONFIG_SCHEMA = {
    Key.builder_version.name: utils.make_schema_type(str),
    Key.cpu_capabilities.name: utils.make_schema_type(_CPU_CAPABILITIES_SCHEMA),
    Key.cuda_capabilities.name: utils.make_schema_type(_CUDA_CAPABILITIES_SCHEMA)
}

def _validate_hw_cap_config_file(hw_cap_config_file):
    '''Perform some validation on the environment file after loading it.'''
    # pylint: disable=import-outside-toplevel
    from open_ce import conda_utils

    try:
        # First, partially render yaml to validate builder version number.
        version_check_obj = conda_utils.render_yaml(hw_cap_config_file, permit_undefined_jinja=True)
        if Key.builder_version.name in version_check_obj.keys():
            if not conda_utils.version_matches_spec(version_check_obj.get(Key.builder_version.name)):
                raise OpenCEError(Error.SCHEMA_VERSION_MISMATCH,
                                  hw_cap_config_file,
                                  version_check_obj.get(Key.builder_version.name),
                                  open_ce_version)

        meta_obj = None
        try:
            meta_obj = conda_utils.render_yaml(hw_cap_config_file, schema=_HW_CAP_CONFIG_SCHEMA)
            #if not (Key.cpu_capabilites.name in meta_obj.keys() or Key.cuda_capabilities.name in meta_obj.keys()):
            #    log.info("validate4")
            #    raise OpenCEError(Error.CONFIG_CONTENT)
            meta_obj[Key.hw_cap_config_file_path.name] = hw_cap_config_file
        except OpenCEError as exc:
            if Key.builder_version.name not in version_check_obj.keys():
                show_warning(Error.SCHEMA_VERSION_NOT_FOUND, hw_cap_config_file, Key.builder_version.name)
            raise exc
        return meta_obj
    except (Exception, SystemExit) as exc: #pylint: disable=broad-except
        raise OpenCEError(Error.ERROR, "Error in {}:\n  {}".format(hw_cap_config_file, str(exc))) from exc

def load_hw_cap_config_file(config_file):
    '''
    Load the hw capabilities config file
    '''
    hw_cap_config_file = os.path.abspath(config_file)

    # Load the hw cap config file using conda-build's API. This will allow for the
    # filtering of text using selectors and jinja2 functions
    
    return _validate_hw_cap_config_file(hw_cap_config_file)