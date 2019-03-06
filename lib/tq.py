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
import threading
import queue as queue
import json

from ruamel.yaml import YAML
from threading import Thread
from lib.factory import DriverFactory
from lib.wsclient import WSClient


class TargetQueue(Thread):

    def __init__(self, _data=None, use_case_name=None, use_case_data=None, group=None, target=None, name=None, args=(),
                 kwargs=None, *, daemon=None):
        super(TargetQueue, self).__init__(group=group, target=target, name=name, daemon=daemon)
        self.__data = _data
        self.use_case_name = use_case_name
        self.use_case_data = use_case_data
        self.tq = list()
        self.q = queue.Queue()
        self.e = threading.Event()
        self.results = {'overall': False}
        __cso_ws_url = '{0}://{1}:{2}/ws'.format(c.CONFIG['ws_client_protocol'], c.CONFIG['ws_client_ip'],
                                                 c.CONFIG['ws_client_port'])
        __url = '{0}?clientname=server'.format(__cso_ws_url)
        c.cso_logger.info('WS Client connect to URL: {0}'.format(__url))
        self.ws_client = WSClient(name='server', url=__url)
        self.ws_client.connect()

    def run(self):

        for target in self.__data:
            c.cso_logger.info('[{0}][TQ]: Start deploy usecase <{1}>'.format(target['name'], self.use_case_name))
            df = DriverFactory(name=c.CONFIG['driver'])
            driver = df.init_driver(target_data=target, use_case_name=self.use_case_name,
                                    use_case_data=self.use_case_data, results=self.results, ws_client=self.ws_client)
            self.tq.append(driver)
            driver.start()

        for d in self.tq:
            d.join()

        if self.results['overall']:
            message = {'action': 'update_card_deploy_status', 'usecase': self.use_case_name, 'status': True}
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
            message = {'action': 'update_card_deploy_status', 'usecase': self.use_case_name, 'status': False}
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

    def emit_message(self, message=None):

        if message is not None:
            self.ws_client.send(json.dumps(message))
        else:
            print('empty message')

