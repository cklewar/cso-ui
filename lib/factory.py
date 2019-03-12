#
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
#
# Copyright (c) 2019 Juniper Networks, Inc.
# All rights reserved.
#
# Use is subject to license terms.
#
# Licensed under the Apache License, Version 2.0 (the ?License?); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: cklewar
#

import lib.constants as c

from lib.driver._pyez import PyEzDriver
from lib.driver._ansible import AnsibleDriver
from lib.driver._saltstack import SaltDriver


class DriverFactory(object):

    def __init__(self, name=None):

        self.name = name
        self._driver = None

    def init_driver(self, target_data=None, use_case_name=None, use_case_data=None, results=None, ws_client=None):

        if self.name == c.DRIVER_SALTSTACK:
            self._driver = SaltDriver()
        elif self.name == c.DRIVER_ANSIBLE:
            self._driver = AnsibleDriver()
        elif self.name == c.DRIVER_PYEZ:
            self._driver = PyEzDriver(target_data=target_data, use_case_name=use_case_name, use_case_data=use_case_data,
                                      results=results, ws_client=ws_client)

        return self._driver
