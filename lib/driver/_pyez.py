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
import uuid
import shutil

from git import Repo
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

    def __init__(self):
        super().__init__()
        print('Loading PyEZ driver')
        self.session = None
        self.gl = None
        self.mode = None
        self.address = None
        self.port = None
        self.user = None
        self.pw = None
        self._data = None
        self._use_case_path = None
        self._dev = None
        self.jnpr_junos_tty = logging.getLogger('jnpr.junos.tty')
        self.jnpr_junos_tty_netconf = logging.getLogger('jnpr.junos.tty_netconf')
        formatter = logging.Formatter("%(message)s")
        self.ws = WSHandler(ws_client=self.ws_client)
        self.ws.setFormatter(formatter)
        self.ws.setLevel(logging.INFO)
        self.jnpr_junos_tty.addHandler(self.ws)
        self.jnpr_junos_tty_netconf.addHandler(self.ws)

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

    def connect(self, target=None, after_zeroize=False):
        self.ws.target = target
        self.ws.task = 'Connect'

        if after_zeroize:

            try:
                self._dev = Device(host=target['address'], mode=target['mode'], port=target['port'],
                                   user=target['user'], gather_facts=False)
                message = {'action': 'update_session_output', 'msg': 'Connecting to target: {0}\n'.format(target['name'])}
                self.emit_message(message=message)
                message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': target['uuid'],
                           'status': 'Connecting...'}
                self.emit_message(message=message)
                self._dev.open()
                message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': target['uuid'],
                           'status': 'Connected'}
                self.emit_message(message=message)

                message = {'action': 'update_session_output',
                           'msg': '\nConnected to target: {0}\n'.format(target['name'])}
                self.emit_message(message=message)

            except (RuntimeError, OSError) as err:
                print(err)
                return False

        else:

            try:
                self._dev = Device(host=target['address'], mode=target['mode'], port=target['port'],
                                   user=target['user'],
                                   password=target['password'], gather_facts=False)
                message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': target['uuid'],
                           'msg': 'Connecting to target: {0}\n'.format(target['name'])}
                self.emit_message(message=message)
                message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': target['uuid'],
                           'status': 'Connecting...'}
                self.emit_message(message=message)
                self._dev.open()
                message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': target['uuid'],
                           'msg': 'Connected to target: {0}\n'.format(target['name'])}
                self.emit_message(message=message)
                message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': target['uuid'],
                           'status': 'Get target model...'}
                self.emit_message(message=message)
                message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': target['uuid'],
                           'msg': 'Get target model...\n'}
                self.emit_message(message=message)
                re = self._dev.rpc.get_route_engine_information({'format': 'json'})
                message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': target['uuid'],
                           'msg': 'Target RE Model: '}
                self.emit_message(message=message)

                for t in self.__data:
                    if t['name'] == target['name']:
                        print(t)
                        t['model'] = re['route-engine-information'][0]['route-engine'][0]['model'][0]['data']
                        message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': target['uuid'],
                                   'msg': t['model']+'\n'}
                        self.emit_message(message=message)

            except (RuntimeError, OSError) as err:
                print(err)
                return False

        message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)

    def disconnect(self, target=None):
        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': target['uuid'],
                   'status': 'Disconnecting...'}
        self.emit_message(message=message)
        self._dev.close(skip_logout=True)
        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)

    def clone(self):

        URL = '{0}://git@{1}:{2}/{3}.git'.format('ssh', c.CONFIG['git_host'], c.CONFIG['git_ssh_port'],
                                                 c.CONFIG['git_repo_url'])
        print('Fetch use case data from repo <{0}>'.format(URL))
        PATH = '{0}'.format(c.CONFIG['tmp_dir'])

        if os.path.exists(PATH):
            shutil.rmtree(PATH)

        resp = Repo.clone_from(URL, PATH)
        print(resp)
        time.sleep(3)
        ret_code = 0

        if ret_code == 0:
            return {'result': 'OK'}
        if ret_code > 0:
            return {'result': 'FAILED'}

    def get_target_tasks(self, use_case_name=None, use_case_data=None):
        print('Get target task list')

        self._use_case_name = use_case_name
        self._use_case_data = use_case_data
        self._use_case_path = '{0}/{1}'.format(self.tmp_dir, self._use_case_data['directory'])
        play = '{0}/{1}'.format(self._use_case_path, self._use_case_data['playbook'])
        self.__data = list()

        with open(play, 'r') as fd:
            play_data = yaml.safe_load(fd)

        for target, value in play_data['targets'].items():
            _tmp = {'name': target, **value, 'uuid': str(uuid.uuid4()), 'tasks': list()}
            _tmp['tasks'].append({'name': 'Connect', 'status': 'waiting'})
            for task, attr in value['tasks'].items():
                if attr['enabled']:
                    _tmp['tasks'].append({'name': task, 'status': 'waiting', **attr})
            _tmp['tasks'].append({'name': 'Disconnect', 'status': 'waiting'})
            self.__data.append(_tmp)

        return self.__data

    def run(self, use_case_name=None, use_case_data=None):
        print('Deploy use case <{0}>'.format(use_case_name))
        self._use_case_name = use_case_name
        self._use_case_data = use_case_data

        for target in self.__data:
            for task in target['tasks']:

                if task['name'] == 'Connect':
                    self.connect(target=target)
                elif task['name'] == 'Render':
                    _status, _data = self.render(target=target, task=task)
                    self.push(target=target, task=task, data=_data)
                elif task['name'] == 'Zerorize':
                    self.zeroize(target=target, task=task)
                elif task['name'] == 'Configure':
                    self.commit_config(target=target, task=task)
                elif task['name'] == 'Copy':
                    self.copy(target=target, task=task)
                elif task['name'] == 'Disconnect':
                    self.disconnect(target=target)

    def render(self, target=None, task=None):

        print('Render device <{0}> configuration and push to git'.format(target['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Render template'}
        self.emit_message(message=message)

        try:
            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self._use_case_path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(task['template'])

        except (TemplateNotFound, IOError) as err:
            print(err)
            return False, err

        with open('{0}/{1}'.format(self._use_case_path, task['template_data'])) as fd:
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
            file_path = '{0}/{1}/{2}'.format(self._use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

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
                    "content": _data.encode('utf-8'),
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
                file_path = '{0}/{1}/{2}'.format(self._use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

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
        print('Pull file <{0}> from git for use case <{1}>'.format(target['name'], self._use_case_name))

        try:
            project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
            _path = '{0}/{1}/{2}'.format(self._use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

            try:
                f = project.files.get(file_path=_path, ref='master')
                return True, f.decode()
            except GitlabError as ge:
                return False, 'Failed to get file with error: <{0}>'.format(ge)

        except (GitlabConnectionError, GitlabError) as gle:
            return False, 'Failed to get project with error: <0>'.format(gle.message)

    def zeroize(self, target=None, task=None):
        print('Zerorize device <{0}>'.format(target['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Zeroize initializing'}
        self.emit_message(message=message)
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
                self.disconnect(target=target)
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Done'}
                self.emit_message(message=message)
                break

            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                       'msg': str(data, 'utf-8')}
            self.emit_message(message=message)
            time.sleep(0.2)

    def commit_config(self, target=None, task=None):
        print('Commit configuration on device <{0}>'.format(target['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Connecting...'}
        self.emit_message(message=message)

        try:

            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self._use_case_path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(task['template'])

        except (TemplateNotFound, IOError) as err:
            print(err)
            return False, err

        with open('{0}/{1}'.format(self._use_case_path, task['template_data'])) as fd:
            data = yaml.safe_load(fd)
            config = template.render(data)
            message = {'action': 'update_task_output', 'task': task['name'], 'uuid': target['uuid'], 'msg': config}
            self.emit_message(message=message)
            print("Device <{0}> is rebooted. Waiting for daemons to be ready...".format(target['name']))
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Waiting for daemons to be ready...'}
            self.emit_message(message=message)

            # adding some timeout for telnet session to close properly. Need a better approach here!
            time.sleep(120)
            self.connect(target=target, after_zeroize=True)
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
