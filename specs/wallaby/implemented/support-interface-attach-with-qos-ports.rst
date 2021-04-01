..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Support interface attach with QoS ports
=======================================

https://blueprints.launchpad.net/nova/+spec/support-interface-attach-with-qos-ports

Since `microversion 2.72`_ nova supports creating servers with neutron ports
having resource request. In the recent releases `support for the lifecycle
operations`_ with such ports have also been added. The next step is to support
attaching QoS ports to running instances.

Problem description
===================

Nova does not support attaching ports to a running instance if the port has
resource request. Such `interface attach is rejected`_ since Neutron added
support for port resource request in Stein.

Use Cases
---------

As an end user, I would like to add a new interface to my server that has QoS
minimum bandwidth rules and I want that such operation only succeeds if the
requested bandwidth can be guaranteed.

Proposed change
===============

The ``attach_interface`` RPC handler in the ComputeManager needs to be extended
with the following logic:

* Gather the port resource request from Neutron
* Call placement ``allocation_candidates`` API based on the port resource
  request, but restrict the query with an ``in_tree`` filter to the current RP
  tree.
* Select the first candidate and note the resource provider mapping of the
  candidate
* Update the instance allocation based on the selected candidate
* Update the ``InstancePciRequest`` of the port, if any, with the interface
  name of the parent physical device based on the device resource provider the
  port allocates from
* Do the PCI claim, if any, as today
* Pass the resource provider mapping to allocate_for_instance call candidate

A couple of new error cases needs to be handled. The ``attach_interface``
compute RPC call is synchronous so the error cases could lead to HTTP error
codes:

* Placement returns no allocation candidates then respond with  HTTP 400
  similarly to NoValidHost
* Updating the instance allocation fails due to resource conflict then retry
  with another candidate. If we run out of candidates then respond with HTTP
  400
* Updating the instance allocation fails due to generation conflict then
  reload allocations from placement and retry the update. If it still fails
  after 3 retries then respond with HTTP 409
* Updating the InstancePciRequest with parent interface name fails the respond
  with HTTP 400

All the error cases keep the server in ACTIVE state and record a failed
instance action. Also none of these are introducing new HTTP response code for
this API so no new microversion is needed.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

``POST /servers/{server_id}/os-interface`` with a Neutron port having resource
request will be accepted. This is a similar change to supporting move
operations with QoS ports and that was done without bumping a microversion. So
this change will also be made without a microversion bump.

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

An extra placement allocation candidate query needs to be made to select which
physical device can accommodate the additional resource request on the host and
then the instance allocation needs to be updated in placement based on the
selected candidate. These queries will only be run if the port has resource
request and the allocation candidate query will be restricted to the host the
instance is currently running on so the overall performance impact is limited.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

The main implementation of this feature will be in the ComputeManager in the
nova-compute service. So the compute service version needs to be bumped.
Currently, the API rejects such attach request. The related check in the API
needs to be replaced with a service level check to ensure that the attach is
only accepted if the compute service hosting the VM is new enough to support
the request.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  balazs-gibizer

Feature Liaison
---------------

Feature liaison:
  balazs-gibizer

Work Items
----------

See them in the `Proposed change`_ section

Dependencies
============

None

Testing
=======

Unit and functional testing will be provided for both normal and PCI device
backed interfaces. Tempest tests will be provided for normal ports only due to
the CI system limitation regarding SRIOV capable network devices.

Documentation Impact
====================

The API guide `Using ports with resource request`_ will be updated accordingly.
Also the Limitations section of the neutron admin guide
`Quality of Service Guaranteed Minimum Bandwidth`_ needs to be updated.


References
==========

.. _`microversion 2.72`: https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#maximum-in-stein
.. _`support for the lifecycle operations`: https://docs.openstack.org/api-guide/compute/port_with_resource_request.html
.. _`interface attach is rejected`: https://review.opendev.org/#/c/570078/
.. _`Using ports with resource request`: https://docs.openstack.org/nova/latest/admin/port_with_resource_request.html
.. _`Quality of Service Guaranteed Minimum Bandwidth`: https://docs.openstack.org/neutron/latest/admin/config-qos-min-bw.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
