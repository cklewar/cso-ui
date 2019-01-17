#!/usr/bin/env python
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
# CSO UI runner
#
# Author: cklewar
#

from __future__ import absolute_import, print_function, unicode_literals

import os
import urllib3
import logging
import salt.client
import salt.config
import salt.runner

HAS_LIBS = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

if not len(logger.handlers):
    if not os.path.isdir('/var/log/jedi'):
        os.mkdir('/var/log/jedi')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler('/var/log/jedi/cso.log')
    logger.addHandler(handler)

__virtualname__ = 'cso_deploy_run'


def __virtual__():
    """
    Check mandatory libs are installed
    """

    # if not HAS_LIBS:
    #    return False, "SEL sdk not installed. See documentation for this runner."

    return True


def _get_jedi_config():
    gc = __salt__['sdb.get']('sdb://jedi_config/gitlab')

    jedi_config = dict()
    jedi_config['gitlab_pillar_project'] = gc['pillar_project_name']
    jedi_config['gitlab_model_project'] = gc['model_project_name']
    jedi_config['gitlab_group_name'] = gc['group_name']

    return jedi_config


def add_file_to_git(data=None, fname=None, path=None, ref=None):
    """
    Add a single file object to a project. File will be created in the repository at the given path with contents of data

    :param data:  string contents of the file to add
    :param path: remote path of the file to add
    :param ref: the name of branch, tag or commit
    :return: {'name': '', 'comment': '', 'success':'', 'changes':''}
    """

    logger.debug("____ cso_runner:add_file_to_git ____")
    ret = dict()
    ret['name'] = 'jedi_gitlab'
    ret['success'] = True
    ret['changes'] = dict()

    jedi_config = _get_jedi_config()

    project_name = jedi_config['gitlab_pillar_project']
    group_name = jedi_config['gitlab_group_name']
    remote_path = '{0}/{1}'.format(path, fname)
    resp = __salt__['jedi_gitlab.add_file_object_to_project'](project_name=project_name, group_name=group_name,
                                                              file_contents=data, remote_path=remote_path, ref=ref)

    logger.debug(resp)
    return "Successfully added file {0} to repository {1}".format(fname, path)


def del_file_from_git(fname=None, path=None, ref=None):
    logger.debug("____ cso_runner:del_file_from_git ____")

    ret = dict()
    ret['name'] = 'jedi_gitlab'
    ret['success'] = True
    ret['changes'] = dict()

    jedi_config = _get_jedi_config()

    project_name = jedi_config['gitlab_pillar_project']
    group_name = jedi_config['gitlab_group_name']
    remote_path = '{0}/{1}'.format(path, fname)

    try:
        resp = __salt__['jedi_gitlab.del_file_from_project'](project_name=project_name, group_name=group_name,
                                                             fname=fname, remote_path=remote_path, ref=ref)
        logger.debug(resp)
        return "Successfully deleted file {0} from repository {1}".format(fname, path)

    except Exception as e:
        logger.debug(e)
        return "Failed to delete file {0} from repository {1}".format(fname, path)


def update_file_in_git(fname=None, path=None, ref=None):
    logger.debug("____ cso_runner:update_file_in_git ____")

    ret = dict()
    ret['name'] = 'jedi_gitlab'
    ret['success'] = True
    ret['changes'] = dict()

    jedi_config = _get_jedi_config()

    project_name = jedi_config['gitlab_pillar_project']
    group_name = jedi_config['gitlab_group_name']
    remote_path = '{0}/{1}'.format(path, fname)

    try:
        resp = __salt__['jedi_gitlab.update_file_in_project'](project_name=project_name, group_name=group_name,
                                                             fname=fname, remote_path=remote_path, ref=ref)
        logger.debug(resp)
        return "Successfully updated file {0} in repository {1}".format(fname, path)

    except Exception as e:
        logger.debug(e)
        return "Failed to update file {0} in repository {1}".format(fname, path)


def get_data_from_git(upstream_path, ref):
    """
        ..
        Get use case config objects data

        :param upstream_path: The file path in the model repository in gitlab
        :param ref: the name of branch, tag or commit
    """

    logger.debug("____ cso_runner:get_data_from_git ____")

    ret = dict()
    ret['success'] = True
    ret['comment'] = 'na'
    ret['changes'] = dict()

    if upstream_path.endswith('.gitkeep'):
        ret['success'] = False
        ret['comment'] = 'Ignoring .gitkeep file'
        return ret

    jedi_config = _get_jedi_config()

    project_name = jedi_config['gitlab_pillar_project']
    group_name = jedi_config['gitlab_group_name']

    resp = __salt__['jedi_gitlab.get_file_from_project'](upstream_path, project_name, group_name, ref)

    if 'success' in resp and resp['success'] is not True:
        ret['success'] = False
        ret['comment'] = 'Could not get inventory file'
        return ret

    file_contents = resp['file_contents']
    ret['changes'] = file_contents

    return ret


def run_ansible_playbook(playbook=None):
    logger.debug("____ cso_runner:run_playbook ____")
    logger.debug(playbook)
    local = salt.client.LocalClient(__opts__['conf_file'])
    pillar = {"pillar": {"playbook": playbook}}
    ret = local.cmd('jedi', 'state.apply', ['jedi.run_playbook'], kwarg=pillar)
    return ret
