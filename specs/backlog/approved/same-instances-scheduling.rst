..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Sort instances if possible inside an host aggregate
===================================================

https://blueprints.launchpad.net/nova/+spec/same-instances-scheduling

Nova should allow sorting instances based on preferences without
host aggregate speraration.

Problem description
===================

As an operator, when you manage hundred or thousand nodes, instances will be
automaticly balanced though all nodes. There is no possibility to ask the
infrastructure to group a kind of instances on the same hosts if possible.

A kind of instance could be based on a specific image, a specific flavor.

For this use case, host-aggregates are not used because this is not a strong
constraint, this is a prefered situation.

Use Cases
----------

Reduce the licence cost: Microsoft Windows licences are billed by host or by
socket. The goal is to stack all Windows instances on the same hosts as much as
possible.

As much as possible means this is a best effort feature, if Nova can place
this new Windows instance on a compute where other Windows are running, do
it. If not, spawn it where you want or on a empty compute to identify it
as `preferred widows compute` for future windows spawn.

Proposed change
===============

Posting to get preliminary feedback on the scope of this spec.

Alternatives
------------

None

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

None

Work Items
----------

None

Dependencies
============

None

Testing
=======

None

Documentation Impact
====================

None

References
==========

None

History
=======

None

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
