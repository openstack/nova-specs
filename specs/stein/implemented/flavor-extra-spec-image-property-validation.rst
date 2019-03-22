..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Flavor Extra Spec and Image Properties Validation
=================================================

https://blueprints.launchpad.net/nova/+spec/flavor-extra-spec-image-property-validation

Problem description
===================

Currently flavor extra-specs and image properties validation are done in
separate places. If they are not compatible, the instance may fail to launch
and go into an ERROR state, or may reschedule an unknown number of times
depending on the virt driver behaviour.

Use Cases
---------

As an end user I would like to have instant feedback if flavor extra spec or
image properties are not valid or they are not compatible with each other so
I can correct my configuration and retry the operation.

Proposed change
===============

We want to validate the combination of the flavor extra-specs and image
properties as early as possible once they're both known.

If validation fails then synchronously return error to user.

We'd need to do this anywhere the flavor or image changes, so basically
instance creation, rebuild, and resize. More precisely, rename
_check_requested_image() to something more generic, take it out of
_checks_for_create_and_rebuild(), modify it to check more things and call it
from all three operations: creation, rebuild, and resize.

.. note:: Only things that are not virt driver specific are validated.

Examples of validations to be added [1]_:

* Call hardware.numa_get_constraints to validate all the various numa-related
  things. This is currently done only on _create_instance(), should be done for
  resize/rebuild as well.
* Ensure that the cpu policy, cpu thread policy and emulator thread policy
  values are valid.
* Validate the realtime mask.
* Validate the number of serial ports.
* Validate the cpu topology constraints.
* Validate the ``quota:*``settings (that are not virt driver specific) in the
  flavor.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

Due to the new validations, users could face more 4xx errors for more cases
than we did before in create/rebuild/resize operations.

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

Negligible.


Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jackding

Work Items
----------

* Add validations mostly in nova/compute/api.py.
* Add/update unit tests.
* Update documentation/release-note if necessary depending on the new
  validations added.

Dependencies
============

None

Testing
=======

Will add unit tests.


Documentation Impact
====================

None

References
==========

.. [1] https://docs.openstack.org/nova/latest/user/flavors.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
