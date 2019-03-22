..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Network Bandwidth resource provider
===================================

https://blueprints.launchpad.net/nova/+spec/bandwidth-resource-provider

This spec proposes adding new resource classes representing network
bandwidth and modeling network backends as resource providers in
Placement. As well as adding scheduling support for the new resources in Nova.


Problem description
===================

Currently there is no method in the Nova scheduler to place a server
based on the network bandwidth available in a host. The Placement service
doesn't track the different network back-ends present in a host and their
available bandwidth.

Use Cases
---------

A user wants to spawn a server with a port associated with a specific physical
network. The user also wants a defined guaranteed minimum bandwidth for this
port. The Nova scheduler must select a host which satisfies this request.


Proposed change
===============

This spec proposes Neutron to model the bandwidth resource of the physical NICs
on a compute host and their resources providers in the Placement service,
express the bandwidth request in the Neutron port, and modify Nova to consider
the requested bandwidth resource during the scheduling of the server based on
the available bandwidth resources on each compute host.

This also means that this spec proposes to use Placement and the nova-scheduler
to select which bandwidth providing RP and therefore which physical device will
provide the bandwidth for a given Neutron port. Today selecting the physical
device happens during Neutron port binding but after this spec is implemented
this selection will happen when an allocation candidate is selected for the
server in the nova-scheduler. Therefore Neutron needs to provide enough
information in the Networking RP model in Placement and in the resource_request
field of the port so that Nova can query Placement and receive allocation
candidates that are not conflicting with Neutron port binding logic.
The Networking RP model and the schema of the new resource_request port
attribute is described in `QoS minimum bandwidth allocation in Placement API`_
Neutron spec.

Please note that today Neutron port binding could fail if the nova-scheduler
selects a compute host where Neutron cannot bind the port. We are not aiming to
remove this limitation by this spec but also we don't want to increase the
frequency of such port binding failures as it would ruin the usability of the
system.


Separation of responsibilities
------------------------------

* Nova creates the root RP of the compute node RP tree as today
* Neutron creates the networking RP tree of a compute node under the compute
  node root RP and reports bandwidth inventories
* Neutron provides the resource_request of a port in the Neutron API
* Nova takes the ports' resource_request and includes it in the GET
  /allocation_candidate request. Nova does not need to understand or manipulate
  the actual resource request. But Nova needs to assign unique granular
  resource request group suffix for each port's resource request.
* Nova selects one allocation candidate and claims the resources in Placement.
* Nova passes the RP UUID used to fulfill the port resource request to Neutron
  during port binding

Scoping
-------

Due to the size and complexity of this feature the scope of the current spec
is limited. To keep backward compatibility while the feature is not fully
implemented both new Neutron API extensions will be optional and turned off by
default. Nova will check for the extension that introduces the port's
resource_request field and fall back to the current resource handling behavior
if the extension is not loaded.

Out of scope from Nova perspective:

* Supporting separate proximity policy for the granular resource request groups
  created from the Neutron port's resource_request. Nova will use the policy
  defined in the flavor extra_spec for the whole request as today such policy
  is global for an allocation_candidate request.
* Handling Neutron mechanism driver preference order in a weigher in the
  nova-scheduler
* Interface attach with a port or network having a QoS minimum bandwidth policy
  rule as interface_attach does not call scheduler today. Nova will reject
  interface_attach request if the port (passed in or created in network that is
  passed in) resource request in non empty.
* Server create with network having QoS minimum bandwidth policy rule as a port
  in this network is created by the nova-compute *after* the scheduling
  decision. This spec proposes to fail such boot in the compute-manager.
* QoS policy rule create or update on bound port
* QoS aware trunk subport create under a bound parent port
* Baremetal port having a QoS bandwidth policy rule is out of scope as Neutron
  does not own the networking devices on a baremetal compute node.

Scenarios
---------

This spec needs to consider multiple flows and scenarios detailed in the
following sections.

Neutron agent first start
~~~~~~~~~~~~~~~~~~~~~~~~~

The Neutron agent running on a given compute host uses the existing ``host``
neutron.conf variable to find the compute RP related to its host in Placement.
See `Finding the compute RP`_ for details and reasoning.

The Neutron agent creates the networking RPs under the compute RP with proper
traits then reports resource inventories based on the discovered and / or
configured resource inventory of the compute host. See
`QoS minimum bandwidth allocation in Placement API`_ for details.

Neutron agent restart
~~~~~~~~~~~~~~~~~~~~~

