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
import json
from threading import Thread

import lib.constants as c


class Base(Thread):

    def __init__(self, target_data=None, use_case_name=None, use_case_data=None, ws_client=None,
                 ws_handler=None, group=None, target=None, name=None, *, daemon=None, event=None,
                 queue=None):
        super(Base, self).__init__(group=group, target=target, name=name, daemon=daemon)
        self.load_settings()
        self.use_case_name = use_case_name
        self.use_case_data = use_case_data
        self.target = target_data
        self.tmp_dir = c.CONFIG['tmp_dir']
        self.globals_file = c.CONFIG['globals']
        self._dev = None
        self.mode = None
        self.address = None
        self.port = None
        self.user = None
        self.pw = None
        self.usecases_dir = c.CONFIG['usecases_dir']
        self.use_case_path = '{0}/{1}'.format(self.tmp_dir, use_case_data['directory'])
        self.ws_client = ws_client
        self.ws_handler = ws_handler
        self.event = event
        self.daemon = daemon
        self.queue = queue

    @abc.abstractmethod
    def authenticate(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def load_settings(self):
        raise NotImplementedError()

    def emit_message(self, message=None):

        if message is not None:
            self.ws_client.send(json.dumps(message))
        else:
            print('empty message')
