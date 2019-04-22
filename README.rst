=======
README
=======

OpenStack Nova Specifications
=============================


This git repository is used to hold approved design specifications for additions
to the Nova project.  Reviews of the specs are done in gerrit, using a similar
workflow to how we review and merge changes to the code itself. For specific
policies around specification review, refer to the end of this document.

The layout of this repository is::

  specs/<release>/

Where there are two sub-directories:

specs/<release>/approved
  specifications approved but not yet implemented

specs/<release>/implemented
  implemented specifications

The lifecycle of a specification
--------------------------------

Developers proposing a specification should propose a new file in the
``approved`` directory. nova-specs-core will review the change in the usual
manner for the OpenStack project, and eventually it will get merged if a
consensus is reached. At this time the Launchpad blueprint is also approved.
The developer is then free to propose code reviews to implement their
specification. These reviews should be sure to reference the Launchpad
blueprint in their commit message for tracking purposes.

Once all code for the feature is merged into Nova, the Launchpad blueprint is
marked complete. As the developer of an approved specification it is your
responsibility to mark your blueprint complete when all of the required
patches have merged.

Periodically, someone from nova-specs-core will move implemented specifications
from the ``approved`` directory to the ``implemented`` directory. Whilst
individual developers are welcome to propose this move for their implemented
specifications, we have generally just done this in a batch at the end of the
release cycle. It is important to create redirects when this is done so that
existing links to the approved specification are not broken. Redirects aren't
symbolic links, they are defined in a file which sphinx consumes. An example
is at ``specs/kilo/redirects``.

.. note:: Use the ``tox -e move-implemented-specs`` target at the end of each
          release to automatically move completed specs and populate the
          redirects file for that release. For example::

            tox -r -e move-implemented-specs -- --dry-run --verbose newton

          Remove the ``--dry-run`` flag to perform the actual file
          moves/writes.

This directory structure allows you to see what we thought about doing,
decided to do, and actually got done. Users interested in functionality in a
given release should only refer to the ``implemented`` directory.

Example specifications
----------------------

You can find an example spec for a given release in
``specs/<release>-template.rst``.

Backlog specifications
----------------------

Additionally, we allow the proposal of specifications that either do not have a
developer assigned to them or are not targeted for the current release. These
are proposed for review in the same manner as above, but are added to::

  specs/backlog/approved

Specifications in this directory indicate the original author has either become
unavailable or has indicated that they are not going to implement the
specification. The specifications found here are available as projects for
people looking to get involved with Nova. Alternatively, they may be for ideas
generated during a given release cycle to begin design discussions, but not
intended to be implemented until a future cycle. If you are interested in
claiming an unassigned backlog spec, or are the assignee and are ready to
propose it for implementation in the current release, start by posting a review
for the specification that moves it from this directory to the next active
release. To ensure existing links are not broken, redirects must be created in
a fashion similar to the process for ``implemented`` specs above. The
``move-spec`` tox target is available to help with this. For example::

  tox -e move-spec -- --dry-run --verbose specs/backlog/my-great-idea.rst specs/train/approved

Remove the ``--dry-run`` option to perform the actual file moves/writes.

.. note:: Please do not use ``move-spec`` to repropose an unimplemented spec
          from one release to another. Instead follow the instructions at
          `Previously approved specifications`_

When claiming an unassigned backlog spec, please set yourself as the new
`primary assignee` and maintain the original author in the `other contributors`
list.

Abandoning a specification
--------------------------
.. note:: For now, this process should only be used to abandon backlog specs.
          Please do not use this process for specs in a real release's
          ``approved`` directory. Currently the indication that such a spec is
          abandoned is that it never appears in any release's ``implemented``
          directory. We may change this process in the future.

If it is decided that a ``backlog`` spec is "never" going to be implemented,
post a review moving the specification from ``specs/<release>/approved`` to
``specs/abandoned``. As with the above processes, redirects must be created to
ensure existing links are not broken. The ``abandon-spec`` tox target is
available to help with this. For example::

  tox -e abandon-spec -- --dry-run --verbose specs/backlog/it-was-a-great-idea.rst

Remove the ``--dry-run`` option to perform the actual file moves/writes.

Please add an explanation to the spec indicating why it is being abandoned, and
update the History section accordingly.

Design documents for releases prior to Juno
-------------------------------------------

Prior to the Juno development cycle, this repository was not used for spec
reviews.  Reviews prior to Juno were completed entirely through `Launchpad
blueprints <http://blueprints.launchpad.net/nova>`_

Please note, Launchpad blueprints are still used for tracking the
current status of blueprints. For more information, see
https://wiki.openstack.org/wiki/Blueprints

Working with gerrit and specification unit tests
------------------------------------------------

For more information about working with gerrit, see
http://docs.openstack.org/infra/manual/developers.html#development-workflow

To validate that the specification is syntactically correct (i.e. get more
confidence in the Jenkins result), please execute the following command::

  $ tox

After running ``tox``, the documentation will be available for viewing in HTML
format in the ``doc/build/`` directory.

Specification review policies
=============================

There are a number of review policies which nova-specs-core will apply when
reviewing proposed specifications. They are:

Trivial specifications
----------------------

Proposed changes which are trivial (very small amounts of code) and don't
change any of our public APIs are sometimes not required to provide a
specification. In these cases a Launchpad blueprint is considered sufficient.
These proposals are approved during the `Open Discussion` portion of the
weekly nova IRC meeting. If you think your proposed feature is trivial and
meets these requirements, we recommend you bring it up for discussion there
before writing a full specification.

Previously approved specifications
----------------------------------

`Specifications are only approved for a single release`. If your specification
was previously approved but not implemented (or not completely implemented),
then you must seek re-approval for the specification. You can re-propose your
specification by doing the following:

* Copy (not move) your specification to the right directory for the current release.
* Update the document to comply with the new template.
* If there are no functional changes to the specification (only template changes) then add the `Previously-approved: <release>` tag to your commit message.
* Send for review.
* nova-specs-core will merge specifications which meet these requirements with a single +2.

Specifications which depend on merging code in other OpenStack projects
-----------------------------------------------------------------------

For specifications `that depend on code in other OpenStack projects merging`
we will not approve the nova specification until the code in that other project
has merged. The best example of this is Cinder and Neutron drivers. To
indicate your specification is in this state, please use the Depends-On git
commit message tag. The correct format is `Depends-On: <change id of other
work>`. nova-specs-core can approve the specification at any time, but it wont
merge until the code we need to land in the other project has merged as well.

New libvirt image backends
--------------------------

There are some cases where an author might propose adding a new libvirt
driver image storage backend which does not require code in other OpenStack
projects. An example was the ceph image storage backend, if we treat that as
separate from the ceph volume support code. Implementing a new image storage
backend in the libvirt drive always requires a specification because of our
historical concerns around adequate CI testing.
