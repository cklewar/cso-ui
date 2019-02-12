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
import os
import socket
import cherrypy
import six
import pprint
import json
import threading
import random

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ruamel.yaml import YAML
from lib.auth import AuthController, require, member_of, name_is
from ws4py.client.threadedclient import WebSocketClient
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from lib.driver._ansible import AnsibleDriver
from lib.driver._saltstack import SaltDriver
from lib.driver._pyez import PyEzDriver


def cors_tool():
    req_head = cherrypy.request.headers
    resp_head = cherrypy.response.headers

    resp_head['Access-Control-Allow-Origin'] = req_head.get('Origin', '*')
    resp_head['Access-Control-Expose-Headers'] = 'GET, POST'
    resp_head['Access-Control-Allow-Credentials'] = 'true'

    if cherrypy.request.method == 'OPTIONS':
        ac_method = req_head.get('Access-Control-Request-Method', None)

        allowed_methods = ['GET', 'POST']
        allowed_headers = [
            'Content-Type',
            'X-Auth-Token',
            'X-Requested-With',
        ]

        if ac_method and ac_method in allowed_methods:
            resp_head['Access-Control-Allow-Methods'] = ', '.join(allowed_methods)
            resp_head['Access-Control-Allow-Headers'] = ', '.join(allowed_headers)
            resp_head['Connection'] = 'keep-alive'
            resp_head['Access-Control-Max-Age'] = '1400'

        cherrypy.response.body = ''
        cherrypy.response.state = 200
        cherrypy.serving.request.handler = None

        if cherrypy.request.config.get('tools.sessions.on', False):
            cherrypy.session['token'] = True
        return True


class WSClient(WebSocketClient):
    def __init__(self, name=None, url=None):
        super(WSClient, self).__init__(url=url, protocols=['http-only', 'chat'])
        self._clientName = name

    def opened(self):
        pass
        # print('opened connection')

    def closed(self, code, reason=None):
        if code != 1000:
            print('WSClient: Connection closed. Code <{0}>, Reason: <{1}>'.format(code, reason))

    def received_message(self, m):
        print('WSClient: Client received data. That\'s not what we want at this stage')


class RestrictedArea(object):
    # all methods in this controller (and sub controllers) is
    # open only to members of the admin group

    _cp_config = {
        'auth.require': [member_of('admin')]
    }

    @cherrypy.expose
    def index(self):
        return """This is the admin only area."""


class Root(object):

    def __init__(self, driver=None):
        self.driver = driver

    _cp_config = {
        'tools.sessions.on': True,
        'tools.auth.on': True
    }

    auth = AuthController()
    restricted = RestrictedArea()

    @cherrypy.expose
    @require()
    def index(self):
        try:
            env = Environment(loader=FileSystemLoader('templates'))
            tmpl = env.get_template('index.html', 'r')
            data = dict()
            data['cards'] = dict()
            # data['cards'] = self.driver.load_use_cases()[1]

            data['protocol'] = c.CONFIG["ws_client_protocol"]
            data['ip'] = c.CONFIG["ws_client_ip"]
            data['port'] = c.CONFIG["ws_client_port"]
            data['clientname'] = "Client%d" % random.randint(0, 100)
            data['demo_ref_doc_url'] = c.CONFIG['demo_ref_doc_url']
            data['jtac_url'] = c.CONFIG['jtac_url']

            with open("config/items.yml", 'r') as fp:
                yaml = YAML(typ='rt')
                data['cards'] = yaml.load(fp)

            index = tmpl.render(data=data)
            return index

        except (TemplateNotFound, IOError) as ioe:

            error = '{0}'.format(ioe.filename if ioe.filename else ioe)
            print(error)
            return error

    @cherrypy.expose
    def ws(self, clientname):
        cherrypy.request.ws_handler.clientname = clientname
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))


