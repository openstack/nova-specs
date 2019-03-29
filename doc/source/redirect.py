# A simple sphinx plugin which creates HTML redirections from old names
# to new names. It does this by looking for files named "redirect" in
# the documentation source and using the contents to create simple HTML
# redirection pages for changed filenames.

import os.path

from sphinx.util import logging

LOG = logging.getLogger(__name__)


def process_redirect_file(app, path, ent):
    parent_path = path.replace(app.builder.srcdir, app.builder.outdir)
    with open(os.path.join(path, ent)) as redirects:
        for line in redirects.readlines():
            from_path, to_path = line.rstrip().split(' ')
            from_path = from_path.replace('.rst', '.html')
            to_path = to_path.replace('.rst', '.html')

            redirected_filename = os.path.join(parent_path, from_path)
            redirected_directory = os.path.dirname(redirected_filename)
            if not os.path.exists(redirected_directory):
                os.makedirs(redirected_directory)
            with open(redirected_filename, 'w') as f:
                f.write('<html><head><meta http-equiv="refresh" content="0; '
                        'url=%s" /></head></html>'
                        % to_path)


def emit_redirects(app, exc):
    LOG.info('scanning %s for redirects...', app.builder.srcdir)

    def process_directory(path):
        for ent in os.listdir(path):
            p = os.path.join(path, ent)
            if os.path.isdir(p):
                process_directory(p)
            elif ent == 'redirects':
                LOG.info('   found redirects at %s' % p)
                process_redirect_file(app, path, ent)

    process_directory(app.builder.srcdir)
    LOG.info('...done')


def setup(app):
    app.connect('build-finished', emit_redirects)
