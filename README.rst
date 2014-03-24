==================================
OpenStack Nova Specifications
==================================

This git repository is used to hold approved design specifications for additions
to the Nova project.  Reviews of the specs are done in gerrit, using a similar
workflow to how we review and merge changes to the code itself.

The layout of this repository is::

  specs/<release>/
    approved/
    implemented/

Specifications are proposed for a given release by adding it to the `approved`
directory and posting it for review.  Once a given spec has been fully
implemented in a release, it can be moved to the `implemented` directory.  This
provides an easy view of what was actually implemented in a given release.  What
remains in the `approved` directory will provide historical record of specs we
approved but were not fully implemented.

You can find an example spec in `doc/source/specs/template.rst`.

Specifications have to be re-proposed for every release.  The review may be
quick, but even if something was previously approved, it should be re-reviewed
to make sure it still makes sense as written.

Prior to the Juno development cycle, this repository was not used for spec
reviews.  Reviews prior to Juno were completed entirely through Launchpad
blueprints::

  http://blueprints.launchpad.net/nova

For more information about working with gerrit, see::

  https://wiki.openstack.org/wiki/Gerrit_Workflow
