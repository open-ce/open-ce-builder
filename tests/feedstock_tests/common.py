#!/usr/bin/env python

# *****************************************************************
# (C) Copyright IBM Corp. 2021. All Rights Reserved.
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

import argparse
import sys
import os
import pathlib

import conda_build.api
from conda_build.config import get_or_merge_config

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
import open_ce.build_feedstock as build_feedstock  # pylint: disable=wrong-import-position
import open_ce.inputs as inputs # pylint: disable=wrong-import-position

def make_parser():
    ''' Parser for input arguments '''
    arguments = [inputs.Argument.PYTHON_VERSIONS, inputs.Argument.BUILD_TYPES, inputs.Argument.MPI_TYPES,
                 inputs.Argument.CUDA_VERSIONS, inputs.Argument.CONDA_BUILD_CONFIG]
    parser = argparse.ArgumentParser(arguments)
    for argument in arguments:
        argument(parser)
    return parser

def get_build_numbers(build_config_data, config, variant):
    build_numbers = dict()
    for recipe in build_config_data["recipes"]:
        metas = conda_build.api.render(recipe['path'],
                                    config=config,
                                    variants=variant,
                                    bypass_env_check=True,
                                    finalize=True)
        for meta,_,_ in metas:
            build_numbers[meta.meta['package']['name']] = {"version" : meta.meta['package']['version'],
                                                           "number" : meta.meta['build']['number']}
    return build_numbers

def get_configs(variant, conda_build_config=None):
    build_config_data, _ = build_feedstock.load_package_config(variants=variant)
    config = get_or_merge_config(None, variant=variant)
    config.variant_config_files = conda_build_config if conda_build_config else []
    config.verbose = False
    recipe_conda_build_config = build_feedstock.get_conda_build_config()
    if recipe_conda_build_config:
        config.variant_config_files.append(recipe_conda_build_config)
    return build_config_data, config

def check_recipes(build_config_data, config, variant):
    return all(conda_build.api.check(recipe['path'], config=config, variants=variant) for recipe in build_config_data["recipes"])
