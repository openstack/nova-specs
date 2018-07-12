#!/usr/bin/env python
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

from launchpadlib import launchpad

LPCACHEDIR = os.path.expanduser('~/.launchpadlib/cache')


def get_releases():
    # 3-tuple (dirpath, dirnames, filenames)
    for _, choices, _ in os.walk('specs'):
        choices.remove('backlog')
        choices.sort()
        # Quit walking (release dirs are at the first level in 'specs')
        break
    return choices


def get_lp_nova(consumer_name):
    # NOTE(mriedem): We have to use the development API since getSpecification
    # is not in the v1.0 API.
    # NOTE(melwitt): We have to use the development API because the
    # valid_specifications attribute is not in the v1.0 API.
    lp = launchpad.Launchpad.login_anonymously(
        consumer_name, 'production', LPCACHEDIR, version='devel')
    return lp.projects['nova']