During restart the Neutron agent ensures that the proper RP tree exists in
Placement with correct inventories and traits by creating / updating the RP
tree if necessary. The Neutron agent only modifies the inventory and traits of
the RPs that were created by the agent. Also Neutron only modifies the pieces
that actually got added or deleted. Unmodified pieces should be left in place
(no delete and re-create).

Server create with pre-created Neutron ports having QoS policy rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The end user creates a Neutron port with the Neutron API and attaches a QoS
policy minimum bandwidth rule to it, either directly or indirectly by attaching
the rule to the network the port is created in. Then the end user creates a
server in Nova and passes in the port UUID in the server create request.

Nova fetches the port data from Neutron. This already happens in
create_pci_requests_for_sriov_ports in the current code base. The port contains
the requested resources and required traits. See
`Resource request in the port`_.

The create_pci_requests_for_sriov_ports() call needs to be refactored to a more
generic call that not just generates PCI requests but also collects the
requested resources from the Neutron ports.

The nova-api stores the requested resources and required traits in a new field
of the RequestSpec object called requested_resources. The new
`requested_resources` field should not be persisted in the api database as
it is computed data based on the resource requests from different sources in
this case from the Neutron ports and the data in the port might change outside
of Nova.

The nova-scheduler uses this information from the RequestSpec to send an
allocation candidate request to Placement that contains the port related
resource requests besides the compute related resource requests. The requested
resources and required traits from each port will be considered to be
restricted to a single RP with a separate, numbered request group as defined in
the `granular-resource-request`_ spec. This is necessary as mixing requested
resource and required traits from different ports (i.e. one OVS and one
SRIOV) towards placement will cause empty allocation candidate response as no
RP will have both OVS and SRIOV traits at the same time.

Alternatively we could extend and use the requested_networks
(NetworkRequestList ovo) parameter of the build_instance code path to store and
communicate the resource needs coming from the Neutron ports. Then the
select_destinations() scheduler rpc call needs to be extended with a new
parameter holding the NetworkRequestList.

The `nova.scheduler.utils.resources_from_request_spec()` call needs to be
modified to use the newly introduced `requested_resources` field from the
RequestSpec object to generate the proper allocation candidate request.

Later on the resource request in the Neutron port API can be evolved to support
the same level of granularity that the Nova flavor resource override
functionality supports.

Then Placement returns allocation candidates. After additional filtering and
weighing in the nova-scheduler, the scheduler claims the resources in the
selected candidate in a single transaction in Placement. The consumer_id of the
created allocations is the instance_uuid. See `The consumer of the port related
resources`_.

When multiple ports, having QoS policy rules towards the same physical network,
are attached to the server (e.g. two VFs on the same PF) then the resulting
allocation is the sum of the resource amounts of each individual port request.

Delete a server with ports having QoS policy rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
During normal delete, `local delete`_ and shelve_offload Nova today deletes the
resource allocation in placement where the consumer_id is the instance_uuid. As
this allocation will include the port related resources those are also cleaned
up.

Detach_interface with a port having QoS policy rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After the detach succeeds in Neutron and in the hypervisor, the nova-compute
needs to delete the allocation related to the detached port in Placement. The
rest of the server's allocation will not be changed.

Server move operations (cold migrate, evacuate, resize, live migrate)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During the move operation Nova makes allocation on the destination host
with consumer_id == instance_uuid while the allocation on the source host is
changed to have consumer_id == migration_uuid. These allocation sets will
contain the port related allocations as well. When the move operation succeeds
Nova deletes the allocation towards the source host. If the move operation
rolled back Nova cleans up the allocations towards the destination host.

As the port related resource request is not persisted in the RequestSpec object
Nova needs to re-calculate that from the ports' data before calling the
scheduler.

Move operations with force host flag (evacuate, live-migrate) do not call the
scheduler. So to make sure that every case is handled we have to go through
every direct or indirect call of `reportclient.claim_resources()` function and
ensure that the port related resources are handled properly. Today we `blindly
copy the allocation from source host to destination host`_ by using the
destination host as the RP. This will be lot more complex as there will be
more than one RP to be replaced and Nova will have a hard time to figure out
what Network RP from the source host maps to what Network RP on the
destination host. A possible solution is to `send the move requests through
the scheduler`_ regardless of the force flag but skipping the scheduler
filters.

.. note::
    Server move operations with ports having resource request are not
    supported in Stein.

Shelve_offload and unshelve
~~~~~~~~~~~~~~~~~~~~~~~~~~~

During shelve_offload Nova deletes the resource allocations including the port
related resources as those also have the same consumer_id, the instance uuid.
During unshelve a new scheduling is done in the same way as described in the
server create case.

