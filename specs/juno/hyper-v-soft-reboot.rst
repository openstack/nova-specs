..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Hyper-V soft reboot
==========================================

https://blueprints.launchpad.net/nova/+spec/hyper-v-soft-reboot

This blueprint introduces soft reboot support in the Nova Hyper-V driver.

Problem description
===================

Currently both "nova reboot" and "nova reboot --hard" cause a hard reset on
Hyper-V instances. The driver needs to perform a soft reboot in the former case
for consistency with the API specifications.

Proposed change
===============

This feature can be implemented by invoking the "InitiateShutdown" method of
the "Msvm_ShutdownComponent" class, waiting for the VM to reach a powered off
status and powering it on again.

For consistency with the libvirt driver, if a soft reboot fails then a hard
reboot is attempted.

Hyper-V provides an API to execute a soft shutdown but not a direct API to
execute a soft reboot, hence the need to wait for the shutdown to be completed.

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

Primary assignee:
  alexpilotti

Work Items
----------

* Hyper-V Nova driver feature implementation
* Unit tests

Dependencies
============

None

Testing
=======

* Unit tests
* Additional Tempest tests can be evaluated

Documentation Impact
====================

None

References
==========

* Initial discussion (Juno design summit):
  https://etherpad.openstack.org/p/nova-hyperv-juno
