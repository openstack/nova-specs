..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
PCI Passthrough Groups
======================

https://blueprints.launchpad.net/nova/+spec/pci-passthrough-groups

This spec proposes flavor PCI aliases for requesting static groups of PCI
devices. Nova will track and assign each group as one indivisible unit.

Problem description
===================

Some PCI devices must be assigned together to one VM. Nova's existing NUMA
affinity policies cannot express this requirement or prevent partial
allocation of such a group.

Some use cases allow a device to be consumed by multiple different groups
that are dynamically selected based on demand. These use cases are out of
scope for this proposal.
In particular, this proposal restricts each tracked PCI device to membership
of zero or one group. A device that belongs to a group can only be used as
part of that group.

Some GPUs expose both a graphics accelerator and an audio device. Passing
through both requires a matching pair from the same card. Allowing the same
card to be requested as a pair for one instance or as just the graphics
device for another is out of scope.

Each Graphcore C200 card presents two PCI devices that must be assigned
together. Multiple cards can also be connected via IPU-Link:
https://docs.graphcore.ai/projects/C600-datasheet/en/latest/product-description.html#ipu-link-cables

NVIDIA NVLink and AMD InfinityFabric connect GPU cards outside their individual
PCI connections. Sets of 4, 8, or more connected devices need to be assigned
together for workloads to use these connections.

Telco appliances can require devices grouped by function, connectivity, or
location. For example, cell transceiver A must be paired with network uplink B
and crypto accelerator C. Operators have worked around Nova's lack of grouping
by booting VMs on individual hosts in a specific order, or by changing
configuration so only the intended devices are available when booting a VM.

Operators also need to keep specific devices for host use, such as management
or storage NICs, while allowing other devices with the same vendor and
product IDs. Some GPUs use the same IDs for a PF and its VFs, but PCI in
Placement cannot expose both. Nova's existing inclusion-only configuration
requires address lists or regular expressions to select all matching devices
except those needed by the host.

Operators also need to generate and update PCI configuration through tools
such as Ansible and crudini. Nova uses oslo.config, which extends INI with
typed options and repeated multi-value options. Generic INI tools may reject
repeated keys or retain only the first or last definition, rather than collect
all definitions into a list as oslo.config does for multi-value options.
JSON lists allow group and alias definitions to be serialized as a single
value for each option.

Use Cases
---------

* As a GPU user, I would like to request a matching graphics and audio pair
  so that both devices from the same card are assigned to my VM.
* As an accelerator user, I would like to request both PCI devices of a
  Graphcore C200 card so that the card can operate in my VM.
* As a GPU user, I would like to request a connected set of GPUs so that my
  workload can use their inter-card connections.
* As a telco operator, I would like to request a transceiver, its network
  uplink, and its crypto accelerator together so that an appliance receives
  the intended devices without controlling VM boot order.
* As a cloud operator, I would like to manage PCI configuration through
  Ansible or crudini without repeated INI keys so that those tools retain
  all device, group, and alias definitions.


Proposed change
===============

Operators will define static groups through ``[pci]group_spec`` using devices
made eligible by ``[pci]device_spec``. Each group will have one unit of
Placement inventory and will be requested through a flavor PCI alias. Nova
will claim, allocate, and free all member devices as one indivisible unit.

The virt driver discovers the host's PCI devices. Nova will select devices
allowed by ``[pci]device_spec``, remove addresses in ``[pci]exclude_list``, and
apply ``[pci]group_spec`` membership and member indices. The PCI tracker will
reconcile the resulting groups and ungrouped devices with its existing state::

    Discover host PCI devices
                |
                v
    Select devices allowed by device_spec
                |
                v
    Remove addresses in exclude_list
                |
                v
    Apply group_spec membership and indices
                |
                v
    Reconcile groups and ungrouped devices
    with existing PCI tracker state

The flow shows how Nova will select eligible devices. Reconciliation will also
preserve instance-owned device state, as described in
`Changing an Existing Group`_. Configuration errors are covered in
`Validation Rules`_.

Configuring Groups
------------------

* A new multi-value config option ``[pci]group_spec`` will be defined.
  Each value defines a single PCI group by listing its devices' PCI addresses.
  The option also accepts a JSON list of group dictionaries.

