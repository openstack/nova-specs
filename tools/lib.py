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
    # Local import so other tools' tox envs can be dep-free.
    from launchpadlib import launchpad
    # NOTE(mriedem): We have to use the development API since getSpecification
    # is not in the v1.0 API.
    # NOTE(melwitt): We have to use the development API because the
    # valid_specifications attribute is not in the v1.0 API.
    lp = launchpad.Launchpad.login_anonymously(
        consumer_name, 'production', LPCACHEDIR, version='devel')
    return lp.projects['nova']


def move_spec(srcfile_abs, destpath_abs, verbose, dry_run):
    srcfile_bname = os.path.basename(srcfile_abs)
    destfile_abs = os.path.join(destpath_abs, srcfile_bname)

    # Move the file
    if verbose:
        print("MOVING %s ==> %s" % (srcfile_abs, destfile_abs))
    if not dry_run:
        os.rename(srcfile_abs, destfile_abs)

    srcdir_abs = os.path.dirname(srcfile_abs)
    # The redirect file is one directory up from the source file
    redir_file = os.path.join(
        os.path.dirname(srcdir_abs), 'redirects')

    # NOTE(efried): Don't use os.path.* for paths in the redirect file; it is
    # interpreted by tooling that uses / as the path separator (HTTP redirects)
    # The redirect source is the last directory and the file.
    redir_src = '/'.join(
        [os.path.basename(os.path.dirname(srcfile_abs)), srcfile_bname])

    common_path = os.path.commonpath([srcfile_abs, destfile_abs])
    srcdir_rel = os.path.relpath(srcdir_abs, start=common_path)
    destfile_rel_split = os.path.relpath(
        destfile_abs, start=common_path).split(os.path.sep)
    backdirs = ['..'] * len(srcdir_rel.split(os.path.sep))
    redir_dest = '/'.join(backdirs + destfile_rel_split)
    redir_line = '%s %s\n' % (redir_src, redir_dest)
    if verbose:
        print("Adding redirect to %s:\n\t%s" % (redir_file, redir_line))
    if not dry_run:
        with open(redir_file, 'a') as redirects:
            redirects.write(redir_line)
