#!/usr/bin/env python
# Copyright 2016 IBM Corp.
#
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

from __future__ import print_function

import argparse
import os

from launchpadlib import launchpad

LPCACHEDIR = os.path.expanduser('~/.launchpadlib/cache')


def get_choices():
    # 3-tuple (dirpath, dirnames, filenames)
    for _, choices, _ in os.walk('specs'):
        choices.remove('backlog')
        choices.sort()
        # Quit walking (release dirs are at the first level in 'specs')
        break
    return choices


def get_options():
    parser = argparse.ArgumentParser(
        description='Move implemented specs for a given release. Requires '
                    'launchpadlib to be installed.')
    parser.add_argument('-v', '--verbose', help='Enable verbose output.',
                        action='store_true')
    parser.add_argument('-n', '--dry-run',
                        help='Do everything except move the files.',
                        action='store_true')
    parser.add_argument('release', help='The release to process.',
                        choices=get_choices())
    return parser.parse_args()


def move_implemented_specs(release, verbose=False, dry_run=False):
    if verbose:
        print('Processing specs for release: %s' % release)

    cwd = os.getcwd()
    approved_dir = os.path.join(cwd, 'specs', release, 'approved')
    implemented_dir = os.path.join(cwd, 'specs', release, 'implemented')
    redirects_file = os.path.join(cwd, 'specs', release, 'redirects')
    approved_specs = os.listdir(approved_dir)
    # NOTE(mriedem): We have to use the development API since getSpecification
    # is not in the v1.0 API.
    lp = launchpad.Launchpad.login_anonymously(
        'move-specs', 'production', LPCACHEDIR, version='devel')
    lp_nova = lp.projects['nova']
    # yay for stats and summaries
    move_count = 0
    incomplete_count = 0
    warnings = []
    template_file = '%s-template.rst' % release
    for spec_fname in sorted(approved_specs):
        # get the blueprint name, it should be the name of the rst file
        if not spec_fname.endswith('.rst'):
            continue

        # check for the template file and skip that
        if spec_fname == template_file:
            continue

        bp_name = spec_fname.split('.rst')[0]
        if verbose:
            print('Processing approved blueprint: %s' % bp_name)

        # get the blueprint object from launchpad
        lp_spec = lp_nova.getSpecification(name=bp_name)
        if lp_spec:
            # check the status; it's possible for a blueprint to be marked as
            # complete but not actually be implemented, e.g. if it's superseded
            # or obsolete.
            if (lp_spec.is_complete and
                    lp_spec.implementation_status == 'Implemented'):
                if verbose:
                    print('Moving blueprint to implemented: %s' % spec_fname)

                if not dry_run:
                    # move the file from approved to implemented
                    os.rename(os.path.join(approved_dir, spec_fname),
                              os.path.join(implemented_dir, spec_fname))
                    # add an entry to the redirects file
                    with open(redirects_file, 'a') as redirects:
                        redirects.write('approved/%s ../implemented/%s\n' %
                                        (spec_fname, spec_fname))
                move_count += 1
            else:
                if verbose:
                    print('Blueprint is not complete: %s; '
                          'implementation status: %s' %
                          (bp_name, lp_spec.implementation_status))
                incomplete_count += 1
        else:
            print('WARNING: Spec %s does not exist in launchpad for nova. The '
                  'spec filename should be fixed.' % bp_name)
            warnings.append(spec_fname)

    template_file = os.path.join(implemented_dir, template_file)
    if not dry_run and move_count and os.path.exists(template_file):
        os.unlink(template_file)

    if verbose:
        print('')
        print('Summary')
        print('-------')
        print('Number of completed specs moved: %s' % move_count)
        print('Number of incomplete specs: %s' % incomplete_count)

    if warnings:
        print('')
        print('Invalid spec filenames')
        print('----------------------')
        for warning in sorted(warnings):
            print(warning)


def main():
    opts = get_options()
    move_implemented_specs(opts.release, opts.verbose, opts.dry_run)


if __name__ == "__main__":
    main()