* Each group in the ``[pci]group_spec`` is defined by 3 mandatory parameters:

  * ``addresses`` is an ordered list of strings of PCI addresses. No
    wildcarding is supported. Member-device eligibility under
    ``[pci]device_spec`` follows `Validation Rules`_.
    The first address has group member index 0, the second index 1, and so on.
    Nova will use these indices to map devices during live migration.
  * ``key`` uniquely identifies the group within a compute node. Nova will
    use this host-local identity for its device pool and Placement Resource
    Provider.
  * ``type`` is a free-form string identifying the logical unit formed by the
    member devices, such as two interconnected GPUs of a given model. It must
    have the same meaning across the deployment. Operators must use distinct
    types for groups whose device counts or compositions change that meaning.
    Multiple groups of a type can exist on one compute node or across the
    deployment. Group aliases will select this value, and Nova will derive the
    group's Placement resource class from it.

* Each group in the ``[pci]group_spec`` can have one optional parameter:

  * ``traits`` is a list of strings defining Placement custom traits nova will
    add to the Resource Provider representing the group.

  There is no ``resource_class`` field in ``group_spec``. The group's
  Placement resource class is derived from its user-defined ``type``.

* Group aliases use the new ``group_type`` field in ``[pci]alias`` to select
  a group type. The existing ``resource_class`` field remains supported for
  non-grouped devices only.

* The ``[pci]alias`` option will be extended to accept a JSON list of alias
  dictionaries in each value, for both ordinary device aliases and group
  aliases. Repeated options, JSON lists, and a combination of the two will be
  supported by ``group_spec`` and ``alias``, matching the existing JSON-list
  support in ``device_spec``. This proposal does not change ``device_spec``.
  Existing alias validation will apply to each dictionary, including
  restrictions on multiple definitions of the same alias when PCI in Placement
  is enabled.


Consider a host with ten PCI devices, ``0000:b0:00.0`` through
``0000:b9:00.0``. Each device has vendor ID ``10de`` and product ID ``233b``.
The devices on buses b0, b1, b2 and b3 form one connected set. The devices on
b4 and b5 form another, as do those on b6 and b7. The devices on b8 and b9 are
not cross-connected.

The boxes below show the connected sets. Here, ``b0`` abbreviates
``0000:b0:00.0``, and likewise for the other devices::

    gpu41, nvidia-gpu-4x       gpu21, nvidia-gpu-2x
    +--------------------+    +--------------------+
    | b0  b1  b2  b3     |    | b4  b5             |
    +--------------------+    +--------------------+

    gpu22, nvidia-gpu-2x       Individually consumable
    +--------------------+    +------+  +------+
    | b6  b7             |    | b8   |  | b9   |
    +--------------------+    +------+  +------+

The following configuration groups the devices based on their connections:

.. code-block:: ini

  [pci]
  device_spec = {"vendor_id": "10de", "product_id": "233b", "managed": "false", "live_migratable": "true"}

  group_spec = {"addresses": ["0000:b0:00.0", "0000:b1:00.0", "0000:b2:00.0", "0000:b3:00.0"], "type": "nvidia-gpu-4x", "key": "gpu41"}
  group_spec = {"addresses": ["0000:b4:00.0", "0000:b5:00.0"], "type": "nvidia-gpu-2x", "key": "gpu21"}
  group_spec = {"addresses": ["0000:b6:00.0", "0000:b7:00.0"], "type": "nvidia-gpu-2x", "key": "gpu22"}

  alias = {"name": "gpu-2x", "group_type": "nvidia-gpu-2x", "live_migratable": "true"}
  alias = {"name": "gpu-4x", "group_type": "nvidia-gpu-4x", "live_migratable": "true"}
  alias = {"name": "gpu-1x", "vendor_id": "10de", "product_id": "233b", "live_migratable": "true"}

With this configuration, nova-compute will track three groups and two
individually consumable devices. Flavors will be able to request either group
type or individual devices.

Devices listed in ``[pci]group_spec`` can only be consumed as part of their
group, not individually. A group can contain a single device. Nova will not
automatically convert ordinary devices into groups of one device.

The following rules apply to member-device tags when forming a group:

* A group is eligible for live migration only if every member device has
  ``live_migratable: true``. An unset or false member value makes the group
  ineligible. A group alias can request this property through
  ``live_migratable``. Group live migration is a stretch goal, as described in
  `Live Migration Support`_.
