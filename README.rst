=======
README
=======

OpenStack Nova Specifications
-----------------------------


This git repository is used to hold approved design specifications for additions
to the Nova project.  Reviews of the specs are done in gerrit, using a similar
workflow to how we review and merge changes to the code itself.

The layout of this repository is::

  specs/<release>/

Where there are two sub-directories:

  specs/<release>/approved: specifications approved but not yet implemented
  specs/<release>/implemented: implemented specifications

This directory structure allows you to see what we thought about doing,
decided to do, and actually got done. Users interested in functionality in a
given release should only refer to the ``implemented`` directory.

You can find an example spec in ``specs/template.rst``.

Additionally, we allow the proposal of specifications that do not have a
developer assigned to them. These are proposed for review in the same manner as
above, but are added to::

  specs/backlog/approved

Specifications in this directory indicate the original author has either
become unavailable, or has indicated that they are not going to implement the
specification. The specifications found here are available as projects for
people looking to get involved with Nova. If you are interested in
claiming a spec, start by posting a review for the specification that moves it
from this directory to the next active release. Please set yourself as the new
`primary assignee` and maintain the original author in the `other contributors`
list.

Specifications are proposed for a given release by adding them to the
``specs/<release>`` directory and posting it for review.  The implementation
status of a blueprint for a given release can be found by looking at the
blueprint in launchpad.  Not all approved blueprints will get fully implemented.

Specifications have to be re-proposed for every release.  The review may be
quick, but even if something was previously approved, it should be re-reviewed
to make sure it still makes sense as written.

Prior to the Juno development cycle, this repository was not used for spec
reviews.  Reviews prior to Juno were completed entirely through `Launchpad
blueprints <http://blueprints.launchpad.net/nova>`_

Please note, Launchpad blueprints are still used for tracking the
current status of blueprints. For more information, see https://wiki.openstack.org/wiki/Blueprints

For more information about working with gerrit, see http://docs.openstack.org/infra/manual/developers.html#development-workflow

To validate that the specification is syntactically correct (i.e. get more
confidence in the Jenkins result), please execute the following command::

  $ tox

After running ``tox``, the documentation will be available for viewing in HTML
format in the ``doc/build/`` directory.