@cherrypy.expose
@require()
class Cards(object):

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, action=None):

        if action == 'add':
            data = cherrypy.request.json
            new_card = dict()
            _tmp = None
            yaml = YAML(typ='rt')

            with open('config/items.yml', 'r') as ifp:

                cards = yaml.load(ifp)
                card_name = None

                for item in data:
                    _tmp = [item[k] for k in item]

                    if _tmp[0] == 'name':
                        card_name = _tmp[1]
                    else:
                        new_card.update({_tmp[0]: _tmp[1]})

                new_card['delete'] = True
                cards[card_name] = new_card

            with open('config/items.yml', 'w+') as ofp:
                yaml.dump(cards, ofp)

            env = Environment(loader=FileSystemLoader('templates'))
            tmpl = env.get_template('item.html', 'r')
            card = tmpl.render(card_id=card_name, card=new_card)

            return card

        elif action == 'delete':
            data = cherrypy.request.json

            with open('config/items.yml', 'r') as ifp:
                yaml = YAML(typ='rt')
                cards = yaml.load(ifp)
                del cards[data]

            with open('config/items.yml', 'w') as ofp:
                yaml.dump(cards, ofp)

            return True

        elif action == 'save':

            data = cherrypy.request.json

            with open('config/items.yml', 'r') as ifp:
                yaml = YAML(typ='rt')
                cards = yaml.load(ifp)

                update_card = cards[data['cardId']]
                update_card['title'] = data['title']
                update_card['playbook'] = data['playbook']
                update_card['directory'] = data['directory']
                update_card['description'] = data['description']
                cards[data['cardId']] = update_card

            with open('config/items.yml', 'w') as ofp:
                yaml.dump(cards, ofp)

            return True


@cherrypy.expose
@require()
class Upload(object):

    @cherrypy.tools.json_out()
    def POST(self, **kwargs):

        with open('static/images/{0}'.format(kwargs['imageFile'].filename), 'wb') as fp:
            size = 0
            while True:
                data = kwargs['imageFile'].file.read(8192)
                if not data:
                    break
                size += len(data)
                fp.write(data)
        return {"status": size}


@cherrypy.expose
@require()
class Deploy(object):

    def __init__(self, driver=None):
        self.driver = driver

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):

        action = cherrypy.request.json['action']
        use_case_name = cherrypy.request.json['use_case_name']

        if action == 'fetch':
            ret = self.driver.fetch()
            return ret
            #return {'result': 'OK'}

        if action == 'run':

            yaml = YAML(typ='rt')

            with open('config/items.yml', 'r') as ifp:
                use_cases = yaml.load(ifp)
                use_case = use_cases[use_case_name]

            ret = self.driver.run(use_case_name=use_case_name, use_case_data=use_case)

            #for item in ret:
            #    print(item)

            return True


class Api(object):

    def __init__(self, driver=None):
        cherrypy.tools.cors_tool = cherrypy.Tool('before_request_body', cors_tool, name='cors_tool', priority=50)
        self.driver = driver
        self.driver.load_settings()
        self.url_map = {'cards': Cards, 'upload': Upload, 'deploy': Deploy}
        self._setattr_url_map()

    def _setattr_url_map(self):
        """
        Set an attribute on the local instance for each key/val in url_map
        """

        for url, cls in six.iteritems(self.url_map):
            if url == 'deploy':
                setattr(self, url, cls(driver=self.driver))
            else:
                setattr(self, url, cls())


class WSPlugin(WebSocketPlugin):
    def __init__(self, bus):
        WebSocketPlugin.__init__(self, bus)
        self.ws_servers_lock = threading.Lock()
        self.ws_clients_lock = threading.Lock()
        self.ws_servers = dict()
        self.ws_clients = dict()

    def start(self):
        WebSocketPlugin.start(self)
        self.bus.subscribe('add-server', self.add_server)
        self.bus.subscribe('get-server', self.get_server)
        self.bus.subscribe('del-server', self.del_server)
        self.bus.subscribe('add-client', self.add_client)
        self.bus.subscribe('get-client', self.get_client)
        self.bus.subscribe('del-client', self.del_client)
        self.bus.subscribe('check-client', self.check_client_exists)
        self.bus.subscribe('get-clients', self.get_clients)

    def stop(self):
        WebSocketPlugin.stop(self)
        self.bus.unsubscribe('add-server', self.add_server)
        self.bus.unsubscribe('get-server', self.get_server)
        self.bus.unsubscribe('del-server', self.del_server)
        self.bus.unsubscribe('add-client', self.add_client)
        self.bus.unsubscribe('get-client', self.get_client)
        self.bus.unsubscribe('del-client', self.del_client)
        self.bus.unsubscribe('check-client', self.check_client_exists)
        self.bus.unsubscribe('get-clients', self.get_clients)

    def add_server(self, name, websocket):

        self.ws_servers_lock.acquire()
        try:
            self.ws_servers[name] = websocket
        finally:
            self.ws_servers_lock.release()

    def get_server(self, name):
        return self.ws_servers[name]

    def del_server(self, name):

        self.ws_servers_lock.acquire()

        try:
            if name in self.ws_servers:
                del self.ws_servers[name]
            else:
                pass

        finally:
            self.ws_servers_lock.release()

    def add_client(self, name, websocket):

        self.ws_clients_lock.acquire()
        try:
            self.ws_clients[name] = websocket
        finally:
            self.ws_clients_lock.release()

    def get_client(self, name):
        if name in self.ws_clients:
            return self.ws_clients[name]
        else:
            return None

    def del_client(self, name):

        self.ws_clients_lock.acquire()

        try:
            if name in self.ws_clients:
                del self.ws_clients[name]
            else:
                pass

        finally:
            self.ws_clients_lock.release()

    def check_client_exists(self, name):

        if name in self.ws_clients:
            return True
        else:
            return False

    def get_clients(self):
        return self.ws_clients


