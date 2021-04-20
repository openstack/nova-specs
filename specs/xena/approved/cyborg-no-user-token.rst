..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Add no user token auth when get Cyborg client
=============================================

https://blueprints.launchpad.net/nova/+spec/cyborg-no-user-token

Add support for cyborg service credentials to create cyborg admin client
instances.

Problem description
===================

Today, if VM hard reboot is triggered by resume_guests_state_on_host_boot=True
during nova-compute start, nova uses a non admin context to retrieve ARQs.
Nova should use the cyborg service token to make such query instead.

Use Cases
---------

As an operator, when I reboot a host and have
``[DEFAULT]/resume_guests_state_on_host_boot=True``
I would like my cyborg instance to retain access to their assigned
accelerators.

Proposed change
===============

Add Cyborg auth configuration in nova.conf.
Add support for create a cyborg admin client when no user token is present.

Alternatives
------------

None

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

Introduce user information to obtain authentication, which will make Nova
and Cyborg interaction less secure since we will now use a higher
privileged token and the cyborg admin password will now be present on
the compute node.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployers will have to add Cyborg auth with user and password configuration
in nova-cpu.conf for nova-compute service.

Developer impact
----------------

None

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  songwenping

Feature Liaison
---------------

Feature liaison:
  songwenping

Work Items
----------

* Register Cyborg group conf.
* Extend nova.accelerator.cyborg.get_client to create admin clients.
* Add related tests.

Dependencies
============

None.

Testing
=======

* Fix old unit and functional tests.
* Add related tests.

Documentation Impact
====================

None.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Xena
     - Introduced
