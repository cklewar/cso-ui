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


import requests

from ruamel.yaml import YAML
from contextlib import contextmanager
from requests import ConnectionError


class SaltDriver(object):

    def __init__(self):
        super(SaltDriver, self).__init__()
        self.edi_protocol = None
        self.edi_ip = None
        self.edi_port = None
        self.edi_user = None
        self.edi_pw = None
        self.edi_auth_module = None
        self.edi_base_url = None
        self.edi_runner = None
        self.git_ref = None
        self.git_path = None

    @contextmanager
    def authenticate(self):

        url = '{0}/login'.format(self.edi_base_url)
        session = requests.Session()

        data = {
            'username': "{0}".format(self.edi_user),
            'password': "{0}".format(self.edi_pw),
            'eauth': "{0}".format(self.edi_auth_module),
        }

        try:

            resp = session.post(url, json=data, verify=False)
            yield session

        except ConnectionError as cer:
            print(cer)

        url = '{0}/logout'.format(self.edi_base_url)

        try:

            resp = session.post(url, verify=False)
            print(resp.status_code)

        except ConnectionError as cer:
            print(cer)

    def deploy(self, use_case_name=None):

        with self.authenticate() as session:

            _data = {
                "client": "runner",
                "fun": "{0}.{1}".format(self.edi_runner, 'get_data_from_git'),
                "upstream_path": '{0}'.format('useCases/useCases.yml'),
                "ref": self.git_ref
            }

            url = '{0}'.format(self.edi_base_url)

            try:

                resp = session.post(url, json=_data, verify=False).json()

                if resp['return'][0]['success']:
                    yaml = YAML()
                    use_cases = yaml.load(resp['return'][0]['changes'])
                    use_case = use_cases[use_case_name]

                    _data = {
                        "client": "runner",
                        "fun": "{0}.{1}".format(self.edi_runner, 'run_ansible_playbook'),
                        "playbook": use_case['playbook'],
                    }

                    url = '{0}'.format(self.edi_base_url)

                    try:

                        resp = session.post(url, json=_data, verify=False).json()
                        d = resp['return'][0]['jedi']
                        first = next(iter(resp['return'][0]['jedi']))
                        return True, d[first]['changes']['stdout']

                    except ConnectionError as cer:
                        return False, cer

            except ConnectionError as cer:
                return False, cer

    '''
    def load_use_cases(self):

        with self.authenticate() as session:

            _data = {
                "client": "runner",
                "fun": "{0}.{1}".format(self.edi_runner, 'get_data_from_git'),
                "upstream_path": '{0}'.format('useCases/useCases.yml'),
                "ref": self.git_ref
            }

            url = '{0}'.format(self.edi_base_url)

            try:

                resp = session.post(url, json=_data, verify=False).json()

                if resp['return'][0]['success']:
                    yaml = YAML()
                    use_cases = yaml.load(resp['return'][0]['changes'])
                    return True, use_cases

            except ConnectionError as cer:
                return False, cer
    '''

    def load_settings(self):
        with open('config/driver/salt.yml', 'r') as fp:
            _config = fp.read()
            yaml = YAML(typ='safe')
            config = yaml.load(_config)
            self.edi_protocol = config['edi_protocol']
            self.edi_ip = config['edi_ip']
            self.edi_port = config['edi_port']
            self.edi_user = config['edi_user']
            self.edi_pw = config['edi_pw']
            self.edi_auth_module = config['edi_auth_module']
            self.edi_runner = config['edi_runner']
            self.edi_base_url = '{0}://{1}:{2}'.format(self.edi_protocol, self.edi_ip, self.edi_port)
            self.git_ref = config['git_ref']
            self.git_path = config['git_path']