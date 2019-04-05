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

import argparse
import os

import lib


def get_options():
    parser = argparse.ArgumentParser(
        description='Count blueprints for a given release. Requires '
                    'launchpadlib to be installed.')
    parser.add_argument('release', help='The release to process.',
                        choices=lib.get_releases())
    return parser.parse_args()


def count_blueprints(release):
    lp_nova = lib.get_lp_nova('count-specs')
    # Valid specifications are specifications that are not obsolete.
    blueprints = lp_nova.getSeries(name=release).valid_specifications
    targeted = len(blueprints)
    approved = 0
    implemented = 0
    unapproved_blueprint_names = set()
    for blueprint in blueprints:
        if blueprint.definition_status == 'Approved':
            approved += 1
        else:
            unapproved_blueprint_names.add(blueprint.name)
        if blueprint.implementation_status == 'Implemented':
            implemented += 1
    print('')
    print('Summary')
    print('-------')
    print('Number of Targeted blueprints: %d' % targeted)
    print('Number of Approved blueprints: %d' % approved)
    print('Number of Implemented blueprints: %d' % implemented)

    # Check for approved specs whose blueprints have not been approved
    cwd = os.getcwd()
    approved_dir = os.path.join(cwd, 'specs', release, 'approved')
    approved_specs = os.listdir(approved_dir)
    template_file = '%s-template.rst' % release
    for spec_fname in sorted(approved_specs):
        # get the blueprint name, it should be the name of the rst file
        if not spec_fname.endswith('.rst'):
            continue
        # check for the template file and skip that
        if spec_fname == template_file:
            continue
        bp_name = spec_fname.split('.rst')[0]
        if bp_name in unapproved_blueprint_names:
            print('WARNING: Blueprint for spec %s needs approval.' %
                  spec_fname)


def main():
    opts = get_options()
    count_blueprints(opts.release)


if __name__ == '__main__':
    main()