.. note::
    Unshelve after Shelve offload operations with ports having resource
    request are not supported in Stein.


Details
-------

Finding the compute RP
~~~~~~~~~~~~~~~~~~~~~~

Neutron already depends on the ``host`` conf variable to be set to the same id
that Nova uses in the Neutron port binding. Nova uses the hostname in the port
binding. If the ``host`` is not defined in the Neutron config then it defaults
to the hostname as well. This way Neutron and Nova are in sync today. The same
mechanism (i.e. the hostname) can be used in Neutron agent to find the compute
RP created by Nova for the same compute host.

Having non fully qualified hostnames in a deployment can cause ambiguity. For
example different cells might contain hosts with the same hostname. This
hostname ambiguity in a multicell deployment is already a problem without the
currently proposed feature as Nova uses the hostname as the compute RP name in
Placement and the name field has a unique constraint in the Placement db model.
So in an ambiguous situation the Nova compute services having non unique
hostnames have already failed to create RPs in Placement.

The ambiguity can be fixed by enforcing that hostnames are FQDNs. However as
this problem is not special for the currently proposed feature this fix is out
of scope of this spec. The `override-compute-node-uuid`_ blueprint describes a
possible solution.

The consumer of the port related resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This spec proposes to use the instance_uuid as the consumer_id for the port
related resource as well.

During the server move operations Nova needs to handle two sets of allocations
for a single server (one for the source and one for the destination host). If
the consumer_id of the port related resources are the port_id then during move
operations the two sets of allocations couldn't be distinguished, especially in
case of resize to same host. Therefore the port_id is not a good consumer_id.

Another possibility would be to use a UUID from the port binding as consumer_id
but the port binding does not have a UUID today. Also today the port binding
is created after the allocations are made which is too late.

In both cases having multiple allocations for a single server on a single host
would make it complex to find every allocation for that server both for Nova
and for the deployer using the Placement API.

Separating non QoS aware and QoS aware ports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If QoS aware and non QoS aware ports are mixed on the same physical port then
the minimum bandwidth rule cannot be fulfilled. The separation can be achieved
at least on two levels:

* Separating compute hosts via host aggregates. The deployer can create two
  host aggregates in Nova, one for QoS aware server and another for non QoS
  aware servers. This separation can be done without changing either Nova or
  Neutron. This is the proposed solution for the first version of this feature.
* Separating physical ports via traits. The Neutron agent can put traits, like
  `CUSTOM_GUARANTEED_BW_ONLY` and `CUSTOM_BEST_EFFORT_BW_ONLY` to the network
  RPs to indicate which physical port belongs to which group. Neutron can offer
  this configurability via neutron.conf. Then Neutron can add
  `CUSTOM_GUARANTEED_BW_ONLY` trait in resource request of the port that is QoS
  aware and add `CUSTOM_BEST_EFFORT_BW_ONLY` trait otherwise. This solution
  would allow better granularity as a server can request guaranteed bandwidth
  on its data port and can accept best effort connectivity on its control port.
  This solution needs additional work in Neutron but no additional work in
  Nova. Also this would mean that ports without QoS policy rules would also
  have at least a trait request (`CUSTOM_BEST_EFFORT_BW_ONLY`) and it would
  cause scheduling problems with a port created by the nova-compute.
  Therefore this option can only be supported
  `after nova port create is moved to the conductor`_.
* If we use \*_ONLY traits then we can never combine them, though that would be
  desirable. For example it makes perfect sense to guarantee 5 gigabits of a
  10 gigabit card to somebody and let the rest to be used on a best effort
  basis. To allow this we only need to turn the logic around and use traits
  CUSTOM_GUARANTEED_BW and CUSTOM_BEST_EFFORT_BW. If the admin still wants to
  keep guaranteed and best effort traffic fully separated then s/he never puts
  both traits on the same RP. But one can mix them if one wants to. Even the
  possible starvation of best effort traffic (next to guaranteed traffic) could
  be easily addressed by reserving some of the bandwidth inventory.

Alternatives
------------

Alternatives are discussed in their respective sub chapters in this spec.


Data model impact
-----------------

Two new standard Resource Classes will be defined to represent the bandwidth in
each direction, named as `NET_BW_IGR_KILOBIT_PER_SEC` and
`NET_BW_EGR_KILOBIT_PER_SEC`. The kbps unit is selected as the
Neutron API already use this unit in the `QoS minimum bandwidth rule`_ API and
we would like to keep the units in sync.

A new `requested_resources` field is added to the RequestSpec versioned
object with ListOfObjectField('RequestGroup') type to store the resource and
trait requests coming from the Neutron ports. This field will not be persisted
in the database.

