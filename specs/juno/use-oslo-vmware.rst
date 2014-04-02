..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================================
Integrate the vmware driver with the oslo.vmware library
========================================================

https://blueprints.launchpad.net/nova/+spec/use-oslo-vmware

Now that the oslo.vmware library has been released, the vmware driver should be
updated to use it.


Problem description
===================

Too much code duplication of vmware-related projects led to the creation of the
oslo.vmware project (https://github.com/openstack/oslo.vmware). Now that it is
released, and already started to be used by Glance and Ceilometer, it's time
the nova driver does the same.


Proposed change
===============

This means mostly adding new import lines, mechanical conversion of call sites
and deleting existing code obsoleted by the library.  Most of the work has
already be done and proposed in the icehouse cycle
(https://review.openstack.org/#/c/70175/) so that can be used as the starting
point of the patch.
The changes are pure code reorganization, and has no externally visible impact.

Alternatives
------------

None, unless we consider the undesirable option of keeping status quo as one.

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

Some version of the oslo.vmware library as eventually dictated by the
the project requirements will have to be installed for the updated vmware
driver to function.

Developer impact
----------------

While the changes are mechanical, it touches many places in the vmwareapi
driver code base, so it can cause a lot of conflict with other driver work.
Once merged, it is likely all vmware driver related patches under review will
have to be updated to account for it.

On the flip side, there is developer impact of this change not being merged as
well:

Until this change is merged, driver changes/fixes to areas of functionality
that oslo.vmware also provides means that a developer should almost always have
to update both nova and oslo.vmware with similar patches.

To migitate this issue of conflicts and code duplication, it is recommended
that patches related to the vmware driver should be made dependent on this
work.

Changes to the nova driver may now require a change/release to oslo.vmware
as a pre-requisite.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  vui

Work Items
----------

Mostly https://review.openstack.org/#/c/70175/ plus some additional updates to
account for recent code additions to the vmware driver code.


Dependencies
============

Changes pertaining to
https://blueprints.launchpad.net/nova/+spec/vmware-spawn-refactor
will cause significant code churn, but given the mostly mechanical nature of
the changes to this blueprint, reacting to the former should be fairly
straightforward.

Given that this work and that for the vmware-spawn-refactor blueprint are
fairly orthogonal, and both necessary to facilitate additional changes to the
driver, it is proposed that they be considered the highest-priority items for
the vmware driver to be included in Juno-1.


Testing
=======

Unit tests exercising the obsoleted code will be removed. Updating existing
tests that currently mocks the obsoleted code to use use.vmware accordingly
so that they pass should be sufficient to validate the change.

No externally visible changes means no additional Tempest tests are needed.


Documentation Impact
====================

None


References
==========

* https://github.com/openstack/oslo.vmware
* https://review.openstack.org/#/c/70175/
* https://blueprints.launchpad.net/nova/+spec/vmware-spawn-refactor