* A group is one-time use, or OTU, if any member device has
  ``one_time_use: true``.
* Groups will ignore device-level ``resource_class`` and ``traits`` tags.
  Group traits must be defined directly in ``[pci]group_spec``.
* ``managed`` is not inherited by the group. When generating the guest XML,
  Nova will use the ``managed`` value of each underlying device.
* The rest of the tags will apply only to individual devices and will not be
  inherited by the group.

.. note::

   PCI in Placement does not yet support devices with ``physical_network``
   tags, which are requested through Neutron ports. Such devices cannot be
   added to PCI groups.

An alias using ``group_type`` requests the whole group atomically. The
following rules apply to group aliases:

* ``vendor_id`` and ``product_id``: not supported. A group can have a diverse
  set of PCI vendors and products.
* ``device_type``: not supported. A group can have a diverse set of PCI, PF,
  and VF devices.
* ``numa_policy``: Supported. See the separate section below for what it means
  for groups.
* ``traits``: Supported. The group must provide every trait requested by
  the alias.
* ``live_migratable``: Supported to request a live migratable group.

PCI grouping builds on PCI in Placement and inherits its limitations. See
https://docs.openstack.org/nova/latest/admin/pci-passthrough#pci-tracking-in-placement

Excluding Devices
-----------------

The new ``[pci]exclude_list`` option contains PCI address strings and defaults
to an empty list. Each entry must be a complete PCI address in
``domain:bus:slot.function`` form. Wildcards and regular expressions are not
supported.

Exclusion takes precedence over permission from ``[pci]device_spec``.
An address excludes only the device at that address. Excluding a PF does not
exclude its VFs, even when they share vendor and product IDs.

Operators can include devices by vendor/product ID and then exclude devices
used by the host, such as NICs used for management or storage, while keeping
other NICs assignable to instances. This natively supports NIC partitioning.
For example, a host with four matching NICs can keep one for host use,
expose two as a group, and leave the fourth individually consumable:

.. code-block:: ini

    [pci]
    device_spec = {"vendor_id": "8086", "product_id": "1533"}
    exclude_list = 0000:03:00.0
    group_spec = {"addresses": ["0000:04:00.0", "0000:05:00.0"], "key": "nic_pair1", "type": "nic_pair"}
    alias = [{"name": "nic-pair", "group_type": "nic_pair"},
             {"name": "nic", "vendor_id": "8086", "product_id": "1533"}]

Some NVIDIA GPUs that support partitioning through VFIO-PCI variant drivers
use the same vendor and product IDs for their PF and VFs. Including devices
by those IDs would include both the PF and its VFs, violating the restriction
in `Dependent Device Handling`_. An address-only exclusion of the PF leaves
the VFs eligible without requiring their addresses in ``device_spec``.

For example, using ``1234`` as an illustrative product ID to replace with
the hardware's actual ID, and ``0000:06:00.0`` as the PF address:

.. code-block:: ini

    [pci]
    device_spec = {"vendor_id": "10de", "product_id": "1234"}
    exclude_list = 0000:06:00.0
    alias = [{"name": "gpu-vf", "vendor_id": "10de", "product_id": "1234", "device_type": "type-VF"}]

The exclusion affects only the named PF, not VFs sharing its IDs. If those
VFs are grouped, ``group_spec`` still requires their explicit addresses.
Multiple exclusions use a comma-separated list, for example::

    exclude_list = 0000:06:00.0,0000:07:00.0

An excluded device is not admitted to Nova's inventory. Removal of previously
tracked devices follows the lifecycle rules in `Changing an Existing Group`_.

The exclusion list is distinct from ``managed=false``, which controls
libvirt's management of a device's driver, and from ``remote_managed``,
which describes remote management of ``Off Path`` DPUs requested through
Neutron ports.

Validation Rules
----------------

The following configuration validation checks will be enforced for
``[pci]group_spec``:

* PCI groups require ``[pci]report_in_placement = True`` and
  ``[filter_scheduler]pci_in_placement = True``.
