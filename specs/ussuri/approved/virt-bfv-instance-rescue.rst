..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Virtual instance rescue with boot from volume instances
=======================================================

https://blueprints.launchpad.net/nova/+spec/virt-bfv-instance-rescue

Building on the existing stable disk device rescue spec [1]_ this spec will
introduce support for rescuing boot from volume (BFV) instances and detail the
impact this will have on the API.

Problem description
===================

The original instance rescue implementation included a check in the compute API
to block any requests to rescue instances where the root BDM is a cinder volume
[2]_. Any such request would be rejected initially by an
``InstanceNotRescuable`` exception being raised back to the API that would then
result in a ``400`` error being returned to the caller.

Given the work being carried out as part of the stable disk device rescue spec
[1]_ we are now able to correctly wire up all disks during an instance rescue
and as a result can remove this check, accepting requests to rescue BFV
instances.

Use Cases
---------

* Tenant users would like to rescue BFV instances.

Proposed change
===============

The work outlined in the stable disk device rescue spec [1]_ will already allow
Nova to correctly wire up root cinder volumes during a rescue while booting
from the rescue device.

The only additional changes required to allow us to remove the current BFV
instance check from the compute API are a new compatibility trait, update to
``_get_rescue_image`` within the compute manager and a new API microversion.

A new ``COMPUTE_RESCUE_BFV`` trait will be introduced to os-traits, allowing a
compatibility check within the compute API to ensure the target compute service
is capable of rescuing BFV instances.

In the compute manager ``_get_rescue_image`` will be extended to attempt to
find a reference to the original image when a rescue image is not provided but
the instance is BFV. An ``InstanceNotRescuable`` exception will be raised if no
reference to the original can be found as we can't boot from the original root
disk as a rescue device while also attaching it again to the instance during a
rescue.

A new API microversion will be introduced to signal the change in behaviour
from the existing rescue implementation where attempts to rescue BFV instances
were rejected.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

A new microversion will be introduced to signal the change in behaviour from
the original implementation. No other changes will be made to the API.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Users attempting to use this feature will need to opt-in by using the newly
introduced microversion or later.


Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

The ``COMPUTE_RESCUE_BFV`` compatibility trait will be used to ensure the
target compute service is capable of performing the requested rescue against a
BFV instance within the compute API. If this is not set the existing
``InstanceNotRescuable`` exception will be raised back to the API resulting in
a ``400`` error being returned to the caller.

The new microversion or later will be used by callers to opt-in to this new
behaviour. If this isn't provided the original behaviour of rejecting requests
to rescue BFV instances will be used.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    lyarwood

Other contributors:

Feature Liaison
---------------
lyarwood

Work Items
----------

* Complete the initial stable device rescue spec. [1]_

* Introduce a new ``COMPUTE_RESCUE_BFV`` trait to os-traits

* Start reporting this trait from Nova's Libvirt driver.

* Introduce a new microversion signalling the API behaviour change.

* Start using the new ``COMPUTE_RESCUE_BFV`` trait and microversion in the REST
  API to determine when to allow the Compute API to rescue a BFV instance.

Dependencies
============

As highlighted throughout this spec this all requires the initial stable disk
device rescue spec [1]_ to land before this could be implemented.

Testing
=======

Tempest and functional tests will be introduced to fully validate this new
behaviour.

Documentation Impact
====================

The new microversion will be documented and the existing rescue API
documentation updated to reference it.

References
==========

.. [1] Virtual instance rescue with stable disk devices https://review.opendev.org/#/c/693849/
.. [2] BFV instance compute API check https://github.com/openstack/nova/blob/7aa88029bbf6311033457c32801963da01e88ecb/nova/compute/api.py#L4044-L4053

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
