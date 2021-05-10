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
from collections import Counter
import networkx

test_dir = pathlib.Path(__file__).parent.absolute()

import open_ce.build_tree as build_tree
import open_ce.conda_env_file_generator as conda_env_file_generator
import open_ce.utils as utils

external_deps = ["external_pac1    1.2", "external_pack2", "external_pack3=1.2.3"]

def sample_build_commands() :
    retval = networkx.DiGraph()
    node1 = build_tree.DependencyNode(packages=["package1a", "package1b"], build_command=build_tree.BuildCommand("recipe1",
                                                                                                    "repo1",
                                                                                                    ["package1a", "package1b"],
                                                                                                    python="3.6",
                                                                                                    build_type="cuda",
                                                                                                    mpi_type="openmpi",
                                                                                                    cudatoolkit="10.2",
                                                                                                    output_files=["package1a-1.0-py36_cuda10.2.tar.bz2", "package1b-1.0-py36_cuda10.2.tar.bz2"],
                                                                                                    run_dependencies=["python     >=3.6", "pack1    1.0", "pack2   >=2.0", "pack3 9b"]))
    node2 = build_tree.DependencyNode(packages=["package2a"], build_command=build_tree.BuildCommand("recipe2",
                                                                                                    "repo2",
                                                                                                    ["package2a"],
                                                                                                    python="3.6",
                                                                                                    build_type="cpu",
                                                                                                    mpi_type="system",
                                                                                                    cudatoolkit="10.2",
                                                                                                    output_files=["package2a-1.0-py36_cuda10.2.tar.bz2"],
                                                                                                    run_dependencies=["python ==3.6", "pack1 >=1.0", "pack2   ==2.0", "pack3 3.3 build"]))
    node3 = build_tree.DependencyNode(packages=["package3a", "package3b"], build_command=build_tree.BuildCommand("recipe3",
                                                                                                    "repo3",
                                                                                                    ["package3a", "package3b"],
                                                                                                    python="3.7",
                                                                                                    build_type="cpu",
                                                                                                    mpi_type="openmpi",
                                                                                                    cudatoolkit="10.2",
                                                                                                    output_files=["package3a-1.0-py37_cuda10.2.tar.bz2", "package3b-1.0-py37_cuda10.2.tar.bz2"],
                                                                                                    run_dependencies=["python 3.7", "pack1==1.0", "pack2 <=2.0", "pack3   3.0.*",
                                                                                                                    "pack4=1.15.0=py38h6ffa863_0"]))
    node4 = build_tree.DependencyNode(packages=["package4a", "package4b"], build_command=build_tree.BuildCommand("recipe4",
                                                                                                    "repo4",
                                                                                                    ["package4a", "package4b"],
                                                                                                    python="3.7",
                                                                                                    build_type="cuda",
                                                                                                    mpi_type="system",
                                                                                                    cudatoolkit="10.2",
                                                                                                    output_files=["package4a-1.0-py37_cuda.tar.bz2", "package4b-1.0-py37_cuda.tar.bz2"],
                                                                                                    run_dependencies=["pack1==1.0", "pack2 <=2.0", "pack3-suffix 3.0"]))

    retval.add_node(node1)
    retval.add_node(node2)
    retval.add_node(node3)
    retval.add_node(node4)

    for dep in external_deps:
        retval.add_node(build_tree.DependencyNode({dep}))

    return retval

def test_conda_env_file_content():
    '''
    Tests that the conda env file content are being populated correctly
    '''
    mock_conda_env_file_generator = build_tree.get_conda_file_packages(sample_build_commands(), external_deps, starting_nodes=[list(sample_build_commands().nodes)[0]])
    expected_deps = set(["python >=3.6", "pack1 1.0.*", "pack2 >=2.0", "package1a 1.0.* py36_cuda10.2", "package1b 1.0.* py36_cuda10.2",
                         "pack3 9b", "external_pac1 1.2.*", "external_pack2", "external_pack3=1.2.3"])
    assert Counter(expected_deps) == Counter(mock_conda_env_file_generator._dependency_set)

    mock_conda_env_file_generator = build_tree.get_conda_file_packages(sample_build_commands(), [], starting_nodes=[list(sample_build_commands().nodes)[1]])
    expected_deps = set(["python ==3.6.*", "pack1 >=1.0", "pack2 ==2.0.*", "package2a 1.0.* py36_cuda10.2", "pack3 3.3.* build"])
    assert Counter(expected_deps) == Counter(mock_conda_env_file_generator._dependency_set)

    mock_conda_env_file_generator = build_tree.get_conda_file_packages(sample_build_commands(), external_deps, starting_nodes=[list(sample_build_commands().nodes)[2]])
    expected_deps = set(["python 3.7.*", "pack1==1.0.*", "pack2 <=2.0", "pack3 3.0.*", "package3a 1.0.* py37_cuda10.2", "package3b 1.0.* py37_cuda10.2",
                     "pack4=1.15.0=py38h6ffa863_0", "external_pac1 1.2.*", "external_pack2", "external_pack3=1.2.3"])
    assert Counter(expected_deps) == Counter(mock_conda_env_file_generator._dependency_set)

    mock_conda_env_file_generator = build_tree.get_conda_file_packages(sample_build_commands(), [], starting_nodes=[list(sample_build_commands().nodes)[3]])
    expected_deps = set(["pack1==1.0.*", "pack2 <=2.0", "pack3-suffix 3.0.*", "package4a 1.0.* py37_cuda", "package4b 1.0.* py37_cuda"])
    assert Counter(expected_deps) == Counter(mock_conda_env_file_generator._dependency_set)

def test_create_channels():
    output_dir = os.path.join(test_dir, '../condabuild' )
    expected_channels = ["file:/{}".format(output_dir), "some channel", "defaults"]

    assert expected_channels == conda_env_file_generator._create_channels(["some channel"], output_dir)

def test_get_variant_string(mocker):
    var_str = "py3.6-cuda-openmpi-10.2"
    test_env_file = "#" + utils.OPEN_CE_VARIANT + ":" + var_str + "\nsomething else"
    mocker.patch('builtins.open', mocker.mock_open(read_data=test_env_file))

    assert conda_env_file_generator.get_variant_string("some_file.yaml") == var_str

def test_get_variant_string_no_string(mocker):
    test_env_file = "some string without\n a variant string"
    mocker.patch('builtins.open', mocker.mock_open(read_data=test_env_file))

    assert conda_env_file_generator.get_variant_string("some_file.yaml") is None
