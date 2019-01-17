#
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
#
# Copyright (c) 2018 Juniper Networks, Inc.
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

import constants as c
import cherrypy
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

SESSION_KEY = '_cp_username'


def check_credentials(username, password):
    if username in c.ADMIN_USERS and password == c.ADMIN_USER_PW:
        return None
    else:
        return u"Incorrect username or password."


def check_auth(*args, **kwargs):
    conditions = cherrypy.request.config.get('auth.require', None)

    if conditions is not None:
        username = cherrypy.session.get(SESSION_KEY)
        if username:
            cherrypy.request.login = username
            for condition in conditions:
                # A condition is just a callable that returns true or false
                if not condition():
                    raise cherrypy.HTTPRedirect("/auth/login")
        else:
            raise cherrypy.HTTPRedirect("/auth/login")


cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)


def require(*conditions):

    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f

    return decorate


def member_of(groupname):
    def check():
        # replace with actual check if <username> is in <groupname>
        return cherrypy.request.login == 'admin' and groupname == 'admin'

    return check


def name_is(reqd_username):
    return lambda: reqd_username == cherrypy.request.login


def any_of(*conditions):
    """Returns True if any of the conditions match"""

    def check():
        for c in conditions:
            if c():
                return True
        return False

    return check


def all_of(*conditions):
    """Returns True if all of the conditions match"""

    def check():
        for c in conditions:
            if not c():
                return False
        return True

    return check


class AuthController(object):

    def on_login(self, username):
        """Called on successful login"""

    def on_logout(self, username):
        """Called on logout"""

    def get_loginform(self, username, msg="Enter login information", from_page="/"):

        try:
            env = Environment(loader=FileSystemLoader('templates'))
            tmpl = env.get_template('login.html', 'r')
            data = dict()
            data['from_page'] = from_page
            data['msg'] = msg
            data['username'] = username
            login = tmpl.render(data=data)
            return login

        except (TemplateNotFound, IOError) as ioe:

            error = '{0}'.format(ioe.filename if ioe.filename else ioe)
            print(error)
            return error

    @cherrypy.expose
    def login(self, username=None, password=None, from_page="/"):
        if username is None or password is None:
            return self.get_loginform("", from_page=from_page)

        error_msg = check_credentials(username, password)
        if error_msg:
            return self.get_loginform(username, error_msg, from_page)
        else:
            cherrypy.session.regenerate()
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            self.on_login(username)
            raise cherrypy.HTTPRedirect(from_page or "/")

    @cherrypy.expose
    def logout(self, from_page="/"):
        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None
        if username:
            cherrypy.request.login = None
            self.on_logout(username)
        raise cherrypy.HTTPRedirect(from_page or "/")
