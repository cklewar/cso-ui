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

import os
import json
import tempfile
import subprocess
import lib.constants  as c
from ruamel.yaml import YAML
from lib.driver.driver import Base


class AnsibleDriver(Base):

    def __init__(self):
        super(AnsibleDriver, self).__init__()
        print('Loading Ansible driver')
        self.git_protocol = None
        self.git_ip = None
        self.git_port = None
        self.git_user = None
        self.git_pw = None
        self.git_ref = None
        self.git_path = None
        self.git_base_url = None
        tempfile.tempdir = self.tmp_dir
        self.fd, self.tmp_file = tempfile.mkstemp(prefix='cso-ui_')
        os.environ["CSO_WS_URL"] = '{0}://{1}:{2}/ws'.format(c.CONFIG['ws_client_protocol'], '127.0.0.1',
                                                             c.CONFIG['ws_client_port'])
        os.environ["CSO_GIT_PROTOCOL"] = c.CONFIG["git_protocol"]
        os.environ["CSO_GIT_HOST"] = c.CONFIG["git_host"]
        os.environ["CSO_GIT_PORT"] = str(c.CONFIG["git_port"])
        os.environ["CSO_GIT_REPO_URL"] = c.CONFIG["git_repo_url"]

    def authenticate(self):
        return True

    def fetch(self):

        w_dir = '{0}/lib'.format(os.getcwd())
        p_dir = '{0}'.format('playbooks')
        ret_code = self.__deploy(playbook='get_playbook_data.yml', temp_file=self.tmp_file, w_dir=w_dir,
                                 p_dir=p_dir)

        with open(self.fd, 'r') as fp1:
            ret = json.load(fp1)

        if ret_code == 0:
            return {'result': 'OK', 'uuid': ret['uuid'], 'target': ret['target']}
        if ret_code > 0:
            return {'result': 'FAILED', 'uuid': ret['uuid'], 'target': ret['target']}

    def run(self, use_case=None):
        self.__deploy(playbook=use_case, temp_file=self.tmp_file, w_dir=self.tmp_dir, p_dir='usecases')

    def __deploy(self, playbook=None, temp_file=None, w_dir=None, p_dir=None):

        old = os.getcwd()
        os.chdir(w_dir)
        pb = '{0}/{1}'.format(p_dir, playbook)
        command = "ansible-playbook {0} -e {1}:{2}".format(pb, "tmp_file", temp_file)
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        ret_code = process.returncode
        os.unlink(self.tmp_file)
        os.chdir(old)

        return ret_code

    def get_status_update(self):
        pass

    def load_settings(self):
        with open('config/driver/ansible.yml', 'r') as fp:
            _config = fp.read()
            yaml = YAML(typ='safe')
            config = yaml.load(_config)
            self.git_protocol = config['git_protocol']
            self.git_ip = config['git_ip']
            self.git_port = config['git_port']
            self.git_user = config['git_user']
            self.git_pw = config['git_pw']
            self.git_ref = config['git_ref']
            self.git_path = config['git_path']
            self.git_base_url = '{0}://{1}:{2}'.format(self.git_protocol, self.git_ip, self.git_port)
