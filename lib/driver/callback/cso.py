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

import socket
import json

try:
    from __main__ import cli
except ImportError:
    cli = None
from ansible.plugins.callback import CallbackBase
from ws4py.client.threadedclient import WebSocketClient

DOCUMENTATION = """
    callback: cso
    callback_type: notification
    short_description: send ansible events via ws to CSO Runner UI.
    author: "cklewar"
    description:
      - This callback will report start, failed and stats events to CSO Runner UI
    version_added: "2.7"
    requirements:
      - whitelisting in configuration
    options:
      cso_ws_url:
        description: WS Server URL
        required: True
        env:
          - name: CSO_WS_URL
        ini:
          - section: callback_cso
            key: ws_url
"""


class CallbackModule(CallbackBase):

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'default'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self, display=None):
        super(CallbackModule, self).__init__(display=display)
        self._options = cli.options
        self.ws_client = None
        self.ws_url = None

    def set_options(self, task_keys=None, var_options=None, direct=None):
        super(CallbackModule, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)
        self.ws_url = self.get_option('cso_ws_url')

        if self.ws_url is None:
            self.disabled = True
            self._display.warning('CSO-UI Runner Websocket URL was not provided. The '
                                  'Websocket URL can be provided using '
                                  'the `CSO_WS_URL` environment '
                                  'variable.')
        else:
            url = '{0}?clientname=server'.format(self.ws_url)
            self.ws_client = WSClient(name='server', url=url)

            try:
                self.ws_client.connect()
            except socket.error as se:
                print(se.filename, se.strerror, se.args, se.errno)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        print('v2_runner_on_failed: {0}'.format(result.task_name))
        data = result._task.serialize()
        message = {'action': 'v2_runner_on_failed', 'host': result._host.get_name(), 'task': result.task_name.strip(),
                   'status': 'FAILED', 'uuid': data['uuid']}
        self.emit_message(message=message)

    def v2_runner_on_ok(self, result):
        print('v2_runner_on_ok: {0}'.format(result.task_name))
        data = result._task.serialize()
        message = {'action': 'v2_runner_on_ok', 'host': result._host.get_name(), 'task': result.task_name.strip(),
                   'status': 'OK', 'uuid': data['uuid']}
        self.emit_message(message=message)

    def v2_runner_on_skipped(self, result):
        print('v2_runner_on_skipped')

    def v2_runner_on_unreachable(self, result):
        print('v2_runner_on_unreachable')

    def v2_playbook_on_no_hosts_matched(self):
        print('v2_playbook_on_no_hosts_matched')

    def v2_playbook_on_no_hosts_remaining(self):
        print('v2_playbook_on_no_hosts_remaining')

    def v2_playbook_on_task_start(self, task, is_conditional):
        print('v2_playbook_on_task_start: {0}'.format(task.get_name().strip()))
        data = task.serialize()
        message = {'action': 'v2_playbook_on_task_start', 'host': 'None', 'task': data['name'], 'status': 'running',
                   'uuid': data['uuid']}
        self.emit_message(message=message)

    def v2_playbook_on_cleanup_task_start(self, task):
        print('v2_playbook_on_cleanup_task_start')

    def v2_playbook_on_handler_task_start(self, task):
        print('v2_playbook_on_handler_task_start')

    def v2_playbook_on_play_start(self, play):
        print('v2_playbook_on_play_start: {0}'.format(play.get_name().strip()))
        data = play.serialize()
        extra_vars = self._options.extra_vars

        with open(extra_vars[0].split(':')[1], 'w') as fp:
            fp.write(data['uuid'])

        message = {'action': 'v2_playbook_on_play_start', 'host': data['hosts'], 'task': play.get_name().strip(),
                   'status': 'running', 'uuid': data['uuid']}
        self.emit_message(message=message)

    def v2_on_file_diff(self, result):
        print('v2_on_file_diff: {0}'.format(result.task_name))

    def v2_runner_item_on_ok(self, result):
        print('v2_runner_item_on_ok: {0}'.format(result.task_name().strip()))
        self.emit_message(message='v2_runner_item_on_ok: {0}'.format(result.task_name.strip()))

    def v2_runner_item_on_failed(self, result):
        print('v2_runner_item_on_failed')
        pass

    def v2_runner_item_on_skipped(self, result):
        print('v2_runner_item_on_skipped')
        pass

    def v2_playbook_on_include(self, included_file):
        print('v2_playbook_on_include')
        pass

    def v2_playbook_on_stats(self, stats):
        print('v2_playbook_on_stats')
        pass

    def v2_playbook_on_start(self, playbook):
        print('v2_playbook_on_start')
        pass

    def v2_runner_retry(self, result):
        print('v2_runner_retry')
        pass

    def v2_playbook_on_notify(self, handler, host):
        print('v2_playbook_on_notify')
        pass

    def emit_message(self, message=None):

        if message is not None:
            self.ws_client.send(json.dumps(message))
            #self.ws_client.close()
        else:
            print('empty message')


class WSClient(WebSocketClient):
    def __init__(self, name=None, url=None):

        super(WSClient, self).__init__(url=url, protocols=['http-only', 'chat'])
        self._clientName = name

    def opened(self):
        print('opened connection')

    def closed(self, code, reason=None):
        if code != 1000:
            print('WSClient: Connection closed. Code <{0}>, Reason: <{1}>'.format(code, reason))

    def received_message(self, m):
        print('WSClient: Client received data. That\'s not what we want at this stage')
