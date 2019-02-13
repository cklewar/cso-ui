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
import pprint
import gitlab
import lib.constants as c
import requests
import json
import time
import socket
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


class PyEzDriver(Base):

    def __init__(self, ws_client=None):
        super().__init__(ws_client=ws_client)
        print('Loading PyEZ driver')
        self.session = None
        self.gl = None
        self.mode = None
        self.address = None
        self.port = None
        self.user = None
        self.pw = None
        self._data = None
        self._path = None

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

    def fetch(self):
        URL = '{0}://git@{1}:{2}/{3}.git'.format('ssh', c.CONFIG['git_host'], c.CONFIG['git_ssh_port'],
                                                 c.CONFIG['git_repo_url'])
        print('Fetch use case data from repo <{0}>'.format(URL))
        PATH = '{0}'.format(c.CONFIG['tmp_dir'])

        if os.path.exists(PATH):
            shutil.rmtree(PATH)

        resp = Repo.clone_from(URL, PATH)
        print(resp)
        ret_code = 0

        if ret_code == 0:
            return {'result': 'OK', 'uuid': str(uuid.uuid4()), 'target': '1'}
        if ret_code > 0:
            return {'result': 'FAILED', 'uuid': str(uuid.uuid4()), 'target': '1'}

    def run(self, use_case_name=None, use_case_data=None):
        print('Deploy use case <{0}>'.format(use_case_name))

        self._data = list()
        self._use_case_name = use_case_name
        self._use_case_data = use_case_data

        try:
            self.ws_client.connect()
        except socket.error as se:
            print(se.filename, se.strerror, se.args, se.errno)

        self._path = '{0}/{1}'.format(self.tmp_dir, self._use_case_data['directory'])
        play = '{0}/{1}'.format(self._path, self._use_case_data['playbook'])

        with open(play, 'r') as fd:
            play_data = yaml.safe_load(fd)

        for target, value in play_data['targets'].items():

            _tmp = {'name': target, 'address': value['address'], 'port': value['port'], 'mode': value['mode'],
                    'user': value['user'], 'password': value['password'], 'template': value['template'],
                    'template_data': value['template_data'], 'tasks': list()}

            for task, state in play_data['tasks'].items():
                print(task, state)

                if state:
                    _tmp['tasks'].append({'name': task, 'status': 'waiting', 'uuid': str(uuid.uuid4())})

            self._data.append(_tmp)

        message = {'action': 'add_tasks', 'data': self._data}
        self.emit_message(message=message)

        for target in self._data:
            for task in target['tasks']:

                if task['name'] == 'Render':
                    self.render(target=target, task=task)
                elif task['name'] == 'Zerorize':
                    self.zeroize(target=target, task=task)
                elif task['name'] == 'Configure':
                    self.commit_config(target=target, task=task)
                elif task['name'] == 'Copy':
                    self.copy(target=target, task=task)

    def render(self, target=None, task=None):
        print('Render device <{0}> configuration and push to git'.format(target['name']))
        message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Render template'}
        self.emit_message(message=message)

        try:

            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self._path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(target['template'])

        except (TemplateNotFound, IOError) as err:
            print('Error({0}): {1} --> {2})'.format(err.errno, err.strerror, err.filename))
            return False, err

        with open('{0}/{1}'.format(self._path, target['template_data'])) as fd:
            data = yaml.safe_load(fd)
            config = template.render(data)

        status = self.authenticate()

        if status:

            message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Push config'}
            self.emit_message(message=message)

            try:

                project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
                file_path = '{0}/{1}/{2}'.format(self._use_case_name, 'config', target['name'])

                file_body = {
                    "file_path": file_path,
                    "branch": "master",
                    "content": config,
                    "commit_message": "Device config {0}".format(target['name'])
                }

                message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Done'}
                self.emit_message(message=message)

            except (GitlabConnectionError, GitlabError) as gle:
                return False, 'Failed to get project with error: <0>'.format(gle.message)

            try:
                f = project.files.create(file_body)
                return status, f

            except GitlabCreateError as gce:
                return False, 'Failed to add device config with error: <{0}>'.format(gce)

    def zeroize(self, target=None, task=None):

        print('Zerorize device <{0}>'.format(target['name']))
        message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Zeroize initializing'}
        self.emit_message(message=message)

        try:

            try:
                dev = Device(host=target['address'], mode=target['mode'], port=target['port'], user=target['user'],
                             password=target['password'])
                dev.open()
                resp = dev.zeroize()

            except (RuntimeError, OSError) as err:
                print(err)

            message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Zeroize initialized'}
            self.emit_message(message=message)

            while True:

                data = dev._tty._tn.read_until(b"\r\n")
                print(str(data, 'utf-8'))

                if data.decode('utf-8').strip() in c.TERM_STRINGS:
                    print("Device <{0}> is rebooted. Waiting for daemons to come up...".format(target['name']))
                    message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Done'}
                    self.emit_message(message=message)
                    dev.close(skip_logout=True)
                    break

                message = {'action': 'update_session_output', 'uuid': task['uuid'],
                           'msg': str(data, 'utf-8')}
                self.emit_message(message=message)
                time.sleep(0.2)

        except (EOFError, OSError) as err:
            print(err)

    def commit_config(self, target=None, task=None):

        print('Pushing configuration to device <{0}>'.format(target['name']))

        try:

            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self._path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(target['template'])

        except (TemplateNotFound, IOError) as err:
            print('Error({0}): {1} --> {2})'.format(err.errno, err.strerror, err.filename))
            return False, err

        with open('{0}/{1}'.format(self._path, target['template_data'])) as fd:
            data = yaml.safe_load(fd)
            config = template.render(data)

        try:

            dev = Device(host=target['address'], user=self.user, passwd=self.pw, mode=target['mode'],
                         port=target['port'], console_has_banner=True)
            message = {'action': 'update_task_status', 'uuid': task['uuid'],
                       'status': 'Waiting for daemons to be ready...'}
            self.emit_message(message=message)
            result = dev.probe(timeout=60)

            if result:
                # adding some timeout for telnet session to close properly. Need a better approach here!
                time.sleep(90)

                message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Connecting...'}
                self.emit_message(message=message)
                dev.open()
                cu = Config(dev)
                message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Lock config'}
                self.emit_message(message=message)
                cu.lock()
                message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Load config'}
                self.emit_message(message=message)
                cu.load(config, merge=True)
                message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Commit config'}
                self.emit_message(message=message)
                cu.commit()
                message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Unlock config'}
                self.emit_message(message=message)
                cu.unlock()
                message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Done'}
                self.emit_message(message=message)
                dev.close()

        except (ConnectionResetError, RuntimeError) as err:
            print(err)
            return False, err

    def copy(self, target=None, task=None):
        print('Copy file to device <{0}>'.format(target['name']))
        message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'Done'}
        self.emit_message(message=message)

    def get_status_update(self):
        pass

    def load_settings(self):
        with open('config/driver/pyez.yml', 'r') as fp:
            _config = fp.read()
            yaml = YAML(typ='safe')
            config = yaml.load(_config)
            print(config)
            self.mode = config['mode']
            self.port = config['port']
            self.address = config['ip']
            self.user = config['user']
            self.pw = config['pw']