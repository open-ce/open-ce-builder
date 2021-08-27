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
import traceback

from open_ce import utils
from open_ce import inputs
from open_ce.inputs import Argument
from open_ce.errors import OpenCEError, Error, log

COMMAND = 'feedstock'

DESCRIPTION = 'Build conda packages as part of Open-CE'

ARGUMENTS = inputs.PRIMARY_BUILD_ARGS + \
            [Argument.RECIPE_CONFIG_FILE,
             Argument.RECIPES,
             Argument.WORKING_DIRECTORY,
             Argument.LOCAL_SRC_DIR,
             Argument.CONDA_PKG_FORMAT,
             Argument.DEBUG,
             Argument.DEBUG_OUTPUT_ID]

def get_conda_build_config():
    '''
    Checks for a conda_build_config file inside config dir of the feedstock.
    And returns the same if it exists.
    '''
    recipe_conda_build_config = os.path.join(os.getcwd(), "config", "conda_build_config.yaml")
    return recipe_conda_build_config if os.path.exists(recipe_conda_build_config) else None

def load_package_config(config_file=None, variants=None, recipe_path=None):
    '''
    Check for a config file. If the user does not provide a recipe config
    file as an argument, it will be assumed that there is only one
    recipe to build, and it is in the directory called 'recipe'.
    '''
    # pylint: disable=import-outside-toplevel
    from open_ce import conda_utils

    if recipe_path:
        recipe_name = os.path.basename(os.getcwd())
        build_config_data = {'recipes':[{'name':recipe_name, 'path':recipe_path}]}
    elif not config_file and not os.path.exists(utils.DEFAULT_RECIPE_CONFIG_FILE):
        recipe_name = os.path.basename(os.getcwd())
        build_config_data = {'recipes':[{'name':recipe_name, 'path':'recipe'}]}
    else:
        if not config_file:
            config_file = utils.DEFAULT_RECIPE_CONFIG_FILE
        if not os.path.exists(config_file):
            raise OpenCEError(Error.CONFIG_FILE, config_file)

        build_config_data = conda_utils.render_yaml(config_file, variants)

    return build_config_data, config_file

def _set_local_src_dir(local_src_dir_arg, recipe, recipe_config_file):
    """
    Set the LOCAL_SRC_DIR environment variable if local_src_dir is specified.
    """
    # Local source directory provided as command line argument has higher priority
    # than what is specified in build-config.yaml
    if local_src_dir_arg:
        local_src_dir = os.path.expanduser(local_src_dir_arg)
    elif 'local_src_dir' in recipe:
        local_src_dir = os.path.expanduser(recipe.get('local_src_dir'))
        # If a relative path is specified, it should be in relation to the config file
        if not os.path.isabs(local_src_dir):
            local_src_dir = os.path.join(os.path.dirname(os.path.abspath(recipe_config_file)),
                                         local_src_dir)
    else:
        local_src_dir = None

    if local_src_dir:
        if not os.path.exists(local_src_dir):
            raise OpenCEError(Error.LOCAL_SRC_DIR, local_src_dir)
        os.environ["LOCAL_SRC_DIR"] = local_src_dir
    else:
        if 'LOCAL_SRC_DIR' in os.environ:
            del os.environ['LOCAL_SRC_DIR']

def build_feedstock_from_command(command, # pylint: disable=too-many-arguments, too-many-locals
                                 recipe_config_file=None,
                                 output_folder=utils.DEFAULT_OUTPUT_FOLDER,
                                 local_src_dir=None,
                                 pkg_format=utils.DEFAULT_PKG_FORMAT,
                                 debug=None,
                                 debug_output_id=None):
    '''
    Build a feedstock from a build_command object.
    '''
    utils.check_if_package_exists('conda-build')

    # pylint: disable=import-outside-toplevel
    import conda_build.api
    from conda_build.config import get_or_merge_config

    saved_working_directory = None
    if command.repository:
        saved_working_directory = os.getcwd()
        os.chdir(os.path.abspath(command.repository))

    recipes_to_build = inputs.parse_arg_list(command.recipe)

    for variant in utils.make_variants(command.python, command.build_type, command.mpi_type, command.cudatoolkit):
        build_config_data, recipe_config_file  = load_package_config(recipe_config_file, variant, command.recipe_path)

        # Build each recipe
        if build_config_data['recipes'] is None:
            build_config_data['recipes'] = []
            log.info("No recipe to build for given configuration.")
        for recipe in build_config_data['recipes']:
            if recipes_to_build and recipe['name'] not in recipes_to_build:
                continue

            config = get_or_merge_config(None, variant=variant)
            config.skip_existing = False
            config.prefix_length = 225
            config.output_folder = output_folder
            conda_build_configs = [utils.download_file(conda_build_config) if utils.is_url(conda_build_config)
                                       else conda_build_config
                                           for conda_build_config in command.conda_build_configs]
            config.variant_config_files = [config for config in conda_build_configs if os.path.exists(config)]

            if pkg_format == "conda":
                config.conda_pkg_format = "2"     # set to .conda format

            recipe_conda_build_config = get_conda_build_config()
            if recipe_conda_build_config:
                config.variant_config_files.append(recipe_conda_build_config)

            config.channel_urls = [os.path.abspath(output_folder)]
            config.channel_urls += command.channels
            config.channel_urls += build_config_data.get('channels', [])

            _set_local_src_dir(local_src_dir, recipe, recipe_config_file)
            try:
                if debug:
                    activation_string=conda_build.api.debug(os.path.join(os.getcwd(),recipe['path'])
                                                             ,output_id=debug_output_id,config=config)
                    if activation_string:
                        log.info("#" * 80)
                        log.info(
                                 "Build and/or host environments created for debug output id %s."
                                 "To enter a debugging environment:\n",debug_output_id
                                )
                        log.info(activation_string)
                        log.info("#" * 80)
                else:
                    conda_build.api.build(os.path.join(os.getcwd(), recipe['path']),
                               config=config)
            except Exception as exc: # pylint: disable=broad-except
                traceback.print_exc()
                raise OpenCEError(Error.BUILD_RECIPE,
                                  recipe['name'] if 'name' in recipe else os.getcwd,
                                  str(exc)) from exc

    if saved_working_directory:
        os.chdir(saved_working_directory)

def build_feedstock(args):
    '''Entry Function'''
    # Here, importing BuildCommand is intentionally done here to avoid circular import.

    from open_ce.build_tree import BuildCommand   # pylint: disable=import-outside-toplevel
    command = BuildCommand(recipe=inputs.parse_arg_list(args.recipe_list),
                           repository=args.working_directory,
                           packages=[],
                           python=args.python_versions,
                           build_type=args.build_types,
                           mpi_type=args.mpi_types,
                           cudatoolkit=args.cuda_versions,
                           channels=args.channels_list,
                           conda_build_configs=args.conda_build_configs)

    build_feedstock_from_command(command,
                                 recipe_config_file=args.recipe_config_file,
                                 output_folder=args.output_folder,
                                 local_src_dir=args.local_src_dir,
                                 pkg_format=args.conda_pkg_format,
                                 debug=args.debug,
                                 debug_output_id=args.debug_output_id)

ENTRY_FUNCTION = build_feedstock
