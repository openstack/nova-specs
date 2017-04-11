..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Allow an attached volume to be extended
=======================================

https://blueprints.launchpad.net/nova/+spec/nova-support-attached-volume-extend


Problem description
===================

Currently a volume size extension requires that a volume be
in the available state. This requires an attached volume to be detached
from a server before the volume can be extended in size. This requires that
a volume be brought offline from the standpoint of the application
using the volume.

Use Cases
---------

A end user wants to increase the size of a volume that is currently attached
to a server.

Proposed change
===============

Nova will be listening for attached volume extend notification from Cinder
using the existing external-events API endpoint.

When the notification is received, Nova will trigger a rescanning of device
on the host using os-brick to discover the change in volume size.
The os-brick library already supports volume size extension
through the Connector API method called "extend_volume" since 0.8.0.

The initial implementation aims to support virt drivers using os-brick
such as libvirt and hyper-v.

The end user will have to perform a partition and/or filesystem resize
in the guest to fully benefit from the new volume size.

Capabilities discovery and error handling if the compute host
does not support the extend volume operation are being discussed on the
openstack-dev mailinglist. [1]_

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

A new microversion is required because a new external-event type
will be added: volume-extended.

Proposed JSON request body for the new "volume-extended" event::

    {
        "events": [
            {
                "name": "volume-extended",
                "server_uuid": "3df201cf-2451-44f2-8d25-a4ca826fc1f3",
                "tag": "0e63d806-6fe4-4ffc-99bf-f3dd056574c0"
            }
        ]
    }

Definition of fields:

name
  Name of the event. ("volume-extended" for this feature).
tag
  Volume UUID being extended.
server_uuid
  Server UUID to which the extended volume is attached.

Proposed JSON response body for the new "volume-extended" event::

    {
        "events": [
            {
                "name": "volume-extended",
                "status": "completed",
                "code": 200,
                "server_uuid": "3df201cf-2451-44f2-8d25-a4ca826fc1f3",
                "tag": "0e63d806-6fe4-4ffc-99bf-f3dd056574c0"
            }
        ]
    }

Definition of fields:

name
  Name of the event. ("volume-extended" for this feature).
status
  Event status. Possible values:
    * "completed" if accepted by Nova
    * "failed" if a failure is encountered
code
  Event result code. Possible values:
    * 200 means accepted
    * 404 means the server could not be found
    * 422 means the event cannot be processed because the instance was found
      to not be associated to a host.
server_uuid
  Same value as provided in original request.
tag
  Same value as provided in original request.

Possible HTTP response codes:

* The HTTP response code 200 is returned on success.
* The HTTP response code 207 is returned if any event fails with 422 code.
* The HTTP response code 400 is returned on a bad request.
* The HTTP response code 401 is returned if request is unauthorized. (keystone)
* The HTTP response code 403 is returned if request is forbidden. (policy)
* The HTTP response code 404 is returned if no server could be found.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The end user will be able to extend their volumes without having
to detach them.

The end user will have to perform a partition and/or filesystem resize
to fully benefit from the new volume size.

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

Driver owners may want to enable this feature in their driver.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mgagne
Other contributors:
  manas-mandlekar
  shyvenug@in.ibm.com

Work Items
----------

* Add new external-event type and new microversion
* Call virt driver so guest detects the new volume size
* Call the os-brick extend_volume API to trigger the host kernel size
  information to be updated on the attached host

Dependencies
============

* The Cinder API changes to allow extend of an attached volume


Testing
=======

Add Tempest test where the size of a volume attached to a server is extended
and the new size can be discovered on the host.

Documentation Impact
====================

Update the compute API reference documentation with new volume-extended event.

References
==========

This blueprint is in conjunction with the work being done on the Cinder
extend attached volume. [2]_

.. [1] http://lists.openstack.org/pipermail/openstack-dev/2017-April/115292.html
.. [2] https://review.openstack.org/#/c/453286/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced


