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

import os
import pathlib
import tempfile
from importlib.util import spec_from_loader, module_from_spec
from importlib.machinery import SourceFileLoader

test_dir = pathlib.Path(__file__).parent.absolute()

spec = spec_from_loader("opence", SourceFileLoader("opence", os.path.join(test_dir, '..', 'open_ce', 'open-ce')))
opence = module_from_spec(spec)
spec.loader.exec_module(opence)

import open_ce.get_graph as get_graph
import open_ce.utils as utils

def test_get_graph(caplog):
    '''
    This is a complete test of `get_graph`.
    '''
    tmp_test = tempfile.TemporaryDirectory()
    output_folder = os.path.join(tmp_test.name, "output")
    opence._main(["get", get_graph.COMMAND, "xgboost-env.yaml",
                  "--output_folder", output_folder,
                  "--python_versions", "3.6,3.7",
                  "--build_types", "cuda,cpu",
                  "--repository_folder", os.path.join(tmp_test.name, "repos")])

    assert "Build graph successfully output" in caplog.text

    output_file = os.path.join(output_folder, utils.DEFAULT_GRAPH_FILE)
    assert os.path.exists(output_file)

    tmp_test.cleanup()
