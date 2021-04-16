"""
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
"""

import open_ce.utils

open_ce.utils.check_if_package_exists('pyyaml')

#pylint: disable=wrong-import-position
import yaml

# Determine if the yaml package contains the C loaders/dumpers. If so, use
# the C versions. Otherwise, use the python versions.
try:
    safe_loader = yaml.CSafeLoader
    safe_dumper = yaml.CSafeDumper
# pylint: disable=bare-except
except:
    safe_loader = yaml.SafeLoader
    safe_dumper = yaml.SafeDumper

def load(stream):
    """
    Use pyyaml's safe loader. If available, the C based version of the loader will be used.
    """
    return yaml.load(stream, Loader=safe_loader)

def dump(data, stream=None):
    """
    Use pyyaml's safe dumper. If available, the C based version of the dumper will be used.
    """
    return yaml.dump(data, stream, Dumper=safe_dumper)