A new field ``requester_id`` is added to the InstancePCIRequest versioned
object to connect the PCI request created from a Neutron port to the resource
request created from the same Neutron port. Nova will populate this field with
the ``port_id`` of the Neutron port and the ``requester_id`` field of the
RequestGroup versioned object will be used to match the PCI request with the
resource request.

The  `QoS minimum bandwidth allocation in Placement API`_ Neutron spec will
propose the modeling of the Networking RP subtree in Placement. Nova will
not depend on the exact structure of such model as Neutron will provide the
port's resource request in an opaque way and Nova will only need to blindly
include that resource request to the ``GET allocation_candidates`` request.

Resource request in the port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Neutron needs to express the port's resource needs in the port API in a similar
way the resource request can be done via flavor extra_spec. For now we assume
that a single port requests resources from a single RP. Therefore Nova will map
each port's resource request to a single numbered resource request group as
defined in `granular-resource-request`_ spec. That spec requires that the name
of the numbered resource groups has a form of `resources<integer>`. Nova will
map a port's resource_request to the first unused numbered group in the
allocation_candidate request. Neutron does not know which ports are used
together in a server create request, and which numbered groups have already
been used by the flavor extra_spec therefore Neutron cannot assign unique
integer ids to the resource groups in these ports.

From implementation perspective it means Nova will create one RequestGroup
instance for each Neutron port based on the port's resource_request and insert
it to the end of the list in `RequestSpec.requested_resources`.

In case when the Neutron multi-provider extension is used and a logical network
maps to more than one physnet then the port's resource request will require
that the selected network RP has one of the physnet traits the network maps to.
This any-traits type of request is not supported by Placement today but can be
implemented similarly to member_of query param used for aggregate selection in
Placement. This will be proposed in a separate spec
`any-traits-in-allocation_candidates-query`_.

Mapping between physical resource consumption and claimed resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Neutron must ensure that the resources allocated in Placement for a port are
the same as the resources consumed by that port from the physical
infrastructure. To be able to do that Neutron needs to know the mapping between
a port's resource request and a specific RP (or RPs) in the allocation record
of the server that are fulfilling the request.

Nova will calculate which port is fulfilled by which RP and the RP UUID will be
provided to Neutron during the port binding.

REST API impact
---------------

Neutron REST API impact is discussed in the separate
`QoS minimum bandwidth allocation in Placement API`_ Neutron spec.

The Placement REST API needs to be extended to support querying allocation
candidates with an RP that has at least one of the traits from a list
of requested traits. This feature will be described in the separate
`any-traits-in-allocation_candidates-query`_ spec.

This feature also depends on the `granular-resource-request`_ and
`nested-resource-providers`_ features which impact the Placement REST API.

A new microversion will be added to the Nova REST API to indicate that server
create supports ports with resource request. Server operations
(e.g. create, interface_attach, move) involving ports having resource request
will be rejected with older microversion. However server delete and port detach
will be supported with old microversion for these server too.

.. note::
    Server move operations are not supported in Stein even with the new
    microversion.


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

* Placement API will be used from Neutron to create RPs and the compute RP tree
  will grow in size.

* Nova will send more complex allocation candidate request to Placement as it
  will include the port related resource request as well.

* Nova will calculate the mapping between each port's resource request and the
  RP in the overall allocation that fulfills such request.

As Placement do not seem to be a bottleneck today we do not foresee
performance degradation due to the above changes.

Other deployer impact
---------------------

This feature impacts multiple modules and creates new dependencies between
Nova, Neutron and Placement.

Also the deployer should be aware that after this feature the server create and
move operations could fail due to bandwidth limits managed by Neutron.


Developer impact
----------------

None

Upgrade impact
--------------

Servers could exist today with SRIOV ports having QoS minimum bandwidth policy
rule and for them the resource allocation is not enforced in Placement during
scheduling. Upgrading to an OpenStack version that implements this feature
will make it possible to change the rule in Neutron to be placement aware (i.e.
request resources) then (live) migrate the servers and during the selection of
the target of the migration the minimum bandwidth rule will be enforced by the
scheduler. Tools can also be provided to search for existing instances and try
to do the minimum bandwidth allocation in place. This way the number of
necessary migrations can be limited.

The end user will see behavior change of the Nova API after such upgrade:

* Booting a server with a network that has QoS minimum bandwidth policy rule
  requesting bandwidth resources will fail. The current Neutron feature
  proposal introduces the possibility of a QoS policy rule to request
  resources but in the first iteration Nova will only support such rule on
  a pre-created port.
