#!/usr/bin/env python
# Copyright 2019 OpenStack Foundation
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

import argparse
import os

import lib


def get_options():
    parser = argparse.ArgumentParser(
        description='Move a spec from one folder to another and create a '
                    'redirect for it.')
    parser.add_argument('-v', '--verbose', help='Enable verbose output',
                        action='store_true')
    parser.add_argument('-n', '--dry-run',
                        help='Do everything except move/write the files',
                        action='store_true')
    parser.add_argument('spec',
                        help='Path to the spec to be moved. For example, '
                             'specs/backlog/approved/my-great-idea.rst')
    parser.add_argument('destdir',
                        help='Directory to which the spec should be moved. '
                             'For example, specs/train/approved')
    return parser.parse_args()


def move_spec(spec, destdir, verbose, dry_run):
    spec_abs = os.path.abspath(spec)
    if not os.path.exists(spec_abs):
        raise ValueError('Could not find spec %s at %s' % (spec, spec_abs))
    if not os.path.isfile(spec_abs):
        raise ValueError('%s is not a regular file' % spec)

    destdir_abs = os.path.abspath(destdir)
    if not os.path.exists(destdir_abs):
        raise ValueError('Could not find destination directory %s at %s (you '
                         'may have to create it)' %
                         (destdir, destdir_abs))
    if not os.path.isdir(destdir_abs):
        raise ValueError('%s is not a directory' % destdir)

    lib.move_spec(
        spec_abs, destdir_abs, verbose, dry_run)


def main():
    opts = get_options()
    move_spec(opts.spec, opts.destdir, opts.verbose, opts.dry_run)


if __name__ == '__main__':
    main()
