#!/usr/bin/env python
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
import shutil
from open_ce import utils
from open_ce import __version__ as open_ce_version
from open_ce.inputs import Argument, parse_arg_list
from open_ce.errors import OpenCEError, Error, show_warning, log

COMMAND = 'image'
DESCRIPTION = 'Run Open-CE tools within a container'
ARGUMENTS = [Argument.LOCAL_CONDA_CHANNEL,
             Argument.CONDA_ENV_FILE,
             Argument.CONTAINER_BUILD_ARGS,
             Argument.CONTAINER_TOOL]

OPEN_CE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
RUNTIME_IMAGE_NAME = "opence-runtime"
RUNTIME_IMAGE_PATH = os.path.join(OPEN_CE_PATH, "images",
                                  RUNTIME_IMAGE_NAME)
REPO_NAME = "open-ce"
TEMP_FILES = "temp_dir"

OPENCE_USER = "opence"
LOCAL_CONDA_CHANNEL_IN_IMG = "opence-local-conda-channel"
TARGET_DIR = "/home/{}/{}".format(OPENCE_USER, LOCAL_CONDA_CHANNEL_IN_IMG)

def build_image(local_conda_channel, conda_env_file, container_tool, image_version, container_build_args=""):
    """
    Build a container image from the Dockerfile in RUNTIME_IMAGE_PATH.
    Returns a result code and the name of the new image.
    """
    variant = os.path.splitext(conda_env_file)[0].replace(utils.CONDA_ENV_FILENAME_PREFIX, "", 1)
    variant = variant.replace("-runtime", "")
    image_name = REPO_NAME + ":" + image_version + "-" + variant
    # Docker version on ppc64le rhel7 doesn't allow Dockerfiles to be out of build context.
    # Hence, copying it in temp_dir inside the build context. This isn't needed with newer
    # docker versions or podman but to be consistent, doing this in all cases.
    dockerfile_path = os.path.join(local_conda_channel, TEMP_FILES, "Dockerfile")
    runtime_img_file = _get_runtime_image_file(container_tool)
    create_copy(runtime_img_file, dockerfile_path)

    build_cmd = container_tool + " build "
    build_cmd += "-f " + dockerfile_path + " "
    build_cmd += "-t " + image_name + " "
    build_cmd += "--build-arg OPENCE_USER=" + OPENCE_USER + " "
    build_cmd += "--build-arg LOCAL_CONDA_CHANNEL=" + "./ "
    build_cmd += "--build-arg CONDA_ENV_FILE=" + os.path.join(TEMP_FILES, conda_env_file) + " "
    build_cmd += "--build-arg TARGET_DIR=" + TARGET_DIR + " "
    build_cmd += container_build_args + " "
    build_cmd += local_conda_channel

    log.info("Container build command: %s", build_cmd)
    if os.system(build_cmd):
        raise OpenCEError(Error.BUILD_IMAGE, image_name)

    return image_name

def _get_runtime_image_file(container_tool):
    tool_ver = utils.get_container_tool_ver(container_tool)
    image_file = os.path.join(RUNTIME_IMAGE_PATH, "docker/Dockerfile")
    if not tool_ver:
        show_warning(Error.CONTAINER_VERSION, container_tool)
        # If we couldn't get the version of the tool, should use the older docker
        # supported Dockerfile
        return image_file

    tool_ver = tool_ver.replace(".", "")
    if (container_tool == "docker" and int(tool_ver) >= 1709) or \
       (container_tool == "podman" and int(tool_ver) >= 200):
        # Use the newer docker/podman supported Dockerfile
        image_file = os.path.join(RUNTIME_IMAGE_PATH, "podman/Dockerfile")

    log.info("Dockerfile being used: %s", image_file)
    return image_file

def build_runtime_container_image(args):
    """
    Create a runtime image which will have a conda environment created
    using locally built conda packages and environment file.
    """

    if not args.container_tool:
        raise OpenCEError(Error.NO_CONTAINER_TOOL_FOUND)

    local_conda_channel = os.path.abspath(args.local_conda_channel)
    if not os.path.exists(local_conda_channel):
        raise OpenCEError(Error.INCORRECT_INPUT_PATHS)

    os.makedirs(os.path.join(local_conda_channel, TEMP_FILES), exist_ok=True)

    for conda_env_file in parse_arg_list(args.conda_env_files):
        conda_env_file = os.path.abspath(conda_env_file)
        if not os.path.exists(conda_env_file):
            raise OpenCEError(Error.INCORRECT_INPUT_PATHS)

        # Copy the conda environment file into the TEMP_FILES dir inside local
        # conda channel with a new name and modify it
        conda_env_runtime_filename = os.path.splitext(os.path.basename(conda_env_file))[0]+'-runtime.yaml'
        conda_env_runtime_file = os.path.join(local_conda_channel, TEMP_FILES, conda_env_runtime_filename)
        create_copy(conda_env_file, conda_env_runtime_file)
        utils.replace_conda_env_channels(conda_env_runtime_file, r'file:.*', "file:/{}".format(TARGET_DIR))

        image_version = utils.get_open_ce_version(conda_env_file)
        image_name = build_image(args.local_conda_channel, os.path.basename(conda_env_runtime_file),
                                 args.container_tool, image_version, args.container_build_args)
        log.info("Docker image with name %s is built successfully.", image_name)

    cleanup(local_conda_channel)

def create_copy(src_file, dest_file):
    '''
    Creates a copy of src_file to dest_file
    '''
    try:
        shutil.copy(src_file, dest_file)
    except shutil.SameFileError:
        log.info("File '%s' already in local conda channel.", src_file)

def cleanup(local_conda_channel):
    '''
    Removes TEMP_FILES directory from the specified directory
    '''
    try:
        shutil.rmtree(os.path.join(local_conda_channel, TEMP_FILES))
    except OSError:
        log.info("Error removing temporary files created during build image.") #TODO: Switch to an opence warning.


ENTRY_FUNCTION = build_runtime_container_image
