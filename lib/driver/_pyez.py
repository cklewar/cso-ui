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

import logging
import re
import pprint
import gitlab
import lib.constants as c
import requests
import json
import time
import yaml

from lxml.etree import XMLSyntaxError
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from jnpr.junos.utils.config import Config
from jnpr.junos import Device
from jnpr.junos.exception import ConfigLoadError, CommitError, ConnectClosedError, ConnectAuthError
from jnpr.junos.exception import RpcError
from gitlab.exceptions import GitlabError, GitlabDeleteError, GitlabConnectionError, GitlabCreateError, GitlabHttpError
from ruamel.yaml import YAML
from lib.driver.driver import Base
from lib.handler import WSHandler


class PyEzDriver(Base):

    def __init__(self, target_data=None, use_case_name=None, use_case_data=None, results=None, ws_client=None):
        super().__init__(target_data=target_data, use_case_name=use_case_name, use_case_data=use_case_data,
                         results=results,
                         ws_client=ws_client)
        c.cso_logger.info('Loading PyEZ driver')
        self.session = None
        self.gl = None
        self.isRebooted = False
        self.isNetConf = False
        self.isConnected = False
        self.status = True
        self.isZeroized = False
        self.ws = WSHandler(ws_client=self.ws_client, target_data=self.target)
        self.ws.setFormatter(logging.Formatter("%(message)s"))
        self.ws.setLevel(logging.DEBUG)
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

    def connect(self):
        c.cso_logger.info('[{0}][{1}]: Connecting to device'.format(self.target['name'], 'Connect'))
        self.ws.task = 'Connect'

        try:
            self._dev = Device(host=self.target['address'], mode=self.target['mode'],
                               port=self.target['port'],
                               user=self.target['user'],
                               password=self.target['password'], gather_facts=False)
            message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target['uuid'],
                       'msg': 'Connecting to target: {0}\n'.format(self.target['name'])}
            self.emit_message(message=message)
            message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target['uuid'],
                       'status': 'Connecting...'}
            self.emit_message(message=message)

            try:
                self._dev.open()

            except ConnectAuthError as err:
                message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target['uuid'],
                           'status': str(err)}
                self.emit_message(message=message)
                c.cso_logger.info(
                    '[{0}][{1}]: Connecting to device failed: {2}'.format(self.target['name'], 'Connect', err))
                return False

            self.isNetConf = True
            self.isConnected = True
            message = {'action': 'update_session_output', 'task': 'Connect', 'uuid': self.target['uuid'],
                       'msg': 'Connected to target: {0}\n'.format(self.target['name'])}
            self.emit_message(message=message)
            c.cso_logger.info('[{0}][{1}]: Connecting to device --> DONE'.format(self.target['name'], 'Connect'))

        except (RuntimeError, OSError) as err:
            c.cso_logger.info(
                '[{0}][{1}]: Connecting to device failed: {2}'.format(self.target['name'], 'Connect', err))
            message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target['uuid'],
                       'status': str(err)}
            self.emit_message(message=message)
            return False

        message = {'action': 'update_task_status', 'task': 'Connect', 'uuid': self.target['uuid'],
                   'status': 'Done'}
        self.emit_message(message=message)
        return True

    def disconnect(self):
        """
        Disconnect complete telnet session
        :return:
        """

        self.ws.task = 'Disconnect'

        c.cso_logger.info('[{0}][{1}]: Disconnect from device'.format(self.target['name'], 'Disconnect'))
        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target['uuid'],
                   'status': 'Disconnecting...'}
        self.emit_message(message=message)

        if self.isRebooted:
            c.cso_logger.info(
                '[{0}][{1}]: Disconnect from device after reboot'.format(self.target['name'], 'Disconnect'))
            self.isRebooted = False
            self.isConnected = False
            # Closing telnet connection
            self._dev.close(skip_logout=True)
            c.cso_logger.info(
                '[{0}][{1}]: Disconnect from device after reboot --> DONE'.format(self.target['name'], 'Disconnect'))

        else:
            if self.target['model'] == 'nfx':
                c.cso_logger.info(
                    '[{0}][{1}]: Logout from NFX shell...'.format(self.target['name'], 'Disconnect'))
                self._dev._tty._tn.write('exit'.encode("ascii") + b"\r\n")
                self._dev.close(skip_logout=True)
                c.cso_logger.info(
                    '[{0}][{1}]: Logout from NFX shell --> DONE'.format(self.target['name'], 'Disconnect'))
            elif self.isNetConf:
                c.cso_logger.info(
                    '[{0}][{1}]: Terminate netconf session...'.format(self.target['name'], 'Disconnect'))
                self.disconnect_netconf()
                c.cso_logger.info(
                    '[{0}][{1}]: Terminate netconf session --> DONE'.format(self.target['name'], 'Disconnect'))
                self.isNetConf = False
                c.cso_logger.info(
                    '[{0}][{1}]: Logout from shell...'.format(self.target['name'], 'Disconnect'))
                self._dev._tty._tn.write('exit'.encode("ascii") + b"\r\n")
                c.cso_logger.info(
                    '[{0}][{1}]: Logout from shell --> DONE'.format(self.target['name'], 'Disconnect'))
                self._dev.close(skip_logout=True)
            else:
                c.cso_logger.info(
                    '[{0}][{1}]: Logout from shell...'.format(self.target['name'], 'Disconnect'))
                self._dev._tty._tn.write('exit'.encode("ascii") + b"\r\n")
                c.cso_logger.info(
                    '[{0}][{1}]: Logout from shell --> DONE'.format(self.target['name'], 'Disconnect'))
                self._dev.close(skip_logout=True)

        c.cso_logger.info('[{0}][{1}]: Disconnect from device --> DONE'.format(self.target['name'], 'Disconnect'))

        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target['uuid'],
                   'status': 'Done'}
        self.emit_message(message=message)

    def connect_netconf(self):
        self.ws.task = 'Connect'

        try:
            c.cso_logger.info('[{0}][{1}]: Connect to netconf session'.format(self.target['name'], 'Connect'))
            self._dev._tty.nc.open(True)
            self.isNetConf = True
            c.cso_logger.info('[{0}][{1}]: Connect to netconf session --> DONE'.format(self.target['name'], 'Connect'))
            return True

        except (ConnectionResetError, RuntimeError) as err:
            c.cso_logger.info(
                '[{0}][{1}]: Connect netconf session failed: {2}'.format(self.target['name'], 'Connect', err))
            return False

    def disconnect_netconf(self):
        self.ws.task = 'Disconnect'
        c.cso_logger.info('[{0}][{1}]: Disconnect netconf session'.format(self.target['name'], 'Disconnect'))
        self._dev._tty.nc.close()
        self.isNetConf = False
        c.cso_logger.info('[{0}][{1}]: Disconnect netconf session --> DONE'.format(self.target['name'], 'Disconnect'))

    def run(self):

        for task in self.target['tasks']:

            if self.status:

                if task['name'] == 'Connect':
                    self.status = self.connect()

                elif task['name'] == 'Render':
                    _status, _data = self.render(task=task)

                    if _status:
                        self.status = self.push(task=task, data=_data)
                    else:
                        self.status = _status
                        break

                elif task['name'] == 'Zerorize':
                    self.status = self.zeroize(task=task)

                elif task['name'] == 'Configure':
                    _status, _data = self.pull(task=task)

                    if _status:
                        self.status = self.configure(task=task, data=_data.decode('utf-8'))
                    else:
                        break

                elif task['name'] == 'Copy':
                    self.status = self.copy(task=task)
                elif task['name'] == 'License':
                    self.status = self.license(task=task)
                elif task['name'] == 'Reboot':
                    self.status = self.reboot(task=task)
                elif task['name'] == 'Disconnect':
                    self.disconnect()

                message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'],
                           'msg': self.gen_task_done_message(task=task)}
                self.emit_message(message=message)
            else:
                c.cso_logger.info('[{0}][{1}]: Error in last task.'.format(self.target['name'], task['name']))
                break

        if self.status:
            self.results[self.target['name']] = True
            self.results['overall'] = True
            c.cso_logger.info(
                '[{0}][Run]: Deploy use case <{1}> --> DONE'.format(self.target['name'], self.use_case_name))
        else:
            self.results[self.target['name']] = False
            self.results['overall'] = False
            c.cso_logger.info(
                '[{0}][Run]: Deploy use case <{1}> --> FAILED'.format(self.target['name'], self.use_case_name))

    def render(self, task=None):
        c.cso_logger.info(
            '[{0}][{1}]: Render configuration'.format(self.target['name'], task['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Render template'}
        self.emit_message(message=message)

        try:
            env = Environment(autoescape=False,
                              loader=FileSystemLoader(self.use_case_path), trim_blocks=True, lstrip_blocks=True)

            template = env.get_template(task['template'])

        except (TemplateNotFound, IOError) as err:
            c.cso_logger.info(
                '[{0}][{1}]: Render configuration failed: {2}'.format(self.target['name'], task['name'], err))
            return False, err

        with open('{0}/{1}'.format(self.use_case_path, task['template_data'])) as fd:
            data = yaml.safe_load(fd)
            config = template.render(data)

        message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'],
                   'msg': config + '\n'}
        self.emit_message(message=message)
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)
        c.cso_logger.info(
            '[{0}][{1}]: Render configuration --> DONE'.format(self.target['name'], task['name']))

        return True, config

    def push(self, task=None, data=None):
        c.cso_logger.info('[{0}][{1}]: Push configuration to git'.format(self.target['name'], task['name']))
        status = self.authenticate()

        if status:

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': 'Push config'}
            self.emit_message(message=message)

            try:

                project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
                c.cso_logger.info(
                    '[{0}][{1}]: Push configuration to git --> DONE'.format(self.target['name'], task['name']))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                           'status': 'Done'}
                self.emit_message(message=message)

            except (GitlabConnectionError, GitlabError) as gle:
                c.cso_logger.info(
                    '[{0}][{1}]:Failed to get project with error: <{2}>'.format(self.target['name'], task['name'], gle))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                           'status': str(gle)}
                self.emit_message(message=message)
                return False

            _status, _data = self.pull(task=task)
            file_path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], self.target['name'])

            if _status:
                c.cso_logger.info('[{0}][{1}]: Updating file <{0}>'.format(self.target['name'], task['name']))

                file_body = {
                    "branch": c.CONFIG['git_branch'],
                    "content": data,
                    "commit_message": "Device config {0}".format(self.target['name'])
                }

                try:

                    _data = project.files.update(file_path=file_path, new_data=file_body)
                    c.cso_logger.info(
                        '[{0}][{1}]: Updating file <{0}> --> DONE'.format(self.target['name'], task['name']))
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': 'Done'}
                    self.emit_message(message=message)
                    return True, _data

                except (GitlabConnectionError, GitlabError, GitlabHttpError) as gle:
                    c.cso_logger.info(
                        '[{0}][{1}]: Failed to update device template with error: <{2}>'.format(self.target['name'],
                                                                                                task['name'], gle))
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': str(gle)}
                    self.emit_message(message=message)
                    return False

            else:
                c.cso_logger.info('[{0}][{1}]: Creating new file <{0}>'.format(self.target['name'], task['name']))

                file_body = {
                    "file_path": file_path,
                    "branch": c.CONFIG['git_branch'],
                    "content": data,
                    "commit_message": "Device config {0}".format(self.target['name'])
                }

                try:

                    _data = project.files.create(file_body)
                    c.cso_logger.info(
                        '[{0}][{1}]: Creating new file <{0}> --> DONE'.format(self.target['name'], task['name']))
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': 'Done'}
                    self.emit_message(message=message)
                    return True, _data

                except (GitlabConnectionError, GitlabError) as gle:
                    c.cso_logger.info(
                        '[{0}][{1}]: Failed to create device template with error: <{2}>'.format(self.target['name'],
                                                                                                task['name'], gle))
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': str(gle)}
                    self.emit_message(message=message)
                    return False

    def update(self, task=None, data=None):
        c.cso_logger.info(
            '[{0}][{1}]: Update device <{0}> configuration in git'.format(self.target['name'], task['name']))
        status = self.authenticate()

        if status:

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': task['uuid'],
                       'status': 'Pushing config'}
            self.emit_message(message=message)

            try:

                project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
                # file_path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], self.target['name'])

                file_body = {
                    "branch": c.CONFIG['git_branch'],
                    "content": data.decode('utf-8'),
                    "commit_message": "Device config {0}".format(self.target['name'])
                }

            except (GitlabConnectionError, GitlabError) as gle:
                return False, 'Failed to get project with error: <0>'.format(gle.message)

            try:
                _response = project.files.update(file_body)
                c.cso_logger.info(
                    '[{0}][{1}]: Update configuration in git --> DONE'.format(self.target['name'], task['name']))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': task['uuid'], 'status': 'Done'}
                self.emit_message(message=message)
                return True, _response

            except GitlabCreateError as gce:
                return False, 'Failed to update template data with error: <{0}>'.format(gce)

    def pull(self, task=None):
        c.cso_logger.info(
            '[{0}][{1}]: Pull file <{0}> from git for use case <{2}>'.format(self.target['name'], task['name'],
                                                                             self.use_case_name))

        try:
            project = self.gl.projects.get('{0}'.format(c.CONFIG['git_repo_url']))
            _path = '{0}/{1}/{2}'.format(self.use_case_name, c.CONFIG['git_device_conf_dir'], self.target['name'])

            try:
                f = project.files.get(file_path=_path, ref='master')
                c.cso_logger.info(
                    '[{0}][{1}]: Pull file <{0}> from git for use case <{2}> --> DONE'.format(self.target['name'],
                                                                                              task['name'],
                                                                                              self.use_case_name))
                return True, f.decode()

            except GitlabError as ge:
                c.cso_logger.info(
                    '[{0}][{1}]: Pull file from git failed with error: {2}'.format(self.target['name'], task['name'],
                                                                                   ge))
                message = {'action': 'update_task_status', 'task': task['name'],
                           'uuid': self.target['uuid'],
                           'status': str(ge)}
                self.emit_message(message=message)
                return False, 'Pull file from git failed with error: <{0}>'.format(ge)

        except (GitlabConnectionError, GitlabError) as gle:
            c.cso_logger.info(
                '[{0}][{1}]: Failed to get project with error: <{2}>'.format(self.target['name'], task['name'],
                                                                             gle))
            message = {'action': 'update_task_status', 'task': task['name'],
                       'uuid': self.target['uuid'],
                       'status': str(gle)}
            self.emit_message(message=message)
            return False, 'Failed to get project with error: <{0}>'.format(gle.message)

    def zeroize(self, task=None):
        c.cso_logger.info('[{0}][{1}]: Initialize zerorize device'.format(self.target['name'], task['name']))
        self.ws.task = task['name']
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Zeroize initializing'}
        self.emit_message(message=message)

        if not self.isNetConf:
            self.connect_netconf()

        resp = self._dev.zeroize()
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Zeroize running'}
        self.emit_message(message=message)
        message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'], 'msg': resp}
        self.emit_message(message=message)

        while True:

            try:
                raw_data = self._dev._tty._tn.read_until(b"\r\n")
                data = self.escape_ansi(line=raw_data.decode().strip())

            except EOFError as err:
                c.cso_logger.info('[{0}][{1}]: Telnet session error {2}'.format(self.target['name'], task['name'], err))
                return False

            c.cso_logger.info('[{0}][{1}]: {2}'.format(self.target['name'], task['name'],
                                                       self.escape_ansi(line=data)))
            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'],
                       'msg': data}
            self.emit_message(message=message)

            if self.target['model'] == 'nfx':

                if data in c.TERM_STRINGS_QFX:
                    self.isRebooted = True
                    self.isZeroized = True
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': 'Done'}
                    self.emit_message(message=message)
                    c.cso_logger.info('[{0}][{1}]: Zerorize device --> DONE'.format(self.target['name'], task['name']))
                    message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target['uuid'],
                               'status': 'waiting'}
                    self.emit_message(message=message)

                    return True
            else:
                if data in c.TERM_STRINGS:
                    self.isRebooted = True
                    self.isZeroized = True
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': 'Done'}
                    self.emit_message(message=message)
                    c.cso_logger.info('[{0}][{1}]: Zerorize device --> DONE'.format(self.target['name'], task['name']))
                    message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target['uuid'],
                               'status': 'waiting'}
                    self.emit_message(message=message)

                    return True

            time.sleep(0.2)

    def configure(self, task=None, data=None):
        self.ws.task = task['name']
        c.cso_logger.info('[{0}][{1}]: Commit configuration on device'.format(self.target['name'], task['name']))
        message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'],
                   'msg': data}
        self.emit_message(message=message)

        if not self.isConnected:
            self.wait_for_daeomons(task=task)
            self.connect()

        if not self.isNetConf:
            self.connect_netconf()

        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Connecting...'}
        self.emit_message(message=message)
        cu = Config(self._dev)

        if self.target['model'] == 'qfx' and self.isZeroized:
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': 'Device with auto-image-upgrade. Stopping that...'}
            self.emit_message(message=message)
            c.cso_logger.info(
                '[{0}][{1}]: Device with auto-image-upgrade. Stopping that...'.format(self.target['name'],
                                                                                      task['name']))
            try:
                c.cso_logger.info(
                    '[{0}][{1}]: Device with auto-image-upgrade. Loading configuration'.format(self.target['name'],
                                                                                               task['name']))
                cu.load(c.cfg_aiu, format="text", merge=True)
                c.cso_logger.info(
                    '[{0}][{1}]: Device with auto-image-upgrade. Loading configuration --> DONE'.format(
                        self.target['name'],
                        task['name']))

            except (ConfigLoadError, RuntimeError, ConnectClosedError) as err:
                c.cso_logger.info(
                    '[{0}][{1}]: Error loading configuration: {2}'.format(self.target['name'], task['name'], err))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                           'status': str(err)}
                self.emit_message(message=message)
                self.disconnect()

                return False

            try:
                c.cso_logger.info(
                    '[{0}][{1}]: Device with auto-image-upgrade. Commit configuration'.format(self.target['name'],
                                                                                              task['name']))
                cu.commit(confirm=task['confirm'], sync=task['sync'])
                c.cso_logger.info(
                    '[{0}][{1}]: Device with auto-image-upgrade. Commit configuration --> DONE'.format(
                        self.target['name'],
                        task['name']))

            except CommitError as err:
                c.cso_logger.info(
                    '[{0}][{1}]: Error committing configuration: {2}'.format(self.target['name'], task['name'], err))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                           'status': str(err)}
                self.emit_message(message=message)
                self.disconnect()

                return False

            c.cso_logger.info(
                '[{0}][{1}]: Device with auto-image-upgrade. Stopping auto-image-upgrade --> DONE'.format(
                    self.target['name'],
                    task['name']))

        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Load config'}
        self.emit_message(message=message)

        try:
            c.cso_logger.info('[{0}][{1}]: Device loading configuration'.format(self.target['name'], task['name']))
            cu.load(data, merge=task['merge'], overwrite=task['override'], update=task['update'], format="text")
            c.cso_logger.info(
                '[{0}][{1}]: Device loading configuration --> DONE'.format(self.target['name'], task['name']))

        except (ConfigLoadError, RuntimeError, ConnectClosedError) as err:
            c.cso_logger.info(
                '[{0}][{1}]: Error loading configuration: {2}'.format(self.target['name'], task['name'], err))
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': str(err)}
            self.emit_message(message=message)
            self.disconnect()

            return False

        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Commit config'}
        self.emit_message(message=message)

        try:
            c.cso_logger.info('[{0}][{1}]: Device commit configuration'.format(self.target['name'], task['name']))
            cu.commit(confirm=task['confirm'], sync=task['sync'])
        # NetConf session gets dropped when override config with NetConf service enabled. So we need to catch up here
        # and reconnect.
        except XMLSyntaxError as xse:
            c.cso_logger.info('[{0}][{1}]: {2}'.format(self.target['name'], task['name'], xse))
            self.disconnect()
            time.sleep(3)
            self.connect()

        except CommitError as err:
            c.cso_logger.info(
                '[{0}][{1}]: Error committing configuration: {2}'.format(self.target['name'], task['name'], err))
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': 'Error committing configuration'}
            self.emit_message(message=message)
            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'],
                       'msg': str(err)}
            self.emit_message(message=message)
            self.disconnect()

            return False

        c.cso_logger.info(
            '[{0}][{1}]: Commit configuration on device --> DONE'.format(self.target['name'], task['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'], 'status': 'Done'}
        self.emit_message(message=message)

        return True

    def copy(self, task=None):
        self.ws.task = task['name']

        if not self.isConnected:
            self.wait_for_daeomons(task=task)
            self.connect()

        if self.isNetConf:
            self.disconnect_netconf()

        for item in list(zip(task['src'], task['dst'])):

            c.cso_logger.info(
                '[{0}][{1}]: Copy file <{2}> to <{3}>'.format(self.target['name'], task['name'], item[0], item[1]))

            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': 'Copy file {0}'.format(item[0])}
            self.emit_message(message=message)
            _file = '{0}/{1}'.format(c.CONFIG['tmp_dir'], item[0])
            self._dev._tty._tn.write('cat > {0} << EOF'.format(item[1]).encode('ascii') + b"\r\n")
            self._dev._tty._tn.read_until(b"\r\n")

            with open(_file, 'r') as fd:
                total_lines = sum(1 for _ in open(_file, 'rb'))
                line_count = 0

                for line in fd:
                    self._dev._tty._tn.write(line.encode("ascii"))
                    self._dev._tty._tn.read_until(b"\r\n")

                    line_count += 1
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': 'Copy file {0} ({1}%)'.format(item[0],
                                                                       int(100 * (line_count / float(total_lines))))}
                    self.emit_message(message=message)
                    message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'],
                               'msg': str(line.encode("ascii"), 'utf-8')}
                    self.emit_message(message=message)
                    time.sleep(1)

            c.cso_logger.info(
                '[{0}][{1}]: Copy file <{2}> to <{3}> --> DONE'.format(self.target['name'], task['name'], task['src'],
                                                                       task['dst']))
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': 'Done'}
            self.emit_message(message=message)

        return True

    def license(self, task=None):
        self.ws.task = task['name']

        c.cso_logger.info(
            '[{0}][{1}]: Install license <{2}>'.format(self.target['name'], task['name'], task['file']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Adding license...'}
        self.emit_message(message=message)

        if not self.isConnected:
            self.wait_for_daeomons(task=task)
            self.connect()

        if self.isNetConf:
            self.disconnect_netconf()

        command = 'cli -c "request system license add {0}"'.format(task['file'])
        self._dev._tty._tn.write(command.encode("ascii") + b"\r\n")

        while True:
            try:
                data = self._dev._tty._tn.read_until(b"\r\n")

            except EOFError as err:
                c.cso_logger.info('[{0}][{1}]: Telnet session error {2}'.format(self.target['name'], task['name'], err))
                return False

            c.cso_logger.info('[{0}][{1}]: {2}'.format(self.target['name'], task['name'], str(data, 'utf-8').strip()))
            _data = data.decode('utf-8').strip()
            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'],
                       'msg': str(data, 'utf-8')}
            self.emit_message(message=message)

            re_pattern = re.compile(r'add license failed \(.*? errors\)')
            term_str = re_pattern.match(_data)

            if term_str:
                c.cso_logger.info('[{0}][{1}]: Adding license --> FAILED'.format(self.target['name'], task['name']))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                           'status': 'Failed'}
                self.emit_message(message=message)
                return False

            elif _data == 'add license complete (no errors)':
                c.cso_logger.info('[{0}][{1}]: Adding license --> DONE'.format(self.target['name'], task['name']))
                message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                           'status': 'Done'}
                self.emit_message(message=message)
                return True

            time.sleep(0.2)

    def reboot(self, task=None):
        self.ws.task = task['name']

        c.cso_logger.info('[{0}][{1}]: Rebooting device...'.format(self.target['name'], task['name'], ))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Rebooting...'}
        self.emit_message(message=message)

        if not self.isConnected:
            self.wait_for_daeomons(task=task)
            self.connect()

        if not self.isNetConf:
            self.connect_netconf()

        message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target['uuid'],
                   'status': 'waiting'}
        self.emit_message(message=message)

        try:
            resp = self._dev.rpc.request_reboot()
            c.cso_logger.info('[{0}][{1}]: {2}'.format(self.target['name'], task['name'], resp))

        except BrokenPipeError as bpErr:
            c.cso_logger.info('[{0}][{1}]: Reboot failed: {2}'.format(self.target['name'], task['name'], bpErr))
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': str(bpErr)}
            self.emit_message(message=message)
            return False

        except RpcError as rpcErr:
            c.cso_logger.info('[{0}][{1}]: Reboot failed: {2}'.format(self.target['name'], task['name'], rpcErr))
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': str(rpcErr.message)}
            self.emit_message(message=message)
            self.disconnect()
            return False

        while True:

            try:
                raw_data = self._dev._tty._tn.read_until(b"\r\n")
                data = self.escape_ansi(line=raw_data.decode().strip())

            except EOFError as err:
                c.cso_logger.info('[{0}][{1}]: Telnet session error {2}'.format(self.target['name'], task['name'], err))
                return False

            c.cso_logger.info('[{0}][{1}]: {2}'.format(self.target['name'], task['name'],
                                                       self.escape_ansi(line=data)))
            message = {'action': 'update_session_output', 'task': task['name'], 'uuid': self.target['uuid'],
                       'msg': data}
            self.emit_message(message=message)

            if self.target['model'] == 'nfx':

                if data in c.TERM_STRINGS_QFX:
                    self.isRebooted = True
                    self.isZeroized = True
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': 'Done'}
                    self.emit_message(message=message)
                    c.cso_logger.info('[{0}][{1}]: Reboot device --> DONE'.format(self.target['name'], task['name']))
                    message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target['uuid'],
                               'status': 'waiting'}
                    self.emit_message(message=message)
                    return True
            else:

                re_pattern = re.compile(self.target['name'] + ' ' + r'\(tty.*\)')
                term_str = re_pattern.match(data)

                if term_str:
                    self.isRebooted = True
                    c.cso_logger.info('[{0}][{1}]: Rebooting device --> DONE'.format(self.target['name'], task['name']))
                    message = {'action': 'update_task_status', 'task': 'Disconnect', 'uuid': self.target['uuid'],
                               'status': 'waiting'}
                    self.emit_message(message=message)
                    message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                               'status': 'Done'}
                    self.emit_message(message=message)
                    return True

            time.sleep(0.2)

    def wait_for_daeomons(self, task=None):
        c.cso_logger.info(
            "[{0}][{1}]: Device was rebooted. Waiting for daemons to be ready...".format(self.target['name'],
                                                                                         task['name']))
        message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                   'status': 'Waiting for daemons to be ready...'}
        self.emit_message(message=message)
        # adding some timeout for telnet session to close properly. Need a better approach here!
        mark_start = datetime.now()

        if self.target['model'] == 'qfx' or self.target['model'] == 'nfx':
            timeout = 20
        else:
            timeout = 120

        mark_end = mark_start + timedelta(seconds=timeout)

        while datetime.now() < mark_end:
            timeout -= 1
            message = {'action': 'update_task_status', 'task': task['name'], 'uuid': self.target['uuid'],
                       'status': 'Waiting for daemons to be ready... {0}'.format(timeout)}

            self.emit_message(message=message)
            c.cso_logger.info(
                "[{0}][{1}]: Device was rebooted. Waiting for daemons to be ready <{2}>".format(self.target['name'],
                                                                                                task['name'],
                                                                                                timeout))
            time.sleep(1)

    def gen_task_done_message(self, task=None):
        header = '{0} TASK {1} DONE {2}'.format(15 * '#', task['name'], 15 * '#')
        return header

    def escape_ansi(self, line=None):
        ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', line)

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
