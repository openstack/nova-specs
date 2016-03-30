..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
Add os-win dependency
=====================

https://blueprints.launchpad.net/nova/+spec/add-os-win-library

Hyper-V is involved in many of OpenStack components (nova, neutron, cinder,
ceilometer, etc.) and will be involved with other components in the future.

A common library has been created, named os-win, in order to reduce the code
duplication between all these components (utils classes, which interacts
directly with Hyper-V through WMI), making it easier to maintain, review and
propose new changes to current and future components.

Problem description
===================

There are many Hyper-V utils modules duplicated across several projects,
which can be refactored into os-win, reducing the code duplication and making
it easier to maintain. Plus, the review process will be simplified, as
reviewers won't have to review Hyper-V related code, in which not everyone is
proficient.

Use Cases
---------

This blueprint impacts Developers and Reviewers.

Developers will be able to submit Hyper-V related commits directly to os-win.

Reviewers will not have to review low level Hyper-V related code. Thus, the
amount of code that needs to be reviewed will be reduced by approximately 50%.

Proposed change
===============

In order to implement this blueprint, minimal changes are necessary, as the
behaviour will stay the same.

The primary changes that needs to be done on nova are as follows:

* add os-win in requirements.txt
* replace ``nova.virt.hyperv.vmutils.HyperVException`` references to
  ``os_win.HyperVException``
* replace all ``nova.virt.hyperv.utilsfactory`` imports used by the
  `HyperVDriver` with ``os_win.utilsfactory``
* remove all utils modules and their unit tests in ``nova.virt.hyperv``, since
  they will no longer be used.
* other trivial changes, which are to be seen in the implementation.

Changes that needs to be done on other projects:

* add os-win in global-requirements.txt [1]

Alternatives
------------

Originally, os-win was planned to be part of Oslo, it was suggested that os-win
should be a standalone project, as otherwise the Oslo team would also have to
maintain in and there aren't many / anyone that specializes in Windows /
Hyper-V related code.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

os-win dependency will have to be installed in order for the HyperVDriver to be
used.

Developer impact
----------------

In a typical scenario, a blueprint implementation for the Hyper-V Driver will
require 2 parts:

* os-win commit, adding Hyper-V related utils required in order to implement
  the blueprint.
* nova commit, implementing the blueprint and using the changes made in os-win.

If a nova commit requires a newer version of os-win, the patch to
global-requirements should be referenced with Depends-On in the commit message.

For bugfixes, there are chances that they require 2 patches: one for nova and
one for os-win. The backported bugfix must be a squashed version of the 2
patches, referencing both commit IDs in the commit message::

    (cherry picked from commit <nova-commit-id>)
    (cherry picked from commit <os-win-commit-id)

If the bugfix requires only one patch to either project, backporting will
proceed as before.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Claudiu Belu <cbelu@cloudbasesolutions.com>

Other contributors:
  Lucian Petrut <lpetrut@cloudbasesolutions.com>

Work Items
----------

As described in the `Proposed change` section.

Dependencies
============

Adds os-win library as a dependency.

Testing
=======

* Unit tests
* Hyper-V CI

Documentation Impact
====================

The Hyper-V documentation page [3] will have to be updated to include os-win
as a dependency.

References
==========

[1] os-win added to global-requirements.txt:
        https://review.openstack.org/#/c/230394/

[2] os-win repository:
        https://github.com/openstack/os-win

[3] Hyper-V virtualization platform documentation page:
        http://docs.openstack.org/liberty/config-reference/content/hyper-v-virtualization-platform.html

History
=======

Mitaka: Introduced