* An address appearing in both ``[pci]group_spec`` and
  ``[pci]exclude_list`` is a hard startup configuration error when no member
  of the affected group is claimed or allocated. If any member is claimed or
  allocated, nova-compute will instead log a warning and continue startup,
  preserving the group's device records, membership, indices, and instance
  ownership until final release. Neither the group nor its members will be
  available for new allocations. Nova will compare the configured addresses
  even if the hardware is absent from discovery, and report the conflicting
  group key and PCI address. Usage-dependent validation will use persisted
  PCI device state. Rejecting the configuration must preserve existing device
  records and instance ownership.
* Each group must contain at least one device. Every discovered member of a
  new or free group must be allowed by ``[pci]device_spec``; otherwise,
  nova-compute will reject startup. Claimed or allocated groups will retain
  ineligible members until final release, as described in
  `Changing an Existing Group`_.
* No address may be repeated in the group spec.
* Each PCI device can only be in either zero or one group
* The number of devices in each group of a ``type`` must be equal across
  the deployment. At startup, nova-compute will enforce this only among its
  own groups. When group live migration is implemented, its pre-checks will
  compare the source and destination. Operators remain responsible for
  consistent group definitions across compute nodes, since startup checks
  cannot validate other nodes.

The following configuration validation checks will be enforced for
``[pci]alias``:

* ``group_type`` is mutually exclusive with ``resource_class``, ``vendor_id``,
  ``product_id``, and ``device_type``. The alias JSON Schema must reject any
  entry combining ``group_type`` with one or more of these fields as a hard
  configuration error.
* A resource-class-only alias cannot request ``CUSTOM_PCI_GROUP_*`` inventory.
  It must use ``group_type`` instead.

Nova will reject invalid ``[pci]exclude_list`` entries when loading
configuration.
Duplicate addresses in ``exclude_list`` are invalid. An exclusion may name an
address that no ``device_spec`` entry allows.

Placement Integration
---------------------

Each PCI group will be represented in Placement as a single Resource
Provider (RP) that is a child of the compute node RP:

* ``RP Name``: ``{hostname}_group_{key}``
* Resource class is ``CUSTOM_PCI_GROUP_{TYPE}``, using the existing custom
  resource-class normalization rules. The group type is uppercased and
  non-alphanumeric characters are replaced with underscores. For example,
  ``nvidia-gpu-2x`` produces ``CUSTOM_PCI_GROUP_NVIDIA_GPU_2X``. The alias will
  use the same normalization for ``group_type``. Types that produce the same
  normalized resource class identify the same group type for inventory and
  alias matching.
* Total inventory is 1 because the group is an atomic unit. An instance
  consumes one unit when it allocates the group.
* Traits are those defined in the ``traits`` tag of the group definition.
  Groups with the same type should typically have identical traits.
  Divergent traits should not change the semantics of the group type.

Placement reporting will follow PCI tracker state. Nova must not offer an
incomplete or in-use group for a new allocation. Existing allocations must
remain intact when a member disappears. Device retention follows
`Changing an Existing Group`_, independently of Placement reconciliation.

If any device in the group has ``one_time_use: true``, Nova will set
``reserved: 1`` on the group inventory after allocation, while the instance
still owns the group, as in the existing individual-device ``one_time_use``
workflow. Placement permits this reservation of in-use inventory. The
reservation will remain after the instance releases a group that is still
configured and eligible, and Nova will not clear it. An external cleanup
agent must understand the group's membership, clean the relevant devices,
and then clear the group's reservation before reuse.

.. note::

   Providing a reference implementation of a group-aware external cleanup
   agent is out of scope.

Device Tracking and Scheduling
------------------------------

The ``extra_info`` field of the PCIDevice ovo will track group membership and
the zero-based ``group_member_index`` derived from configured address order.
This is a DictOfString field stored as a JSON blob in the DB. The tracker
will persist membership and indices across compute restarts.

Both ordinary and group aliases retain the existing request construction:
one ``InstancePCIRequest`` per flavor alias item with its requested count.
For a group alias, the count is the number of whole groups, not member
devices. For example, ``pair:2`` creates one PCI request with ``count=2``.
All member devices of both selected groups will share that request's
``request_id``; persisted group membership distinguishes the groups.

The existing expansion into Placement request groups applies to group aliases
without splitting the ``InstancePCIRequest``. A request with ``count=N``
generates N Placement request groups, each requesting one unit of the group's
resource class. Each can be fulfilled by a different nested resource provider
with one inventory unit. Ordinary device aliases retain their existing count
semantics.

