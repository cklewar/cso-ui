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
import html

from lxml.etree import XMLSyntaxError
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

    def __init__(self, _data=None, use_case_name=None, use_case_data=None):
        super().__init__(_data=_data, use_case_name=use_case_name, use_case_data=use_case_data)
        c.cso_logger.info('Loading PyEZ driver')
        self.session = None
        self.gl = None
        self.rebooted = False
        self.ws = WSHandler(ws_client=self.ws_client, target_data=self.target_data)
        self.ws.setFormatter(logging.Formatter("%(message)s"))
        self.ws.setLevel(logging.DEBUG)
        self.status = False
        c.jnpr_junos_tty.addHandler(self.ws)
        c.jnpr_junos_tty_netconf.addHandler(self.ws)
        c.jnpr_junos_tty_telnet.addHandler(self.ws)

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
            c.cso_logger.info('{0} {1} {2}'.format(response.status_code, response.headers, response))
            return False, "GIT AUTH FAILED"

    def connect(self, target=None):
        c.cso_logger.info('[{0}][{1}]: Connecting to device'.format(target['name'], 'Connect'))
        self.ws.task = 'Connect'

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
            message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
                       'msg': self.gen_task_done_message(target=target, task={'name': 'Connect'})}
            self.emit_message(message=message)

            # message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target_data['uuid'],
            #           'status': 'Get target model...'}
            # self.emit_message(message=message)

            # message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
            #           'msg': 'Get target model...\n'}
            # self.emit_message(message=message)
            # model = self._dev.rpc.get_software_information({'format': 'json'})
            # message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
            #           'msg': 'Target RE Model: '}
            # self.emit_message(message=message)
            # self.target_data['model'] = model['software-information'][0]['product-model'][0]['data']
            # message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target_data['uuid'],
            #           'msg': self.target_data['model'] + '\n'}
            # self.emit_message(message=message)

        except (RuntimeError, OSError) as err:
            c.cso_logger.info(err)
            return False

        message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target_data['uuid'],
                   'status': 'Done'}
        self.emit_message(message=message)

    def disconnect(self, target=None):
        """
        Disconnect complete telnet session
        :return:
        """

        self.ws.task = 'Disconnect'
        c.cso_logger.info('[{0}][{1}]: Disconnect from device'.format(target['name'], 'Disconnect'))
        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target_data['uuid'],
                   'status': 'Disconnecting...'}
        self.emit_message(message=message)

        self._dev.close(skip_logout=True)
        message = {'action': 'update_session_output', 'task': 'Disconnect', 'uuid': target['uuid'],
                   'msg': self.gen_task_done_message(target=target, task={'name': 'Disconnect'})}
        self.emit_message(message=message)
        c.cso_logger.info('[{0}][{1}]: Disconnect from device --> DONE'.format(target['name'], 'Disconnect'))

        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target_data['uuid'],
                   'status': 'Done'}
        self.emit_message(message=message)

    def connect_netconf(self):
        self.ws.task = 'Connect'
        self._dev._tty.login()

    def disconnect_netconf(self, target=None):
        self.ws.task = 'Disconnect'
        c.cso_logger.info(
            '[{0}][{1}]: Disconnect netconf session'.format('Disconnect', target['name']))
        self._dev._tty.nc.close()
        c.cso_logger.info(
            '[{0}][{1}]: Disconnect netconf session --> DONE'.format('Disconnect', target['name']))

    def run(self):

        for task in self.target_data['tasks']:
            if task['name'] == 'Connect':
                self.connect(target=self.target_data)
            elif task['name'] == 'Render':
                _status, _data = self.render(target=self.target_data, task=task)

                if _status:
                    self.push(target=self.target_data, task=task, data=_data)
                else:
                    c.cso_logger.info(
                        '[{0}][{1}]: Pushing data failed <{2}>'.format(self.target_data['name'], task['name'], _data))
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target_data['uuid'],
                               'status': _data}
                    self.emit_message(message=message)
                    break

            elif task['name'] == 'Zerorize':
                self.zeroize(target=self.target_data, task=task)
            elif task['name'] == 'Configure':
                self.configure(target=self.target_data, task=task)
            elif task['name'] == 'Copy':
                self.copy(target=self.target_data, task=task)
            elif task['name'] == 'Disconnect':
                self.disconnect(target=self.target_data)

        message = {'action': 'update_card_deploy_status', 'usecase': self.use_case_name}
        self.emit_message(message=message)
        c.cso_logger.info(
            '[{0}][Run]: Deploy use case <{1}> --> DONE'.format(self.target_data['name'], self.use_case_name))

    def render(self, target=None, task=None):
        c.cso_logger.info(
            '[{0}][{1}]: Render configuration'.format(target['name'], task['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Render template'}
        self.emit_message(message=message)

        try:
            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self.use_case_path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(task['template'])

        except (TemplateNotFound, IOError) as err:
            c.cso_logger.info('[{0}]: {1}'.format(task['name'], err))
            return False, err

        with open('{0}/{1}'.format(self.use_case_path, task['template_data'])) as fd:
            data = yaml.safe_load(fd)
            config = template.render(data)

        message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                   'msg': config + '\n'}
        self.emit_message(message=message)

        message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                   'msg': self.gen_task_done_message(target=target, task=task)}
        self.emit_message(message=message)

        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)
        c.cso_logger.info(
            '[{0}][{1}]: Render configuration --> DONE'.format(target['name'], task['name']))

        return True, config

    def push(self, target=None, task=None, data=None):
        c.cso_logger.info('[{0}][{1}]: Push configuration to git'.format(target['name'], task['name']))
        status = self.authenticate()

        if status:

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Push config'}
            self.emit_message(message=message)

            try:

                project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
                c.cso_logger.info(
                    '[{0}][{1}]: Push configuration to git --> DONE'.format(target['name'], task['name']))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Done'}

                self.emit_message(message=message)

            except (GitlabConnectionError, GitlabError) as gle:
                return False, 'Failed to get project with error: <0>'.format(gle.message)

            _status, _data = self.pull(target=target, task=task)
            file_path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

            if _status:
                c.cso_logger.info('[{0}][{1}]: Updating file <{0}>'.format(target['name'], task['name']))

                file_body = {
                    "branch": c.CONFIG['git_branch'],
                    "content": data,
                    "commit_message": "Device config {0}".format(target['name'])
                }

                try:

                    _data = project.files.update(file_path=file_path, new_data=file_body)
                    c.cso_logger.info('[{0}][{1}]: Updating file <{0}> --> DONE'.format(target['name'], task['name']))
                    return True, _data

                except (GitlabConnectionError, GitlabError) as gle:
                    return False, 'Failed to update device template with error: <0>'.format(gle.message)

            else:
                c.cso_logger.info('[{0}][{1}]: Creating new file <{0}>'.format(target['name'], task['name']))

                file_body = {
                    "file_path": file_path,
                    "branch": c.CONFIG['git_branch'],
                    "content": data,
                    "commit_message": "Device config {0}".format(target['name'])
                }

                try:

                    _data = project.files.create(file_body)
                    c.cso_logger.info(
                        '[{0}][{1}]: Creating new file <{0}> --> DONE'.format(target['name'], task['name']))
                    return True, _data

                except (GitlabConnectionError, GitlabError) as gle:
                    return False, 'Failed to create device template with error: <0>'.format(gle.message)

    def update(self, target=None, task=None, data=None):
        c.cso_logger.info('[{0}][{1}]: Update device <{0}> configuration in git'.format(target['name'], task['name']))
        status = self.authenticate()

        if status:

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': task['uuid'],
                       'status': 'Pushing config'}
            self.emit_message(message=message)

            try:

                project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
                file_path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

                file_body = {
                    "branch": c.CONFIG['git_branch'],
                    "content": data.decode('utf-8'),
                    "commit_message": "Device config {0}".format(target['name'])
                }

            except (GitlabConnectionError, GitlabError) as gle:
                return False, 'Failed to get project with error: <0>'.format(gle.message)

            try:
                _response = project.files.update(file_body)
                c.cso_logger.info(
                    '[{0}][{1}]: Update configuration in git --> DONE'.format(target['name'], task['name']))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': task['uuid'], 'status': 'Done'}
                self.emit_message(message=message)
                return True, _response

            except GitlabCreateError as gce:
                return False, 'Failed to update template data with error: <{0}>'.format(gce)

    def pull(self, target=None, task=None):
        c.cso_logger.info(
            '[{0}][{1}]: Pull file <{0}> from git for use case <{2}>'.format(target['name'], task['name'],
                                                                             self.use_case_name))

        try:
            project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
            _path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], target['name'])

            try:
                f = project.files.get(file_path=_path, ref='master')
                c.cso_logger.info(
                    '[{0}][{1}]: Pull file <{0}> from git for use case <{2}> --> DONE'.format(target['name'],
                                                                                              task['name'],
                                                                                              self.use_case_name))
                return True, f.decode()
            except GitlabError as ge:
                return False, 'Failed to get file with error: <{0}>'.format(ge)

        except (GitlabConnectionError, GitlabError) as gle:
            return False, 'Failed to get project with error: <0>'.format(gle.message)

    def zeroize(self, target=None, task=None):
        c.cso_logger.info('[{0}][{1}]: Initialize zerorize device'.format(target['name'], task['name']))
        self.ws.task = task['name']
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Zeroize initializing'}
        self.emit_message(message=message)

        resp = self._dev.zeroize()
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Zeroize running'}
        self.emit_message(message=message)
        message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'], 'msg': resp}
        self.emit_message(message=message)

        while True:

            data = self._dev._tty._tn.read_until(b"\r\n")
            c.cso_logger.info('[{0}][{1}]: {2}'.format(target['name'], task['name'], str(data, 'utf-8')))
            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                       'msg': str(data, 'utf-8')}
            self.emit_message(message=message)

            if data.decode('utf-8').strip() in c.TERM_STRINGS:
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Disconnecting...'}
                self.emit_message(message=message)
                self.disconnect(target=target)
                self.rebooted = True
                message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': target['uuid'],
                           'status': 'waiting'}
                self.emit_message(message=message)
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Done'}
                self.emit_message(message=message)
                c.cso_logger.info('[{0}][{1}]: Zerorize device --> DONE'.format(target['name'], task['name']))
                message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                           'msg': self.gen_task_done_message(target=target, task=task)}
                self.emit_message(message=message)
                break

            time.sleep(0.2)

    def configure(self, target=None, task=None):
        self.ws.task = task['name']
        c.cso_logger.info('[{0}][{1}]: Commit configuration on device'.format(target['name'], task['name']))

        try:

            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self.use_case_path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(task['template'])

        except (TemplateNotFound, IOError) as err:
            c.cso_logger.info('[{0}][{1}]: {2}'.format(target['name'], task['name'], err))
            return False, err

        with open('{0}/{1}'.format(self.use_case_path, task['template_data'])) as fd:
            data = yaml.safe_load(fd)
            config = template.render(data)
            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                       'msg': config}
            self.emit_message(message=message)

            if self.rebooted:
                c.cso_logger.info(
                    "[{0}][{1}]: Device was rebooted. Waiting for daemons to be ready...".format(target['name'],
                                                                                                task['name']))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Waiting for daemons to be ready...'}
                self.emit_message(message=message)
                # adding some timeout for telnet session to close properly. Need a better approach here!
                mark_start = datetime.now()
                SECONDS = 120
                mark_end = mark_start + timedelta(seconds=SECONDS)

                while datetime.now() < mark_end:
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                               'status': 'Waiting for daemons to be ready... {0}'.format(SECONDS - 1)}
                    SECONDS -= 1
                    self.emit_message(message=message)
                    c.cso_logger.info(
                        "[{0}][{1}]: Device was rebooted. Waiting for daemons to be ready <{2}>".format(target['name'],
                                                                                                       task['name'],
                                                                                                       SECONDS - 1))
                    time.sleep(1)

                self.connect(target=target)

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Connecting...'}
            self.emit_message(message=message)
            cu = Config(self._dev)
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Load config'}
            self.emit_message(message=message)
            cu.load(config, merge=task['merge'], override=task['override'], update=task['update'])
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                       'status': 'Commit config'}
            self.emit_message(message=message)

            try:
                cu.commit(confirm=task['confirm'], sync=task['sync'])
            # Netconf Session gets dropped when override config with netconf server enabled. So we need to catch up here
            # and reconnect.
            except XMLSyntaxError as xse:
                c.cso_logger.info('[{0}][{1}]: {2}'.format(target['name'], task['name'], xse))
                self.disconnect(target=target)
                time.sleep(2)
                self.connect(target=target)
            self.disconnect_netconf(target=target)
            c.cso_logger.info(
                '[{0}][{1}]: Commit configuration on device --> DONE'.format(target['name'], task['name']))
            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                       'msg': self.gen_task_done_message(target=target, task=task)}
            self.emit_message(message=message)
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'], 'status': 'Done'}
            self.emit_message(message=message)

    def copy(self, target=None, task=None):
        self.ws.task = task['name']
        c.cso_logger.info(
            '[{0}][{1}]: Copy file <{2}> to <{3}>'.format(target['name'], task['name'], task['src'], task['dst']))

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
        message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                   'msg': self.gen_task_done_message(target=target, task=task)}
        self.emit_message(message=message)
        c.cso_logger.info(
            '[{0}][{1}]: Copy file <{2}> to <{3}> --> DONE'.format(target['name'], task['name'], task['src'],
                                                                   task['dst']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)

    def reboot(self, target=None, task=None):
        self.ws.task = task['name']
        c.cso_logger.info('{0}: Rebooting device {1}'.format(task['name'], target['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                   'status': 'Rebooting...'}
        self.emit_message(message=message)
        resp = self._dev.rpc.request_reboot()
        c.cso_logger.info('{0}: {1}'.format(task['name'], resp))

        while True:

            data = self._dev._tty._tn.read_until(b"\r\n")
            c.cso_c.cso_logger.info('{0}: {1} --> {2}'.format(task['name'], target['name'], str(data, 'utf-8')))

            if data.decode('utf-8').strip() in c.TERM_STRINGS:
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Disconnecting...'}
                self.emit_message(message=message)
                self.disconnect()
                self.rebooted = True
                message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': target['uuid'],
                           'status': 'waiting'}
                self.emit_message(message=message)
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': target['uuid'],
                           'status': 'Done'}
                self.emit_message(message=message)
                break

            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': target['uuid'],
                       'msg': str(data, 'utf-8')}
            self.emit_message(message=message)
            time.sleep(0.2)

    def gen_task_done_message(self, target=None, task=None):
        header = '{0} TASK {1} DONE {2}'.format(15 * '#', task['name'], 15 * '#')
        return header

    def load_settings(self):
        c.cso_logger.info('Loading driver settings')

        with open('config/driver/pyez.yml', 'r') as fp:
            _config = fp.read()
            yaml = YAML(typ='safe')
            config = yaml.load(_config)
            self.mode = config['mode']
            self.port = config['port']
            self.address = config['ip']
            self.user = config['user']
            self.pw = config['pw']
