# *****************************************************************
# (C) Copyright IBM Corp. 2023. All Rights Reserved.
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

# This script can contain common functions needed by feedstocks during the builds.

function cleanup_bazel {
    bazel clean --expunge && bazel shutdown
    if [[ $? -eq 0 ]]; then
        echo "bazel shutdown completed successfully"
    else
        echo "bazel shutdown failed, now trying to kill bazel process ID: $1"
        kill -9 $1 && sleep 20 && echo "Killed bazel process successfully"
    fi
}
