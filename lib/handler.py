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
from logging import Handler


class WSStreamHandler(Handler):

    def __init__(self, ws_client=None, tq=None):
        Handler.__init__(self)
        self.ws_client = ws_client
        self.tq = tq
        print('TQ ID in WSStreamHandlerInit: {0}/{1}'.format(id(self.tq), len(self.tq)))

    def emit(self, record):
        print('TQ ID in EMIT: {0} --> {1} --> {2}'.format(id(self.tq), self.tq[record.threadName], self.tq[record.threadName].current_task))
        target = self.tq[record.threadName].target
        _msg = html.escape(record.msg)
        _msg = {'action': 'update_session_output', 'task': self.tq[record.threadName].current_task,
                'uuid': target['uuid'], 'target': target['name'], 'msg': _msg + '\n'}
        self.ws_client.send(json.dumps(_msg))