Existing PCI lifecycle support, including cold migration, resize,
evacuation, and unshelve, will be preserved, subject to existing restrictions.
These operations must preserve whole-group allocation semantics.

PCI device pools (``PciDeviceStats``) will be extended to support groups:

* Group pools will use ``key`` field as the unique pool key rather than
  per-device attributes like address
* Non-group PCI requests cannot claim grouped devices (groups are
  filtered out for non-group requests)
* When a group is allocated, all devices are consumed atomically
  with the same ``request_id``

Live Migration Support
----------------------

Group live migration is a stretch goal targeted for the same release as core
PCI grouping. It may be deferred without delaying the rest of this proposal.
Until this support is implemented, Nova must reject live migration of instances
with PCI groups, even when every member is marked ``live_migratable='true'``.

Ordered membership and persisted member indices remain part of core grouping.
The following requirements apply when group live migration is implemented.

Live migration will preserve each original PCI ``request_id`` through
destination claims and migration completion or rollback. Within each request,
Nova will identify complete source and destination groups using their
persisted host-local group membership. Nova will pair equivalent whole groups,
then map their individual devices by ``group_member_index``. Each source group
must map wholly to one destination group. Group keys need not match across
hosts, and no stable ordering between equivalent groups is required. Selection
of the corresponding destination groups is an implementation detail.

Groups belonging to different PCI requests must not be paired, even if they
have the same group type. Keeping the original request boundaries preserves
their distinct specifications and NUMA policies. Destination claims must
satisfy the corresponding request's constraints.

For example, if the source group's addresses are ``[A, B]`` and the selected
destination group's addresses are ``[C, D]``, Nova will map A to C and B to D.
Address order defines the mapping, not discovery order or numeric address
sorting.

Live-migration pre-checks must verify that both sides contain the requested
number of complete groups of the requested type. Paired groups must have equal
sizes and matching complete member-index sets. Violations must be rejected
with a clear configuration error before constructing the device-address map.
Operators must ensure that devices at corresponding indices are compatible,
especially in groups containing mixed devices. Incompatible ordering is an
operator configuration error; Nova is not required to validate device-role
equivalence across hosts. Additional vendor/product compatibility checks can
remain an implementation detail.

NUMA Affinity Handling
----------------------

NUMA affinity policies will be evaluated across all devices in a group:

* ``required``: All devices in the group must have NUMA
  affinity to the guest NUMA nodes
* ``socket``: All devices must be on the same socket as the guest
* ``preferred/legacy``: The group with the most devices with affinity to the
  guest NUMA nodes will be selected. Groups will be sorted by NUMA affinity
  score, count of devices with affinity, but no groups will be rejected. The
  ``legacy`` policy for groups means the same as the ``preferred`` value.
  An alias without ``numa_policy`` defaults to ``legacy``, so group requests
  use preferred affinity by default.

Configuration Examples
----------------------

For example, consider the following PCI devices:

* 0000:4e:00.0 Processing accelerators: Graphcore Ltd Device 0003
* 0000:4f:00.0 Processing accelerators: Graphcore Ltd Device 0003
* 0000:89:00.0 Processing accelerators: Graphcore Ltd Device 0003
* 0000:8a:00.0 Processing accelerators: Graphcore Ltd Device 0003

The two physical cards (0000:4x and 0000:8x), spread across two NUMA nodes, can
be presented in two possible ways: either two groups or a single group,
depending on the use cases. For example, two separate groups would be:

.. code-block:: ini

    [pci]
    device_spec = {"vendor_id": "115D", "product_id": "0003"}
    group_spec = {"addresses": ["0000:4e:00.0", "0000:4f:00.0"], "key": "graphcore_1", "type": "c200_x1"}
    group_spec = {"addresses": ["0000:89:00.0", "0000:8a:00.0"], "key": "graphcore_2", "type": "c200_x1"}
    alias = {"name": "c200_x1", "group_type": "c200_x1"}

Or with the alternative JSON list syntax:

.. code-block:: ini

    [pci]
    device_spec = {"vendor_id": "115D", "product_id": "0003"}
    group_spec = [{"addresses": ["0000:4e:00.0", "0000:4f:00.0"], "key": "graphcore_1", "type": "c200_x1"},
                  {"addresses": ["0000:89:00.0", "0000:8a:00.0"], "key": "graphcore_2", "type": "c200_x1"}]
    alias = [{"name": "c200_x1", "group_type": "c200_x1"}]

