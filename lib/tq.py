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
import logging
import queue as queue
import threading
from collections import OrderedDict
from threading import Thread, Event

from ruamel.yaml import YAML

import lib.constants as c
from lib.factory import DriverFactory
from lib.handler import WSStreamHandler
from lib.wsclient import WSClient


class TargetQueue(Thread):

    def __init__(self, _data=None, use_case_name=None, use_case_data=None, group=None, target=None, name=None, args=(),
                 kwargs=None, *, daemon=None):
        super(TargetQueue, self).__init__(group=group, target=target, name=name)
        self.__data = _data
        self.use_case_name = use_case_name
        self.use_case_data = use_case_data
        self.tq = OrderedDict()
        self.queue = queue.Queue()
        self.event = threading.Event()
        __cso_ws_url = '{0}://{1}:{2}/ws'.format(c.CONFIG['ws_client_protocol'], c.CONFIG['ws_client_ip'],
                                                 c.CONFIG['ws_client_port'])
        __url = '{0}?clientname=server'.format(__cso_ws_url)
        c.cso_logger.info('WS Client connect to URL: {0}'.format(__url))
        self.ws_client = WSClient(name='server', url=__url)
        self.ws_client.connect()
        self.ws_handler = WSStreamHandler(ws_client=self.ws_client, tq=self.tq)
        self.ws_handler.setFormatter(logging.Formatter("%(message)s"))
        self.ws_handler.setLevel(logging.DEBUG)
        c.jnpr_junos_tty.addHandler(self.ws_handler)
        c.jnpr_junos_tty_netconf.addHandler(self.ws_handler)
        c.jnpr_junos_tty_telnet.addHandler(self.ws_handler)
        self._stop_event = Event()
        self.final_result = True

    def run(self):

        for target, target_data in self.__data.items():
            c.cso_logger.info('[{0}][TQ]: Start deploy usecase <{1}>'.format(target, self.use_case_name))
            df = DriverFactory(name=c.CONFIG['driver'])
            driver = df.init_driver(target_data=target_data, use_case_name=self.use_case_name,
                                    use_case_data=self.use_case_data, ws_client=self.ws_client,
                                    ws_handler=self.ws_handler, event=self._stop_event, daemon=self.daemon,
                                    queue=self.queue)
            # driver.setDaemon(True)
            self.tq[driver.name] = driver

        _ = {driver.start() for target, driver in self.tq.items()}
        _ = {driver.join() for target, driver in self.tq.items()}

        while not self.queue.empty():
            for k,v in self.queue.get().items():
                if not v:
                    self.final_result = v

        if self.final_result:
            message = {'action': 'update_card_deploy_status', 'usecase': self.use_case_name, 'status': True,
                       'image': self.use_case_data['image_deployed']}
            self.emit_message(message=message)
            yaml = YAML(typ='rt')

            with open('config/items.yml', 'r') as ifp:

                _data = yaml.load(ifp)
                _data['deployed_usecase'] = self.use_case_name

                for k, v in _data['usecases'].items():
                    if k == self.use_case_name:
                        v['deployed'] = True

            with open('config/items.yml', 'w+') as ofp:
                yaml.dump(_data, ofp)

        else:
            message = {'action': 'update_card_deploy_status', 'usecase': self.use_case_name, 'status': False,
                       'image': self.use_case_data['image']}
            self.emit_message(message=message)
            yaml = YAML(typ='rt')

            with open('config/items.yml', 'r') as fp:

                _data = yaml.load(fp)
                _data['deployed_usecase'] = None

                for k, v in _data['usecases'].items():
                    if k == self.use_case_name:
                        v['deployed'] = False

            with open('config/items.yml', 'w+') as ofp:
                yaml.dump(_data, ofp)

        #message = {'action': 'cleanup_after_deploy', 'usecase': self.use_case_name, 'status': self.final_result}
        #self.emit_message(message=message)
        c.jnpr_junos_tty.removeHandler(self.ws_handler)
        c.jnpr_junos_tty_netconf.removeHandler(self.ws_handler)
        c.jnpr_junos_tty_telnet.removeHandler(self.ws_handler)

    def emit_message(self, message=None):

        if message is not None:
            self.ws_client.send(json.dumps(message))
        else:
            c.cso_logger.info('[WS_CLIENT]: {0}'.format('Can not send empty message'))

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
