"""
# *****************************************************************
# (C) Copyright IBM Corp. 2020, 2022. All Rights Reserved.
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
import subprocess
import errno
from itertools import product
import re
import urllib.request
import tempfile
import multiprocessing as mp
from distutils.version import LooseVersion
import pkg_resources
from open_ce.errors import OpenCEError, Error, show_warning, log
from open_ce import constants

def make_variants(python_versions=constants.DEFAULT_PYTHON_VERS,
                  build_types=constants.DEFAULT_BUILD_TYPES,
                  mpi_types=constants.DEFAULT_MPI_TYPES,
                  cuda_versions=constants.DEFAULT_CUDA_VERS):
    '''Create a cross product of possible variant combinations.'''
    results = []
    for build_type in parse_arg_list(build_types):
        variants = { 'python' : parse_arg_list(python_versions),
                     'build_type' : [build_type],
                     'mpi_type' :  parse_arg_list(mpi_types)}
        if build_type == "cuda":
            variants["cudatoolkit"] = parse_arg_list(cuda_versions)
        results += [dict(zip(variants,y)) for y in product(*variants.values())]

    return results

def ALL_VARIANTS():
    '''Returns a list of all possible variant combinations.'''
    return make_variants(constants.SUPPORTED_PYTHON_VERS,
                         constants.SUPPORTED_BUILD_TYPES,
                         constants.SUPPORTED_MPI_TYPES,
                         constants.SUPPORTED_CUDA_VERS)

def remove_version(package):
    '''Remove conda version from dependency.'''
    return package.split()[0].split("=")[0]

def check_if_package_exists(package):
    '''Checks if a package is installed'''
    try:
        pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound as exc:
        raise OpenCEError(Error.PACKAGE_NOT_FOUND, package) from exc

def make_schema_type(data_type,required=False):
    '''Make a schema type tuple.'''
    return (data_type, required)

def validate_type(value, schema_type):
    '''Validate a single type instance against a schema type.'''
    if isinstance(schema_type, dict):
        validate_dict_schema(value, schema_type)
    else:
        if not isinstance(value, schema_type):
            raise OpenCEError(Error.ERROR, f"{value} is not of expected type {schema_type}")

def validate_dict_schema(dictionary, schema):
    '''Recursively validate a dictionary's schema.'''
    for k, (schema_type, required) in schema.items():
        if k not in dictionary:
            if required:
                raise OpenCEError(Error.ERROR, f"Required key {k} was not found in {dictionary}")
            continue
        if isinstance(schema_type, list):
            if dictionary[k] is not None: #Handle if the yaml file has an empty list for this key.
                validate_type(dictionary[k], list)
                for value in dictionary[k]:
                    validate_type(value, schema_type[0])
        else:
            validate_type(dictionary[k], schema_type)
    for k in dictionary:
        if not k in schema:
            raise OpenCEError(Error.ERROR, f"Unexpected key {k} was found in {dictionary}")

def run_command_capture(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None):
    """Run a shell command and capture the ret_code, stdout and stderr."""
    if cwd:
        os.makedirs(cwd, exist_ok=True)
    with subprocess.Popen(
        cmd,
        stdout=stdout,
        stderr=stderr,
        shell=True,
        universal_newlines=True,
        cwd=cwd) as process:
        std_out, std_err = process.communicate()

        return process.returncode == 0, std_out, std_err

    return False, std_out, std_err

def run_and_log(command):
    '''Print a shell command and then execute it.'''
    log.info("--->%s", command)
    return os.system(command)

def get_output(command):
    '''Print and execute a shell command and then return the output.'''
    log.info("--->%s", command)
    _,std_out,_ = run_command_capture(command, stderr=subprocess.STDOUT)
    return std_out.strip()

def variant_string(py_ver, build_type, mpi_type, cudatoolkit):
    '''
    Returns a variant key using python version and build type
    '''
    result = ""
    if py_ver:
        result +=  "py" + py_ver
    if build_type:
        result +=  "-" + build_type
    if mpi_type:
        result +=  "-" + mpi_type
    if cudatoolkit:
        result += "-" + cudatoolkit
    return result

def variant_string_to_dict(var_string):
    """
    Returns a dictionary of variants based on the versions within the variant string.
    """
    variants = var_string.split("-")
    variant_dict = { 'python' : variants[0][2:],
                     'build_type' : variants[1],
                     'mpi_type' : variants[2] }
    if variant_dict["build_type"] == "cuda":
        variant_dict["cudatoolkit"] = variants[3]

    return variant_dict

def generalize_version(package):
    """Add `.*` to package versions when it is needed."""

    # Remove multiple spaces or tabs
    package = re.sub(r'\s+', ' ', package)

    # Check if we want to add .* to the end of versions
    py_matched = re.match(r'([\w-]+)([\s=<>]*)(\d[.\d*\w*]*)([=\s]*.*)', package)

    if py_matched:
        name = py_matched.group(1)
        operator = py_matched.group(2)
        version = py_matched.group(3)
        build = py_matched.group(4)
        if len(version) > 0 and len(operator) > 0:

            #Append .* at the end if it is not there and if operator is space or == or empty
            if not version.endswith(".*") and version[-1].isdigit() and operator.strip() in ["==", " ", ""]:
                package = name + operator + version + ".*" + build

    return package

def cuda_level_supported(cuda_level):
    '''
    Check if the requested cuda level is supported by loaded NVIDIA driver
    '''

    return float(get_driver_cuda_level()) >= float(cuda_level)

def get_driver_cuda_level():
    '''
    Return what level of Cuda the driver can support
    '''
    try:
        smi_out = subprocess.check_output("nvidia-smi").decode("utf-8").strip()
        return re.search(r"CUDA Version\: (\d+\.\d+)", smi_out).group(1)
    except OSError as err:
        if err.errno == errno.ENOENT:
            raise OpenCEError(Error.ERROR, "nvidia-smi command not found") from err

        raise OpenCEError(Error.ERROR, "nvidia-smi command unexpectedly failed") from err

def get_driver_level():
    '''
    Return the NVIDIA driver level on the system.
    '''
    try:
        smi_out = subprocess.check_output("nvidia-smi").decode("utf-8").strip()
        return re.search(r"Driver Version\: (\d+\.\d+\.\d+)", smi_out).group(1)
    except OSError as err:
        if err.errno == errno.ENOENT:
            raise OpenCEError(Error.ERROR, "nvidia-smi command not found") from err

        raise OpenCEError(Error.ERROR, "nvidia-smi command unexpectedly failed") from err

def cuda_driver_installed():
    '''
    Determine if the current machine has the NVIDIA driver installed
    '''

    try:
        lsmod_out = subprocess.check_output("lsmod").decode("utf-8").strip()
        return re.search(r"nvidia ", lsmod_out) is not None
    except OSError as err:
        if err.errno == errno.ENOENT:
            raise OpenCEError(Error.ERROR, "lsmod command not found") from err

        raise OpenCEError(Error.ERROR, "lsmod command unexpectedly failed") from err

def is_subdir(child_path, parent_path):
    """ Checks if given child path is sub-directory of parent_path. """

    child = os.path.realpath(child_path)
    parent = os.path.realpath(parent_path)

    relative = os.path.relpath(child, start=parent)
    return not relative.startswith(os.pardir)

def is_url(to_check):
    '''
    Determines if a string is a URL
    '''
    return to_check.startswith("http:") or to_check.startswith("https:")

def download_file(url, filename=None):
    '''
    Downloads a file from a url string.
    Raises an OpenCE Error if an exception is encountered.
    '''
    retval = None
    try:
        suffix = filename
        if not suffix:
            suffix = os.path.basename(url)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as download_path:
            retval, _ = urllib.request.urlretrieve(url, filename=download_path.name)
    except Exception as exc: # pylint: disable=broad-except
        raise OpenCEError(Error.FILE_DOWNLOAD, url, str(exc)) from exc
    return retval

def replace_conda_env_channels(conda_env_file, original_channel, new_channel):
    '''
    Use regex to substitute channels in a conda env file.
    Regex 'original_channel' is replaced with 'new_channel'
    '''
    #pylint: disable=import-outside-toplevel
    import open_ce.yaml_utils     #pylint: disable=cyclic-import

    with open(conda_env_file, 'r', encoding='utf8') as file_handle:
        env_info = open_ce.yaml_utils.load(file_handle)

    env_info['channels'] = [re.sub(original_channel, new_channel, channel) for channel in env_info['channels']]

    with open(conda_env_file, 'w', encoding='utf8') as file_handle:
        open_ce.yaml_utils.dump(env_info, file_handle)

def get_branch_of_tag(git_tag):
    """
    Find the most recent branch that contains git_tag.
    """
    branch_command = "git branch -a --contains " + git_tag
    ret_code, output, _ = run_command_capture(branch_command)
    if not ret_code or not output:
        return git_tag
    possible_branches = output.splitlines()

    # Clean branches and sort so that highest release version number is last
    possible_branches = [possible_branch.replace('*','').strip() for possible_branch in possible_branches]
    possible_branches = list(filter(lambda x: x == "remotes/origin/main" or x == "remotes/origin/master" or
                               x.startswith("remotes/origin/r"), sorted(possible_branches, key=LooseVersion)))

    return possible_branches[1] if len(possible_branches) > 1 else possible_branches[0]

def git_clone(git_url, git_tag, location, up_to_date=False):
    '''
    Clone a git repository and checkout a certain branch.
    '''
    clone_cmd = "git clone " + git_url + " " + location
    log.info("Clone cmd: %s", clone_cmd)
    clone_result = os.system(clone_cmd)

    cur_dir = os.getcwd()
    clone_successful = clone_result == 0
    if clone_successful:
        if git_tag:
            os.chdir(location)
            if up_to_date:
                git_tag = get_branch_of_tag(git_tag)
            checkout_cmd = "git checkout " + git_tag
            log.info("Checkout branch/tag command: %s", checkout_cmd)
            checkout_res = os.system(checkout_cmd)
            os.chdir(cur_dir)
            clone_successful = checkout_res == 0
    else:
        raise OpenCEError(Error.CLONE_REPO, git_url)

    return clone_successful

def get_container_tool_ver(tool):
    '''
    Returns the version of the tool
    '''
    cmd = tool + " version"
    output = get_output(cmd)
    version = None
    for line in output.split("\n"):
        matched = re.match(r'(\s*Version:\s* (.*))', line)
        if matched:
            version = matched.group(2)
            version = version.strip()
            break

    return version

def get_open_ce_version(conda_env_file):
    '''
    Parses conda environment files to retrieve Open-CE version
    '''
    conda_file = None
    version = "open-ce"
    try:
        with open(conda_env_file, 'r', encoding='utf8') as conda_file:
            lines = conda_file.readlines()
            for line in lines:
                matched = re.match(r'(#'+constants.OPEN_CE_VERSION_STRING+':(.*))', line)
                if matched:
                    version = matched.group(2)
                    break

    except IOError:
        show_warning(Error.CONDA_IO_ERROR, conda_env_file)
    finally:
        if conda_file:
            conda_file.close()
    return version

def _run_helper(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except SystemExit as err:
        raise OpenCEError(Error.ERROR, str(err)) from err

def run_in_parallel(function, arguments):
    '''
    Run function in parallel across all arguments.
    '''
    new_args = [tuple([function]) + x if isinstance(x, tuple) else (function, x) for x in arguments]
    with mp.Pool(constants.NUM_THREAD_POOL) as pool:
        try:
            retval = pool.starmap(_run_helper, new_args)
            return retval
        finally:
            pool.close()
            pool.join()

def get_conda_build_configs(configs):
    '''
    Get a list of all of the conda_build_config file paths.
    If a path is a URL it will be downloaded.
    If a path doesn't exist, it won't be added.
    '''
    result = []
    for config in configs:
        if is_url(config):
            result.append(download_file(config, filename=constants.CONDA_BUILD_CONFIG_FILE))
        elif os.path.exists(config):
            result.append(os.path.abspath(config))

    return result

def check_conda_build_configs_exist(conda_build_configs):
    '''
    Verify that all non-url conda_build_config files exist locally.
    '''
    for conda_build_config in conda_build_configs:
        if not is_url(conda_build_config) and not os.path.exists(conda_build_config):
            raise OpenCEError(Error.CONDA_BUILD_CONFIG_FILE_NOT_FOUND, conda_build_config)

def expanded_path(path, relative_to=None):
    '''
    Expand a path relative to another file.
    '''
    result = os.path.expanduser(path)
    if not os.path.isabs(result) and relative_to:
        result = os.path.join(os.path.dirname(relative_to), result)

    return result

def parse_arg_list(arg_list):
    ''' Turn a comma delimited string into a python list'''
    if isinstance(arg_list, list):
        return arg_list
    return arg_list.split(",") if not arg_list is None else []
