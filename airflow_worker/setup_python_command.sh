#!/usr/bin/env bash
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Setup the python/pip command simlinks. No-op for Python2.

set -ex

if [ "${COMPOSER_PYTHON_VERSION}" == "3" ]; then
  # Ignore https://legacy.python.org/dev/peps/pep-0394/ and make python point to python3.
  DEFAULT_PYTHON_PATH=`which python`
  sudo rm ${DEFAULT_PYTHON_PATH}
  sudo ln -s `which python3` ${DEFAULT_PYTHON_PATH}
  # Similar for pip.
  DEFAULT_PIP_PATH=`which pip`
  sudo rm ${DEFAULT_PIP_PATH}
  sudo ln -s `which pip3` ${DEFAULT_PIP_PATH}
fi
