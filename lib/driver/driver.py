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

import abc


class Base(object):

    def __init__(self):
        self.status = None

    @abc.abstractmethod
    def authenticate(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def deploy(self):
        raise NotImplementedError()

    '''
    @abc.abstractmethod
    def load_use_cases(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def add_use_case(self, data=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def del_use_case(self, data=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def update_use_case(self, data=None):
        raise NotImplementedError()
    '''

    @abc.abstractmethod
    def get_status_update(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def load_settings(self):
        raise NotImplementedError()
