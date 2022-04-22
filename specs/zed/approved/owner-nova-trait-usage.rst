..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Usage of new OWNER_NOVA trait
=============================

The spec is about the usage of new OWNER_NOVA trait.

Problem description
===================

Today in placement each resource class is typically only used by a single
service. With the introduction of VGPU support in cyborg both nova and cyborg
now share ownership or usage of the VGPU resource class. This creates a usage
problem where different workflows are required to correctly consume the VGPU
resource class based on which service created the inventory.

As both the nova and cyborg projects can report VGPU resources, we should be
able to solve the shared VGPU resource class problem by each service recording
that they created or "own" the resource provider, however, that is not done
today.

Use Cases
---------

As an operator, I would like to be able to deploy multiple services that can
share the same resource class name without creating scheduling conflicts.

As an operator, I want to have a way to transition management of resources
between OpenStack service using simple operations such as resizing an instance
from a flavor that consumes VGPUs provided by nova to a flavor that uses VGPUs
provided by cyborg.

As an end-user, I would like to be able to consume resources from nova and
cyborg in a single instance without having to understand the detail of
placement or scheduling.

Proposed change
===============

This spec proposes adding a new OWNER_NOVA trait and pre-filter.
Nova will tag every ResourceProvider it creates with a OWNER_NOVA trait,
implying that inventories are provided by this service only.
Nova will provide a pre-filter that actively requests its own OWNER_NOVA trait
while cyborg will require the OWNER_CYBORG trait via its device profile to
filter their own managed resources.

Alternatives
------------

None

Data model impact
-----------------

None.

REST API impact
---------------

None

Security impact
---------------

None.

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

That operators will see new traits for all the Resource Providers.

Developer impact
----------------

None

Upgrade impact
--------------

We need to make sure that the nova VGPU feature still works during a rolling
upgrade to the nova version introducing the OWNER_NOVA trait.
So to ensure that the nova compute service version will be bumped to signal
when a compute service is upgraded and therefore reports the OWNER_NOVA trait
on its RPs. The pre-filter filtering on OWNER_NOVA will only be enabled if the
minimum compute service version indicates that every compute service is now
upgraded and therefore reporting the OWNER_NOVA trait.
This way during a rolling upgrade with old compute still present the
pre-filter will not be enabled and the nova VGPU feature will work as today.
But as soon as all the computes are upgraded the pre-filter will automatically
start enforcing the OWNER_NOVA trait for all the nova VGPU feature requests.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  wenpingsong

Other contributors:
  brinzhang

Feature Liaison
---------------

Feature liaison:
  wenpingsong

Work Items
----------

* Add OWNER_NOVA for os_traits project.
* Tag every ResourceProvider that nova creates with a OWNER_NOVA trait.
* Add pre-filter the trait for every Nova request group.
* Add related unit and functional tests.

Dependencies
============

None

Testing
=======

Need relate unit and functional tests.

Documentation Impact
====================

Modify the related docs with OWNER_NOVA traits for update available resources
and pre-filter scheduler.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Introduced