Ordinary device aliases can also use JSON lists.

.. note::

   oslo.config accepts indented continuation lines for INI values. The JSON
   lists above do not need backslash escapes or to be collapsed onto one line.

Alternatively, both cards can form a single group of four PCI devices:

.. code-block:: ini

    [pci]
    device_spec = {"vendor_id": "115D", "product_id": "0003"}
    group_spec = {"addresses": ["0000:4e:00.0", "0000:4f:00.0", "0000:89:00.0", "0000:8a:00.0"], "key": "graphcore_1", "type": "c200_x2"}
    alias = {"name": "c200_x2", "group_type": "c200_x2"}

Changing an Existing Group
--------------------------

Nova will retain device records, group membership, member indices, and
instance ownership while any member is claimed or allocated. Releasing one
member does not release the rest of a group still held by an instance. This
state will persist across compute restarts until the instance releases its
final member, for example through deletion or migration. Placement allocations
and inventory reservations do not determine how long Nova will retain these
records.

Adding, removing, or moving member devices is supported only when none of the
affected devices or groups are claimed or allocated. This includes dissolving
a group into individual devices and converting individual devices into a
group. Reordering addresses changes member indices and is also a membership
change, even if the set of addresses is unchanged. Changing a group's ``key``
or ``type`` is subject to the same restriction. Nova-compute will fail startup
on unsafe changes without discarding existing records or ownership.

To replace a device in a free group, remove the old address and add the new
address at the intended index before restarting nova-compute. Nova will update
the group in one restart. Dissolving a free group also takes one configuration
update and restart. The resulting configuration must satisfy
`Validation Rules`_.

A released OTU device can still need cleanup. Operators must complete that
cleanup before making it available for reuse, including through regrouping.
A Placement inventory reservation prevents reuse but does not extend device
record retention.

If a configured member of a new or free group is absent from discovery,
nova-compute will continue startup with a warning identifying the group and
missing address. Nova will offer neither an incomplete group nor its remaining
configured members individually.

If a discovered member no longer matches ``device_spec``, nova-compute will
reject startup for a new or free group. For a claimed or allocated group,
nova-compute will instead log a warning and continue startup, retaining its
device records, membership, indices, and instance ownership until final
release. Neither the group nor its members will be available for new
allocations. After final release, Nova will remove no-longer-eligible devices
from tracking.

If a member of a claimed or allocated group disappears, nova-compute will log
a warning and continue startup so the operator can manage the host's remaining
VMs. Nova will retain the group's state and will not offer a partial group for
allocation. If the device returns with the same configuration, Nova will
continue using it. If the device returns after its configured group membership
has changed incompatibly, nova-compute will refuse startup. After final
release, Nova will remove missing devices from tracking.

A group/exclusion intersection on a free group is a configuration error under
`Validation Rules`_. If any member is claimed or allocated, nova-compute will
instead log a warning and continue startup, retaining the whole group's state
until final release and preventing new allocations. After final release, Nova
will remove excluded devices from tracking without allowing a new claim
between release and removal. Releasing the instance does not correct the
configured intersection. The operator must correct the exclusion list or group
membership before the next restart, subject to the membership-change
restrictions above.

Exclusion of a claimed or allocated ungrouped device will defer its removal.
Nova-compute will retain its device records and ownership, log a warning, and
continue startup. After the consuming instance releases it, Nova will remove
the device without allowing a new claim between release and removal. Placement
reconciliation will handle provider cleanup separately.

Dependent Device Handling
-------------------------

Dependent device handling concerns configurations where both a PF and its
child VFs are made available by ``[pci]device_spec`` after exclusions. PCI in
Placement does not support such configuration and therefore PCI grouping will
not support it either. Either the PF can be configured to be part of a single
group and by that whoever consumes that group gets the whole PF
and can manage VF creation in the guest. Or the VFs of the PF can be configured
but not the PF itself. In this case individual VFs can belong to the same or
different groups without any further restriction.

Alternatives
------------

For some simple cases, NUMA affinity can simulate what is required.
But currently hardware like Graphcore C200 does not work well with Nova.