class WSHandler(WebSocket):
    tmp_client = None

    def opened(self):

        if self.clientname != 'server':

            if cherrypy.engine.publish('check-client', self.clientname)[0]:
                pass
            else:
                cherrypy.engine.publish('add-client', self.clientname, self)
                WSHandler.tmp_client = self.clientname
        else:
            cherrypy.engine.publish('add-server', self.clientname, self)

    def received_message(self, m):

        try:
            _data = json.loads(m.data)

        except ValueError as ve:
            print(ve)
            return None

        all_clients = cherrypy.engine.publish('get-clients')

        for _clients in all_clients:
            for _client_name, client_ws in _clients.items():
                if not client_ws.terminated:
                    client_ws.send(m.data)

    def closed(self, code, reason='Going away'):

        if code == 1000:
            pass
        elif code == 1006 and reason == 'Going away':
            cherrypy.engine.publish('del-client', self.clientname)
        else:
            pass


if __name__ == '__main__':

    with open('config/config.yml', 'r') as fp:
        _config = fp.read()
        yaml = YAML(typ='safe')
        c.CONFIG = yaml.load(_config)

    print('Starting UI at http(s)://{0}:{1}'.format(c.CONFIG['UI_ADDRESS'], c.CONFIG['UI_PORT']))
    cherrypy.config.update({'log.screen': True,
                            'log.access_file': '',
                            'log.error_file': '',
                            'engine.autoreload_on': False,
                            'server.socket_host': c.CONFIG['UI_ADDRESS'],
                            'server.socket_port': c.CONFIG['UI_PORT'],
                            'server.max_request_body_size': 0,
                            }, )

    if c.CONFIG['IS_SSL']:
        ssl_config = {
            'server.ssl_module': 'builtin',
            'server.ssl_certificate': 'config/ssl/cert.pem',
            'server.ssl_private_key': 'config/ssl/privkey.pem',
            # 'server.ssl_certificate_chain': 'bundle.crt'
        }
        cherrypy.config.update(ssl_config)

    ui_conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },

        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static',
        },
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.protocols': ['cso_ui'],
            'tools.websocket.handler_cls': WSHandler
        }
    }

    api_conf = {

        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')],
            'tools.sessions.on': True,
            'tools.cors_tool.on': True,
        },
    }

    if c.CONFIG['DEMONIZE']:
        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

    _driver = None

    cso_ws_url = '{0}://{1}:{2}/ws'.format(c.CONFIG['ws_client_protocol'], c.CONFIG['ws_client_ip'],
                                           c.CONFIG['ws_client_port'])
    url = '{0}?clientname=server'.format(cso_ws_url)
    print(url)
    ws_client = WSClient(name='server', url=url)

    if c.CONFIG['driver'] == c.DRIVER_SALTSTACK:
        _driver = SaltDriver(ws_client=ws_client)
    elif c.CONFIG['driver'] == c.DRIVER_ANSIBLE:
        _driver = AnsibleDriver(ws_client=ws_client)
    elif c.CONFIG['driver'] == c.DRIVER_PYEZ:
        _driver = PyEzDriver(ws_client=ws_client)

    if _driver:
        WSPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()
        cherrypy.tree.mount(Root(driver=_driver), '/', config=ui_conf)
        cherrypy.tree.mount(Api(driver=_driver), '/api', config=api_conf)
        cherrypy.engine.start()
        cherrypy.engine.block()
