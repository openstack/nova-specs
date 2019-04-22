========================
Abandoned Specifications
========================

This folder is for specs that were at some point approved, but we have
since determined, for whatever reason, shall not be implemented.

For the time being, let's only use this for backlog specs, and leave
unchanged the existing process for unimplemented specs in a real
release (i.e. leave them there in the 'approved' directory).

To move a spec to this folder, use the ``abandon-spec`` tox target. In
addition to moving the file, this ensures the proper redirect is created
so any existing links in the wild are not broken.

For example, first do a dry run (``-n``) with verbose output (``-v``) to
see what is going to happen::

  tox -e abandon-spec -- -n -v specs/backlog/approved/it-was-a-great-idea.rst

When you are satisfied, remove the ``-n`` option to make it happen for
real.