Operators can approximate grouping by assigning custom resource classes to
individual devices and creating flavors that request every member. This relies
on keeping flavor counts aligned with group membership, since Nova does not
enforce whole-group consumption. The workaround also requires separate aliases
and flavors for groups that should be interchangeable. Native grouping will
enforce indivisible allocation and let one flavor request any complete group
of the specified type.

Wildcard or regex addresses in ``group_spec`` were considered but are deferred
to a future spec to keep this proposal's scope small. Group membership requires
explicit addresses.

Suppressing a free group containing an excluded member with only a warning
would let nova-compute start despite contradictory configuration. Nova will
instead reject the configuration so the operator can identify and correct the
conflicting group and exclusion. For a claimed or allocated group, Nova will
warn and retain its state until final release so the operator can manage or
move the workload. A device disappearing from hardware discovery is different.
The operator may need nova-compute running to manage or move the remaining
workloads before repairing the host.

Data model impact
-----------------

No database schema changes are required. Group membership and member indices
will be tracked via the existing ``extra_info`` JSON field on PCI device
objects. The new group pool type will use the existing dictionary-valued
``tags`` field of ``PCIDevicePool``. Nova will persist these pools as JSON in
the compute node's ``pci_stats`` database field.

REST API impact
---------------

No impact

Security impact
---------------

No impact

Notifications impact
--------------------

No impact

Other end user impact
---------------------

Users will request groups through flavor PCI aliases. The count is the number
of groups, not the number of member devices. Individual device requests will
not be able to consume devices assigned to a group, including a group with one
device.

Performance Impact
------------------

No impact

Other deployer impact
---------------------

Operators must enable PCI in Placement before defining groups, then configure
group definitions, aliases, and any exact-address exclusions. See
https://docs.openstack.org/nova/latest/admin/pci-passthrough#pci-tracking-in-placement

Invalid group or alias configuration can prevent compute startup, as described
in `Validation Rules`_. Operators must correct configuration errors; missing
hardware and exclusions of occupied devices or groups follow the separate
lifecycle behavior in `Changing an Existing Group`_.

Operators enabling OTU groups must use cleanup agents that understand group
membership and group reservations rather than treating each RP as one device.
Group live migration may be deferred to a later release. Once available, it
requires compatible member ordering across hosts.

Developer impact
----------------

None

Upgrade impact
--------------

The ``CUSTOM_PCI_GROUP_*`` resource class namespace is reserved for native PCI
grouping and is not configurable. Operators already using this prefix for
custom resource classes must discontinue that usage before adopting native
PCI grouping.

Rolling upgrades are supported without changing existing PCI configuration.
PCI grouping is opt-in through configuration changes. Operators should wait
until all nodes are upgraded before adopting it, but this recommendation is
not a mandatory activation gate.

Reconfiguring for Groups
~~~~~~~~~~~~~~~~~~~~~~~~

Devices to be exposed as a group must not be claimed or allocated to an
instance:

1. Ensure no instances have claims or allocations on the affected PCI devices.
2. Complete any required OTU cleanup before making the devices reusable.
3. Define groups via ``[pci]group_spec`` using devices allowed by
   ``[pci]device_spec`` and absent from ``[pci]exclude_list``.
4. Restart nova-compute to create the group resource providers.

The reverse transition requires the same checks. Remove the group definition
and restart nova-compute to expose its devices individually. Both transitions
follow the safety rules in `Changing an Existing Group`_.

Rolling Upgrade Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When upgrading a deployment:

* New resource classes (``CUSTOM_PCI_GROUP_*``) appear in Placement when
  upgraded nova-compute services restart with group configurations
* The scheduler will naturally gate usage to upgraded compute nodes since
  older nodes will not report the new group resource classes
* No REST API changes are required.
* Services must be upgraded before group aliases are configured on them.
  Older services cannot parse aliases containing ``group_type``.
* Flavors with group aliases can be created before all computes are
  upgraded, once the services interpreting those aliases support them;
  scheduling will only select upgraded hosts. Waiting until all nodes are
  upgraded remains the recommended adoption workflow.

Backward Compatibility
~~~~~~~~~~~~~~~~~~~~~~

