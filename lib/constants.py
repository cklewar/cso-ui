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

DRIVER_SALTSTACK = 'saltstack'
DRIVER_ANSIBLE = 'ansible'
DRIVER_PYEZ = 'pyez'
ADMIN_USERS = ('admin', 'root')
ADMIN_USER_PW = 'juniper123'
CONFIG = None
TERM_STRINGS = ["Amnesiac (ttyu0)", "Ubuntu 14.04.1 LTS jdm tty1"]
MODEL_NORMAL = ['qfx', 'srx', 'ex', 'mx']
logger = None
cso_logger = None
jnpr_junos_tty = None
jnpr_junos_tty_netconf = None
jnpr_junos_tty_telnet = None

LOG_CONF = {
    'version': 1,

    'formatters': {
        'void': {
            'format': ''
        },
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'cherrypy_console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'void',
            'stream': 'ext://sys.stdout'
        },
        'cherrypy_access': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'void',
            'filename': 'log/access.log',
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        },
        'cherrypy_error': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'void',
            'filename': 'log/errors.log',
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        },
        'cso_ui': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': 'log/cso-ui.log',
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO'
        },
        'cso_ui': {
            'handlers': ['cso_ui'],
            'level': 'INFO',
            'propagate': False
        },
        'jnpr.junos.tty': {
            'handlers': ['cso_ui'],
            'level': 'DEBUG',
            'propagate': False
        },
        'jnpr.junos.tty_netconf': {
            'handlers': ['cso_ui'],
            'level': 'DEBUG',
            'propagate': False
        },
        'jnpr.junos.tty_telnet': {
            'handlers': ['cso_ui'],
            'level': 'DEBUG',
            'propagate': False
        },
        'jnpr.junos.console': {
            'handlers': ['cso_ui'],
            'level': 'DEBUG',
            'propagate': False
        },
        'cherrypy.access': {
            'handlers': ['cherrypy_access'],
            'level': 'INFO',
            'propagate': False
        },
        'cherrypy.error': {
            'handlers': ['cherrypy_console', 'cherrypy_error'],
            'level': 'INFO',
            'propagate': False
        },
    }
}
