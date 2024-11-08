..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode


==========================================
Use OpenStack SDK in Nova
==========================================

https://blueprints.launchpad.net/nova/+spec/openstacksdk-in-nova

We would like to use the OpenStack SDK to interact with other core OpenStack
services. Implementation began in Train and continues in Ussuri.


Problem description
===================

Nova is using both ``python-${service}client`` and keystoneauth1 adapters to
interact with other core services. Currently changes or fixes to a ``$service``
that Nova depends on may require changes to ``python-${service}client`` before
Nova can be brought into parity. This also requires the OpenStack SDK to be
brought into parity as it is used for the CLI.

Maintenance of ``python-${service}client`` can be burdensome due to high
technical debt in the clients. By consuming the OpenStack SDK directly, we can
eliminate the additional dependency on the ``python-${service}client`` and
streamline the process.

Use Cases
---------

As a developer on OpenStack, I would like to reduce the number of areas where
maintenance must be performed when making changes related to the use of core
OpenStack services.

As a core OpenStack project, Nova should make use of other projects in reliable
and maintainable ways. To this end, we should use the OpenStack SDK for service
to service interaction in place of direct API or ``python-${service}client``
implementations.


Proposed change
===============

This spec proposes to use the OpenStack SDK in place of
``python-${service}client`` and other methods across Nova in three phases for
each of the target services.

Target Services:
 * Ironic (python-ironicclient -> Baremetal SDK)
 * Cinder (python-cinderclient -> Block Storage SDK)
 * Glance (python-glanceclient -> Image v2 SDK)
 * Neutron (python-neutronclient -> Network SDK)
 * Placement (keystoneauth1 adapter -> OpenStack SDK Proxy)

The **initial phase** will consist of adding plumbing to construct an
openstack.connection.Connection object to Nova components that interact with
other services using a ``python-${service}client``. The service proxy from this
connection can then be used in place of existing keystoneauth1 adapter to
retrieve the endpoint to configure the client. This is in progress at
[[#sdk_in_nova]_].

The **main phase** will be to iterate through calls to the
``python-${service}client`` and replace them with calls into the OpenStack SDK
until the client is no longer needed. During this phase, we will close
feature deficiencies identified in the OpenStack SDK as necessary. See
`OpenStack SDK Changes`_ for a list of identified deficiencies. This process is
in progress for ``python-ironicclient`` at [[#sdk_for_ironic]_].

For Placement, replace the keystoneauth1 adapter returned by
``nova.utils.get_ksa_adapter('placement')`` with the SDK's placement proxy.
This is transparent other than a small number of changes to mocks in tests.
This is in progress at [[#sdk_for_placement]_]. Eventually, the SDK may
implement more support for placement. With the framework being in place, we can
consider integrating such changes as they become available.

The **final phase** will simply be to remove the now-unused clients and clean
up any remaining helpers and fixtures.



OpenStack SDK Changes
---------------------

The OpenStack SDK includes a more complete selection of helpers for some
services than others, but at worst provides the same primitives as a
keystoneauth1 adapter. Development has started with Ironic, which has robust
support within the OpenStack SDK. Other services will require additional work
in the OpenStack SDK, or may need to be implemented using the API primitives
provided by openstack.Proxy. It is more desirable to focus on expanding
OpenStack SDK support for these projects rather than implementing them in Nova.
Since there is not a spec repo for OpenStack SDK, we will try to outline the
missing helpers by service here.

| **Ironic**
| node.get_console
| node.inject_nmi
| node.list_volume_connectors
| node.list_volume_targets
| node.set_console_mode (available via ``patch_node``)
| volume_target.create
| volume_target.delete
|
| **Cinder**
| attachments.complete
| attachments.delete
| attachments.update
| volumes.attach
| volumes.begin_detaching
| volumes.detach
| volumes.initialize_connection
| volumes.migrate_volume_completion
| volumes.reserve
| volumes.roll_detaching
| volumes.terminate_connection
| volumes.unreserve
|
| **Glance**
| image.add_location
|
| **Neutron**
| None

Alternatives
------------

One possibility that was considered was to replace calls into
``python-${service}client`` with methods that invoke the ``$service`` APIs
directly through the keystoneauth1 adapter's ``get/put/etc`` primitives. This
would entail effectively porting the ``python-${service}client`` code into
nova. While this would give us the opportunity to clean things up, it would
involve a lot of low-level work like version discovery/negotiation, input
payload construction and validation, and output processing.

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

The initial phase will have minimal impact as the only change is the
construction of the keystoneauth1 adapter by the OpenStack SDK rather than
directly. The main phase will not likely have any difference in performance and
the final phase should approximately offset any impact from the initial phase.

Other deployer impact
---------------------

None

Developer impact
----------------

By using the OpenStack SDK as the single method of contact with other services,
the maintenance footprint can be reduced. This also moves us towards a more
stable OpenStack SDK as more consumers generally mean more chances to find and
resolve bugs.

In addition, as new methods and services are supported by the OpenStack SDK,
introducing them to Nova should be simpler and more reliable than the current
methods.

Upgrade impact
--------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dustinc <dustin.cowles@intel.com>

Other contributors:
  mordred <mordred@inaugust.com>, dtantsur <dtantsur@protonmail.com>

Feature Liaison
---------------

Feature liaison:
  efried

Work Items
----------

1. (Implemented in Train) Introduce package requirements to Nova.

2. (Partially implemented in Train) Introduce plumbing for the construction of
   an openstack.connection.Connection object for each ``$service``.

3. (Partially Implemented in Train) For each target ``$service`` (excluding
   Placement), close deficiencies in OpenStack SDK while replace invocations
   into ``python-${service}client`` one at a time, with calls into the SDK's
   ``$service`` proxy.

   * For Placement, replace the keystoneauth1 adapter with the
     SDK's placement proxy.

4. Remove the now-unused ``python-${service}client``, test fixtures, and other
   helpers and utils.


Dependencies
============

* Nova support for using keystoneauth1 config options for Cinder.

  * https://review.opendev.org/#/c/655985/


Testing
=======

Existing unit tests will need to be updated to assert calls to the SDK instead
of the client. In cases where the client call was mocked, this should be a
matter of swapping out that mock and its assertions. No significant additional
unit testing should be required.

Existing functional test cases should be adequate. Changes may be required in
fixtures and other framework.

Existing integration tests should continue to function seamlessly. This will be
the litmus test of success.


Documentation Impact
====================

None


References
==========

.. [#sdk_in_nova] https://review.opendev.org/#/c/643664/

.. [#sdk_for_ironic] https://review.opendev.org/#/c/642899/

.. [#sdk_for_placement] https://review.opendev.org/#/c/656023/

http://lists.openstack.org/pipermail/openstack-discuss/2019-May/005810.html

https://docs.openstack.org/openstacksdk/latest/user/config/configuration.html

http://eavesdrop.openstack.org/irclogs/%23openstack-sdks/%23openstack-sdks.2019-05-20.log.html#t2019-05-20T13:48:07

https://review.opendev.org/#/c/662881/

Items Implemented In Train
--------------------------
| https://review.opendev.org/#/c/676926/
| https://review.opendev.org/#/c/642899/
| https://review.opendev.org/#/c/656027/
| https://review.opendev.org/#/c/656028/
| https://review.opendev.org/#/c/659690/
| https://review.opendev.org/#/c/680649/
| https://review.opendev.org/#/c/676837/


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced, Partially Implemented
   * - Ussuri
     - Reintroduced
