#!/usr/bin/env python
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
"""Performs worker liveness check.

The check logic concludes that a worker is in bad state if:
  - number of queued tasks > 0 (tasks waiting to be processed).
  - number of running tasks in this worker == 0 (worker doesn't take task).
  - number of recently completed task is 0.
"""

import checker_lib


def main():
  task_counts = checker_lib.task_count_by_state()
  if checker_lib.declare_error_state(task_counts):
    raise Exception('Worker {} seems to be dead. Task counts details:{}'.format(
        checker_lib.host_name, task_counts))
  print('Worker {} is alive with task count details{}'.format(
      checker_lib.host_name, task_counts))


if __name__ == '__main__':
  main()
