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

try:
    import yaml
except ImportError:
    print("Cannot find `pyyaml`, please see https://github.com/open-ce/open-ce-builder#requirements"
              " for a list of requirements.")
    sys.exit(1)

try:
    safe_loader = yaml.CSafeLoader
    safe_dumper = yaml.CSafeDumper
except:
    safe_loader = yaml.SafeLoader
    safe_dumper = yaml.SafeDumper

def load(stream):
    return yaml.load(stream, Loader=safe_loader)

def dump(data, stream=None):
    return yaml.dump(data, stream, Dumper=safe_dumper)