* Existing non-group PCI passthrough configurations continue to work.
  Both ordinary and group aliases retain the existing ``InstancePCIRequest``
  construction and Placement request-group expansion. Counts represent
  individual devices for ordinary aliases and whole groups for group aliases.
* There is no automatic migration from individual device tracking to
  group tracking; operators must explicitly reconfigure

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sean-k-mooney

Feature Liaison
---------------

Feature liaison:
  sean-k-mooney

Work Items
----------

The ``[pci]exclude_list`` enhancement will be completed first, before the
remaining enhancements:

* Add exact-address exclusion configuration, validation, and tracker handling.
* Add group configuration parsing and validation, and alias JSON list support.
* Support group alias counts using the existing PCI request construction and
  Placement request-group expansion.
* Add group pools, persisted membership and indices, and atomic claim,
  allocation, and release handling.
* Implement safe reconfiguration and device-state reconciliation.
* Extend PciPlacementTranslator with group inventory, traits, and OTU handling.
* Reject live migration of instances with PCI groups until group live-migration
  support is available.
* Extend the Cyborg DevStack plugin for simulated group configuration and add
  whitebox Tempest tests to ``nova-alt-configurations``.
* Update the admin guide and add a release note.

As a stretch goal for the same release, add group live migration by pairing
whole groups within each PCI request and mapping their members by index.

Dependencies
============

Integration testing depends on group configuration support in the Cyborg
DevStack plugin and PCI grouping tests in whitebox Tempest. These components
are test dependencies only; PCI grouping does not require Cyborg at runtime.

Testing
=======

All functionality will have unit and functional test coverage using Nova's
existing fixtures, including fake libvirt. Coverage will include configuration
validation, group requests and atomic allocation, tag handling, device
reconciliation, and safe reconfiguration, including persisted membership and
indices, and multiple groups sharing a PCI request ID. Tests will verify
rejection of group live migration until the stretch goal is implemented. If
delivered, group live-migration coverage will include whole-group pairing
within each request, differing host-local group keys and inter-group ordering,
member-index mapping, invalid group counts and membership, distinct requests
with different NUMA policies, completion, and rollback. Existing non-group PCI
behavior will retain regression coverage.

Exclusion coverage will verify startup rejection for free-group intersections
and warning and state retention for occupied groups, including across restarts
and partial member release. Final-release tests will verify removal of excluded
devices without reuse and startup rejection if the configured intersection
remains.

Tempest and pci-sim integration testing will provide additional coverage.
The ``nova-alt-configurations`` job will use pci-sim through the Cyborg
DevStack plugin and run whitebox Tempest tests for whole-group assignment and
isolation from ordinary device requests. The plugin will configure simulated
groups, Nova PCI settings, and flavors. Cyborg services will not be enabled.
CI job consolidation remains out of scope.

Documentation Impact
====================

The PCI admin guide, ``doc/source/admin/pci-passthrough.rst``, will document
group configuration and requests, exact-address exclusions, and operational
requirements for reconfiguration, OTU cleanup, and NUMA affinity. It will
include examples and configuration-error guidance for operators, and state
whether group live migration is supported in the release.

A release note will announce PCI groups and their configuration requirements
and limitations.

References
==========

* `Cyborg pci-sim
  <https://opendev.org/openstack/cyborg/src/branch/master/pci-sim>`_
* `Cyborg DevStack pci-sim integration
  <https://opendev.org/openstack/cyborg/src/branch/master/devstack/lib/pci_sim>`_

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.1 Caracal
     - Introduced
   * - 2026.2 Hibiscus
     - Updated with implementation details: configuration tags, validation
       rules, Placement integration design, pool and allocation semantics,
       live migration support, NUMA affinity handling, detailed work items,
       comprehensive testing plan, and documentation impact.
   * - 2027.1 Indri
     - Updated assignee, added alias JSON lists, single-device groups, and
       exact-address exclusions. Required group_type for group aliases while
       retaining existing PCI request count handling. Defined ordered member
       indices and whole-group live-migration mapping within each PCI request.
       Clarified tag rules, Nova-side device retention, schema-enforced
       alias-field mutual exclusion,
       usage-aware handling of group/exclusion conflicts, and OTU reservations.
       Prioritized exclusions and made group live migration a stretch goal.
       Planned first-party grouping tests using pci-sim, the Cyborg DevStack
       plugin, and whitebox Tempest.
