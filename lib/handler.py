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

import json
import html
from logging import StreamHandler


class WSHandler(StreamHandler):

    def __init__(self, ws_client=None, target_data=None):
        StreamHandler.__init__(self)
        self.ws_client = ws_client
        self.target_data = target_data
        self.task = None

    def emit(self, message):
        _msg = html.escape(message.msg)
        msg = {'action': 'update_session_output', 'task': self.task, 'uuid': self.target_data['uuid'],
               'msg': _msg + '\n'}
        self.ws_client.send(json.dumps(msg))