* Attaching a port or a network having QoS minimum bandwidth policy rule
  requesting bandwidth resources to a running server will fail. The current
  Neutron feature proposal introduces the possibility of a QoS policy rule to
  request resources but in the first iteration Nova will not support
  such rule for interface_attach.

The new QoS rule API extension and the new port API extension in Neutron will
be marked experimental until the above two limitations are resolved.

Implementation
==============

Assignee(s)
-----------

Primary assignee:

  * balazs-gibizer (Balazs Gibizer)

Other contributors:

  * xuhj (Alex Xu)
  * minsel (Miguel Lavalle)
  * bence-romsics (Bence Romsics)
  * lajos-katona (Lajos Katona)

Work Items
----------

This spec does not list work items for the Neutron impact.

* Make RequestGroup an ovo and add the new `requested_resources` field to the
  RequestSpec. Then refactor the `resources_from_request_spec()` to use the
  new field.

* Implement `any-traits-in-allocation_candidates-query`_ and
  `mixing-required-traits-with-any-traits`_ support in Placement.
  This work can be done in parallel with the below work items as any-traits
  type of query only needed for a small subset of the use cases.

* Read the resource_request from the Neutron port in the nova-api and store
  the requests in the RequestSpec object.

* Include the port related resources in the allocation candidate request in
  nova-scheduler and nova-conductor and claim port related resources based
  on a selected candidate.

* Send the server's whole allocation to the Neutron during port binding

* Ensure that server move operations with force flag handles port resource
  correctly by sending such operations through the scheduler.

* Delete the port related allocations from Placement after successful interface
  detach operation

* Reject an interface_attach request that contains a port or a network having
  a QoS policy rule attached that requests resources.

* Check in nova-compute that a port created by the nova-compute during server
  boot has a non empty resource_request in the Neutron API and fail the boot if
  it has


Dependencies
============

* `any-traits-in-allocation_candidates-query`_ and
  `mixing-required-traits-with-any-traits`_ to support multi-provider
  networks. While these placement enhancements are not in place this feature
  will only support networks with a single network segment having a physnet
  defined.

* `nested-resource-providers`_ to allow modelling the networking RPs

* `granular-resource-request`_ to allow requesting each port related resource
  from a single RP

* `QoS minimum bandwidth allocation in Placement API`_ for the Neutron impacts

Testing
=======

Tempest tests as well as functional tests will be added to ensure that server
create operation, server move operations, shelve_offload and unshelve and
interface detach work with QoS aware ports and the resource allocation is
correct.


Documentation Impact
====================

* User documentation about how to use the QoS aware ports.


References
==========

* `nested-resource-providers`_ feature in Nova
* `granular-resource-request`_ feature in Nova
* `QoS minimum bandwidth allocation in Placement API`_ feature in Neutron
* `override-compute-node-uuid`_ proposal to avoid hostname ambiguity


.. _`nested-resource-providers`: https://review.openstack.org/556873
.. _`granular-resource-request`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/granular-resource-requests.html
.. _`QoS minimum bandwidth allocation in Placement API`: https://review.openstack.org/#/c/508149
.. _`override-compute-node-uuid`: https://blueprints.launchpad.net/nova/+spec/override-compute-node-uuid
.. _`vnic_types are defined in the Neutron API`:  > https://developer.openstack.org/api-ref/network/v2/#show-port-details
.. _`blindly copy the allocation from source host to destination host`: https://github.com/openstack/nova/blob/9273b082026080122d104762ec04591c69f75a44/nova/scheduler/utils.py#L372
.. _`QoS minimum bandwidth rule`: https://docs.openstack.org/neutron/latest/admin/config-qos.html
.. _`any-traits-in-allocation_candidates-query`: https://blueprints.launchpad.net/nova/+spec/any-traits-in-allocation-candidates-query
.. _`mixing-required-traits-with-any-traits`: https://blueprints.launchpad.net/nova/+spec/mixing-required-traits-with-any-traits
.. _`local delete`: https://github.com/openstack/nova/blob/4b0d0ea9f18139d58103a520a6a4e9119e19a4de/nova/compute/api.py#L2023
.. _`send the move requests through the scheduler`: https://github.com/openstack/nova/blob/9273b082026080122d104762ec04591c69f75a44/nova/scheduler/utils.py#L339
.. _`after nova port create is moved to the conductor`: https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/prep-for-network-aware-scheduling-pike.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
   * - Rocky
     - Reworked after several discussions
   * - Stein
     - * Re-proposed as implementation hasn't been finished in Rocky
       * Updated based on what was implemented in Stein
