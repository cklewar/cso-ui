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
import logging
import pprint
import gitlab
import lib.constants as c
import requests
import json
import time
import yaml
import six

from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from jnpr.junos.utils.config import Config
from jnpr.junos import Device
from jnpr.junos.exception import ConfigLoadError, CommitError
from jnpr.junos.exception import RpcError
from gitlab.exceptions import GitlabError, GitlabDeleteError, GitlabConnectionError, GitlabCreateError
from ruamel.yaml import YAML
from lib.driver.driver import Base
from lib.handler import WSHandler


class PyEzDriver(Base):
    NEW_LINE = six.b('\n')
    EMPTY_STR = six.b('')
    NETCONF_EOM = six.b(']]>]]>')
    STARTS_WITH = six.b("<!--")

    def __init__(self, _data=None, use_case_name=None, use_case_data=None):
        super().__init__(_data=_data, use_case_name=use_case_name, use_case_data=use_case_data)
        print('Loading PyEZ driver')
        self.session = None
        self.gl = None
        self.rebooted = False
        self.jnpr_junos_tty = logging.getLogger('jnpr.junos.tty')
        self.jnpr_junos_tty_netconf = logging.getLogger('jnpr.junos.tty_netconf')
        self.jnpr_junos_tty_telnet = logging.getLogger('jnpr.junos.tty_telnet')
        formatter = logging.Formatter("%(message)s")
        self.ws = WSHandler(ws_client=self.ws_client, target_data=self.target_data)
        self.ws.setFormatter(formatter)
        self.ws.setLevel(logging.INFO)
        self.jnpr_junos_tty.addHandler(self.ws)
        self.jnpr_junos_tty_netconf.addHandler(self.ws)
        self.jnpr_junos_tty_telnet.addHandler(self.ws)

    def authenticate(self):

        URL = '{0}://{1}:{2}'.format(c.CONFIG['git_protocol'], c.CONFIG['git_host'],
                                     c.CONFIG['git_http_port'])
        LOGIN_URL = '{0}{1}'.format(URL, c.CONFIG['git_login_url'])

        payload = {
            "grant_type": "password",
            "username": c.CONFIG['git_user'],
            "password": c.CONFIG['git_password']
        }
        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache"
        }

        try:

            response = requests.request("POST", LOGIN_URL, data=json.dumps(payload), headers=headers)

        except ConnectionError as ce:
            return False, 'Connection error: <{0}>'.format(ce.errno)

        if response.status_code == 200:
            resp = json.loads(response.content)

            if 'access_token' in resp:

                access_token = resp['access_token']
                self.gl = gitlab.Gitlab(URL, oauth_token=access_token)
                return True, "GIT AUTH OK"
            else:
                return False, "GIT AUTH FAILED"
        else:
            print(response.status_code, response.headers, response)
            return False, "GIT AUTH FAILED"

    def connect(self):
        self.ws.task = 'Connect'
        message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
                   'msg': 'Connecting to target: {0}\n'.format(self.target_data['name'])}
        self.emit_message(message=message)


        try:
            self._dev = Device(host=self.target_data['address'], mode=self.target_data['mode'],
                               port=self.target_data['port'],
                               user=self.target_data['user'],
                               password=self.target_data['password'], gather_facts=False)
            message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
                       'msg': 'Connecting to target: {0}\n'.format(self.target_data['name'])}
            self.emit_message(message=message)
            message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target_data['uuid'],
                       'status': 'Connecting...'}
            self.emit_message(message=message)
            self._dev.open()
            message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
                       'msg': 'Connected to target: {0}\n'.format(self.target_data['name'])}
            self.emit_message(message=message)
            message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target_data['uuid'],
                       'status': 'Get target model...'}
            self.emit_message(message=message)
            #message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
            #           'msg': 'Get target model...\n'}
            #self.emit_message(message=message)
            #model = self._dev.rpc.get_software_information({'format': 'json'})
            #message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
            #           'msg': 'Target RE Model: '}
            #self.emit_message(message=message)
            #self.target_data['model'] = model['software-information'][0]['product-model'][0]['data']
            #message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
            #           'msg': self.target_data['model'] + '\n'}
            #self.emit_message(message=message)

        except (RuntimeError, OSError) as err:
            print(err)
            return False

        message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target_data['uuid'],
                   'status': 'Done'}
        self.emit_message(message=message)

    def disconnect(self):
        """
        Disconnect complete telnet session
        :return:
        """
        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target_data['uuid'],
                   'status': 'Disconnecting...'}
        self.emit_message(message=message)
        self._dev.close(skip_logout=True)
        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target_data['uuid'],
                   'status': 'Done'}
        self.emit_message(message=message)

    def connect_netconf(self):
        self._dev._tty.login()

    def disconnect_netconf(self):
        self._dev._tty.nc.close()

    def run(self):
        print('Deploy use case <{0}>'.format(self.use_case_name))

        for task in self.target_data['tasks']:
            if task['name'] == 'Connect':
                self.connect()
            elif task['name'] == 'Render':
                _status, _data = self.render(target=self.target_data, task=task)

                if _status:
                    self.push(target=self.target_data, task=task, data=_data)
                else:
                    print(_status, _data)

            elif task['name'] == 'Zerorize':
                self.zeroize(target=self.target_data, task=task)
            elif task['name'] == 'Configure':
                self.commit_config(target=self.target_data, task=task)
            elif task['name'] == 'Copy':
                self.copy(target=self.target_data, task=task)
            elif task['name'] == 'Disconnect':
                self.disconnect()

    def render(self, target=None, task=None):
        print('Render device <{0}> configuration and push to git'.format(target['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Render template'}
        self.emit_message(message=message)

        try:
            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self.use_case_path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(task['template'])

        except (TemplateNotFound, IOError) as err:
            print(err)
            return False, err

        with open('{0}/{1}'.format(self.use_case_path, task['template_data'])) as fd:
            data = yaml.safe_load(fd)
            config = template.render(data)

        message = {'action': 'update_task_output', 'task': task['name'], 'uuid': target['uuid'], 'msg': config}
        self.emit_message(message=message)

        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)

        return True, config

    def push(self, target=None, task=None, data=None):
        print('Push device <{0}> configuration to git'.format(target['name']))
        status = self.authenticate()

        if status:

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Push config'}
            self.emit_message(message=message)

            try:

                project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Done'}
                self.emit_message(message=message)

            except (GitlabConnectionError, GitlabError) as gle:
                return False, 'Failed to get project with error: <0>'.format(gle.message)

            _status, _data = self.pull(target=target, task=task)
            file_path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

            if _status:
                print('Updating file <{0}>'.format(target['name']))

                file_body = {
                    "branch": c.CONFIG['git_branch'],
                    "content": data,
                    "commit_message": "Device config {0}".format(target['name'])
                }

                try:

                    _data = project.files.update(file_path=file_path, new_data=file_body)
                    return True, _data

                except (GitlabConnectionError, GitlabError) as gle:
                    return False, 'Failed to update device template with error: <0>'.format(gle.message)

            else:
                print('Creating new file <{0}>'.format(target['name']))

                file_body = {
                    "file_path": file_path,
                    "branch": c.CONFIG['git_branch'],
                    "content": data,
                    "commit_message": "Device config {0}".format(target['name'])
                }

                try:

                    _data = project.files.create(file_body)
                    return True, _data

                except (GitlabConnectionError, GitlabError) as gle:
                    return False, 'Failed to create device template with error: <0>'.format(gle.message)

    def update(self, target=None, task=None, data=None):
        print('Update device <{0}> configuration in git'.format(target['name']))
        status = self.authenticate()

        if status:

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': task['uuid'],
                       'status': 'Push config'}
            self.emit_message(message=message)

            try:

                project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
                file_path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

                file_body = {
                    "branch": c.CONFIG['git_branch'],
                    "content": data.decode('utf-8'),
                    "commit_message": "Device config {0}".format(target['name'])
                }

                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': task['uuid'], 'status': 'Done'}
                self.emit_message(message=message)

            except (GitlabConnectionError, GitlabError) as gle:
                return False, 'Failed to get project with error: <0>'.format(gle.message)

            try:
                _response = project.files.update(file_body)
                return True, _response

            except GitlabCreateError as gce:
                return False, 'Failed to update template data with error: <{0}>'.format(gce)

    def pull(self, target=None, task=None):
        print('Pull file <{0}> from git for use case <{1}>'.format(target['name'], self.use_case_name))

        try:
            project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
            _path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

            try:
                f = project.files.get(file_path=_path, ref='master')
                return True, f.decode()
            except GitlabError as ge:
                return False, 'Failed to get file with error: <{0}>'.format(ge)

        except (GitlabConnectionError, GitlabError) as gle:
            return False, 'Failed to get project with error: <0>'.format(gle.message)

    def zeroize(self, target=None, task=None):
        print('Zerorize device <{0}>'.format(target['name']))
        self.ws.task = task['name']
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Zeroize initializing'}
        self.emit_message(message=message)
        time.sleep(2)
        '''
        resp = self._dev.zeroize()
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Zeroize initialized'}
        self.emit_message(message=message)
        message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'], 'msg': resp}
        self.emit_message(message=message)

        while True:

            data = self._dev._tty._tn.read_until(b"\r\n")
            print(str(data, 'utf-8'))

            if data.decode('utf-8').strip() in c.TERM_STRINGS:
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Disconnecting...'}
                self.emit_message(message=message)
                self.disconnect_netconf()
                self.rebooted = True
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Done'}
                self.emit_message(message=message)
                break

            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                       'msg': str(data, 'utf-8')}
            self.emit_message(message=message)
            time.sleep(0.2)
        '''
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Done'}
        self.emit_message(message=message)

    def commit_config(self, target=None, task=None):
        print('Commit configuration on device <{0}>'.format(target['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Connecting...'}
        self.emit_message(message=message)
        time.sleep(5)

        '''
        try:

            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self.use_case_path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(task['template'])

        except (TemplateNotFound, IOError) as err:
            print(err)
            return False, err

        with open('{0}/{1}'.format(self.use_case_path, task['template_data'])) as fd:
            data = yaml.safe_load(fd)
            config = template.render(data)
            message = {'action': 'update_task_output', 'task': task['name'], 'uuid': target['uuid'], 'msg': config}
            self.emit_message(message=message)
            print("Device <{0}> is rebooted. Waiting for daemons to be ready...".format(target['name']))
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Waiting for daemons to be ready...'}
            self.emit_message(message=message)

            if self.rebooted:
                # adding some timeout for telnet session to close properly. Need a better approach here!
                mark_start = datetime.now()
                SECONDS = 120
                mark_end = mark_start + timedelta(seconds=SECONDS)

                while datetime.now() < mark_end:
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                               'status': 'Waiting for daemons to be ready... {0}'.format(SECONDS - 1)}
                    SECONDS -= 1
                    self.emit_message(message=message)
                    time.sleep(1)

                self.connect_netconf()

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Connecting...'}
            self.emit_message(message=message)
            cu = Config(self._dev)
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Lock config'}
            self.emit_message(message=message)
            cu.lock()
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Load config'}
            self.emit_message(message=message)
            cu.load(config, merge=task['merge'], override=task['override'], update=task['update'])
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Commit config'}
            self.emit_message(message=message)
            cu.commit(confirm=task['confirm'])
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Unlock config'}
            self.emit_message(message=message)
            cu.unlock()
        
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'], 'status': 'Done'}
            self.emit_message(message=message)
            '''
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)

    def copy(self, target=None, task=None):
        print('Copy file <{0}> to <{1}>'.format(task['src'], task['dst']))

        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Copy file {0}'.format(task['src'])}
        self.emit_message(message=message)
        _file = '{0}/{1}'.format(c.CONFIG['tmp_dir'], task['src'])
        self._dev._tty._tn.write('cat > {0} << EOF'.format(task['dst']).encode('ascii') + b"\n\r")

        with open(_file, 'r') as fd:
            for line in fd:
                self._dev._tty._tn.write(line.encode("ascii"))
                message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                           'msg': str(line.encode("ascii"), 'utf-8')}
                self.emit_message(message=message)
                time.sleep(1)

        self._dev._tty._tn.write('clear'.encode("ascii") + b"\n\r")

        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)

    def load_settings(self):
        with open('config/driver/pyez.yml', 'r') as fp:
            _config = fp.read()
            yaml = YAML(typ='safe')
            config = yaml.load(_config)
            self.mode = config['mode']
            self.port = config['port']
            self.address = config['ip']
            self.user = config['user']
            self.pw = config['pw']
