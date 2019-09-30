..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Nova - Cyborg Interaction
=========================

https://blueprints.launchpad.net/nova/+spec/nova-cyborg-interaction

This specification describes the Nova - Cyborg interaction needed to create
and manage instances with accelerators, and the changes needed in Nova to
accomplish that.

Problem description
===================

Scope
-----

Nova and Cyborg need to interact in many areas for handling instances with
accelerators. While this spec covers the gamut, specific areas are covered in
detail in other specs. We list all the areas below, identify which specific
parts are covered by other specs, and describe what is covered in this spec.

* Representation: Cyborg shall represent devices as nested resource providers
  under the compute node (except possibly for disaggregated servers),
  accelerator types as resource classes and accelerators as inventory in
  Placement. The properties needed for scheduling are represented as traits.
  This is specified by [#cy-nova-place]_. This spec does not
  dwell on this topic.

* Discovery and Updates: Among the devices discovered in a host, Cyborg
  intends to claim only those that are not included under the PCI Whitelisting
  mechanism. Cyborg shall update Placement in a way that is compatible with
  the virt driver's update of Placement. These aspects are addressed in
  sections `Coexistence with PCI whitelists`_ and `Placement update`_
  respectively.

* User requests for accelerators: Users usually request compute resources via
  flavors. However, since the requests for devices may be highly varied,
  placing them in flavors may result in flavor explosion. We avoid that by
  expressing device requests in a device profile [#dev-prof]_ . The
  relationship between device profiles and flavors is explored in Section
  `User requests`_.

  When an instance creation (boot) request is made, the contents of a device
  profile shall be translated to request groups in the request spec; the
  syntax in request groups is covered in Section `Updating the Request Spec`_.

* Instance scheduling: Nova shall use the Placement data populated by Cyborg
  to schedule instances. This spec does not dwell on this topic.

* Assignment of accelerators: We introduce the concept of Accelerator Request
  objects in Section `Accelerator Requests`_.  The workflow to create and use
  them is summarized in Section `Nova changes for Assignment workflow`_. The
  same section also highlights the Nova changes needed. The details of the
  Cyborg API implementation for this workflow is covered in Cyborg specs
  ([#cy-api-impl]_).

* Instance operations: The behavior with respect to accelerators for all
  standard instance operations are defined in [#inst-ops]_.
  This spec does not dwell on this topic.

Use Cases
---------

* A user requests an instance with one or more accelerators of different
  types assigned to it.
* An operator may provide users with both Device as a Service or
  Accelerated Function as a Service in the same cluster (see
  [#cy-nova-place]_).

The following use cases are not addressed in Train but are of long term
interest:

* A user requests to add one or more accelerators to an existing instance.
* Live migration with accelerators.

Proposed change
===============

Coexistence with PCI whitelists
-------------------------------
The operator tells Nova which PCI devices to claim and use by configuring the
PCI Whitelists mechanism. In addition, the operator installs Cyborg drivers in
compute nodes and configures/enables them. Those drivers may then discover and
report some PCI devices. The operator must ensure that both configurations
are compatible.

Ideally, there should be a single way for the operator to identify which PCI
devices should be claimed by Nova and which by Cyborg. This could be along the
lines suggested in [#generic-dev-disc]_ or [#kosamara]_. If such a mechanism
could be agreed upon by all stakeholders, Cyborg could adopt it.

Until that point, the operator tells Cyborg which devices to claim by
using Cyborg's configuration file. The operator must ensure that this is
compatible with the PCI whitelists configured in Nova.

Placement update
----------------
Cyborg shall call Placement API directly to represent devices and
accelerators. Some of the intended use cases for the API invocation are:

* Create or delete child RPs under the compute node RP.
* Create or delete custom RCs and custom traits.
* Associate traits with RPs or remove such association.
* Update RP inventory.

Cyborg shall not modify the RPs created by any other component, such
as Nova virt drivers.

User requests
-------------

The user request for accelerators is encapsulated in a device profile
[#dev-prof]_, which is created and managed by the admin via the Cyborg API.

A device profile may be viewed as a 'flavor for devices'. Accordingly, the
instance request should include both a flavor and a device profile. However,
that requires a change to the Nova API for instance creation. To mitigate the
impact of such changes on users and operators, we propose to do this
in phases.

In the initial phase, Nova API remains as today. The device profile is folded
into the flavor as an extra spec by the operator, as below::

 openstack flavor set --property 'accel:device_profile=<profile_name>' flavor

Thus the standard Nova API can be used to create an instance with only the
flavor (without device profiles), like this::

 openstack server create --flavor f ....  # instance creation

In the future, device profile may be used by itself to specify accelerator
resources for the instance creation API.

Updating the Request Spec
-------------------------
When the user submits a request to create an instance, as described in Section
`User requests`_, Nova needs to call a Cyborg API, to get back the resource
request groups in the device profile and merge them into the request spec.
(This is along the lines of the scheme proposed for Neutron
[#req-spec-groups]_.)

..  _cyborg-client-module:

This call, like all the others that Nova would make to Cyborg APIs, is done
through a Keystone-based adapter that would locate the Cyborg service, similar
to the way Nova calls Placement. A new Cyborg client module shall be added to
Nova, to encapsulate such calls and to provide Cyborg-specific functionality.

VM images in Glance may be associated with image properties (other than image
traits), such as bitstream/function IDs needed for that image. So, Nova should
pass the VM image UUID from the request spec to Cyborg. This is TBD.

The groups in the device profile are numbered by Cyborg. The request groups
that are merged into the request spec are numbered by Nova. These numberings
would not be the same in general, i.e., the N-th device profile group may not
correspond to the N-th request group in the request spec.

When the device profile request groups are added to other request groups in
the flavor, the ``group_policy`` of the flavor shall govern the overall
semantics of all request groups.

Accelerator Requests
--------------------
An accelerator request (ARQ) is an object that represents
the state of the request for an accelerator to be assigned to an instance.
The creation and management of ARQs are handled by Cyborg, and ARQs are
persisted in Cyborg database.

An ARQ, by definition, represents a request for a single accelerator. The
device profile in the user request may have N request groups, each asking for
M accelerators; then ``N * M`` ARQs will be created for that device profile.

When an ARQ is initially created by Cyborg, it is not yet associated with a
specific host name or a device resource provider. So it is said to be in an
unbound state. Subsequently, Nova calls Cyborg to bind the ARQ to a host name,
a device RP UUID and an instance UUID. If the instance fails to spawn, Nova
would unbind the ARQ without deleting it. On instance termination, Nova would
delete the ARQs after unbinding them.

.. _match-rp:

Each ARQ needs to be matched to the specific RP in the allocation candidate
that Nova has chosen, before the ARQ is bound. Since Placement does not match
RPs to request groups, this must be done in the Cyborg client module of Nova
(`cyborg-client-module`_). The matching is done using the requester_id field
in the ``RequestGroup`` object ([#requester-id]_) as below:

* The order of request groups in a device profile is not significant, but it
  is preserved by Cyborg. Thus, each device profile request group has a unique
  index.
* When the device profile request groups returned by Cyborg are added to the
  request spec, the requester_id field is set to 'device_profile_<N>' for the
  N-th device profile request group (starting from zero). The device profile
  name need not be included here because there is only one device profile per
  request spec.
* When Cyborg creates an ARQ for a device profile, it embeds the device
  profile request group index in the ARQ before returning it to Nova.
* The matching is done in two steps:

  * Each ARQ is mapped to a specific request group in the request spec using
    the requester_id field.
  * Each request group is mapped to a specific RP using the same logic as the
    Neutron bandwidth provider ([#map-rg-to-rp]_).

Nova changes for Assignment workflow
------------------------------------
This section summarizes the workflow details for Phase 1. The changes needed
in Nova are marked with NEW.

NEW: A Cyborg client module is added to nova (`cyborg-client-module`_). All
Cyborg API calls are routed through that.

#. The Nova API server receives a ``POST /servers`` API request with a flavor
   that includes a device profile name.

#. NEW: The Nova API server calls the Cyborg API ``GET
   /v2/device_profiles?name=$device_profile_name`` and gets back the device
   profile request groups. These are added to the request spec.

#. The Nova scheduler invokes Placement and gets a list of allocation
   candidates. It selects one of those candidates and makes
   claim(s) in Placement. The Nova conductor then sends a RPC message
   ``build_and_run_instances`` to the Nova compute manager.

#. NEW: Nova calls the Cyborg API ``POST /v2/accelerator_requests`` with the
   device profile name. Cyborg creates a set of unbound ARQs for that device
   profile and returns them to Nova. (The call may originate from Nova
   conductor or the compute manager; that will be settled in code review.)

#. NEW: The Cyborg client in Nova matches each ARQ to the resource provider
   picked for that accelerator. See `match-rp`_.

#. NEW: The Nova compute manager calls the Cyborg API ``PATCH
   /v2/accelerator_requests`` to bind the ARQ with the host name, device's RP
   UUID and instance UUID. This is an asynchronous call which prepares or
   reconfigures the device in the background.

#. NEW: Cyborg, on completion of the bindings (successfully or otherwise),
   calls Nova's ``POST /os-server-external-events`` API with::

    {
       "events": [
          { "name": "arq_resolved",
            "tag": $arq_uuid,
            "server_uuid": $instane_uuid,
            "status": "ok" # or "failed"
          },
          ...
       ]
    }

#. NEW: The Nova virt driver waits for the notification, subject to the
   timeout mentioned in Section `Other deployer impact`_. It then calls
   the Cyborg REST API ``GET
   /v2/accelerator_requests?instance=<uuid>&bind_state=resolved``.

#. NEW: The Nova virt driver uses the attach handles returned from the Cyborg
   call to compose PCI passthrough devices into the VM's definition.

#. NEW: If there is any error after binding has been initiated, Nova
   must unbind the relevant ARQs by calling Cyborg API. It may then retry on
   another host or delete the (unbound) ARQs for the instance.

This flow is captured by the following sequence diagram, in which the Nova
conductor and scheduler are together represented as the Nova controller. The
ARQ creation is shown to happen in Nova compute manager only for concreteness;
it may be in the controller instead.

.. seqdiag::

     seqdiag {
         edge_length = 200;
         span_height = 15;
         activation = none;
         default_note_color = white;
         'Nova Controller'; 'Placement'; 'Cyborg'; 'Nova Compute';

         'Nova Controller' -> 'Cyborg' [label =
             "GET /v2/device_profiles?name=mydp"];
         'Nova Controller' <- 'Cyborg' [label =
             '{"device_profiles": $device_profile}'];
         'Nova Controller' -> 'Nova Controller' [label=
             'Merge request groups into request_spec'];
         'Nova Controller' -> 'Placement' [label=
             'Get /allocation_candidates'];
         'Nova Controller' -> 'Placement' [label=
             'allocation candidates with nested RPs'];
         'Nova Controller' -> 'Nova Controller' [label=
             'Select a candidate'];
         'Nova Controller' -> 'Nova Compute' [label=
             'build_and_run_instances()'];
         'Nova Compute' -> 'Cyborg' [label=
             'POST /v2/accelerator_requests'];
         'Nova Compute' <- 'Cyborg' [label=
             '{"arqs": [$arq, ...]'];
         'Nova Compute' -> 'Cyborg' [label=
             'PATCH /v2/accelerator_requests'];
         'Nova Compute' <- 'Cyborg' [label=
             '{"arqs": [$arq, ...]'];
         'Cyborg' -> 'Nova Controller' [label=
             'POST /os-server-external-events'];
         'Nova Compute' -> 'Nova Compute' [label=
             'Wait for notification from Cyborg'];
         'Nova Compute' -> 'Cyborg' [label=
             'GET /v2/accelerator_requests?
             instance=$uuid&bind_state=resolved'];
         'Nova Compute' <- 'Cyborg' [label=
             '{"arqs": [$arq, ....]}'];
     }


Alternatives
------------
It is possible to have an external agent create ARQs from device profiles
by calling Cyborg, and then feed those pre-created ARQs to the Nova instance
creation API, analogous to Neutron ports. We do not take that approach yet
because it requires changes to Nova instance creation API.

It is possible to have the Nova virt driver poll for the Cyborg ARQ binding
completion. That is not preferable, partly because that is not the pattern of
interaction with other services like Neutron.

Data model impact
-----------------

None

REST API impact
---------------

None. A new extra_spec key ``accel:device_profile_name`` is added to
the flavor.

Security impact
---------------

None

Notifications impact
--------------------

Nova may choose to add additional notifications for Cyborg API calls.

Other end user impact
---------------------

None

Performance Impact
------------------

The extra calls to Cyborg REST API may potentially impact Nova
conductor/scheduler throughput. This has been mitigated by making some
critical Cyborg operations as asynchronous tasks.

Other deployer impact
---------------------

The deployer needs to set up the ``clouds.yaml`` file so that Nova
can call the Cyborg REST API.

The deployer needs to configure a new tunable in ``nova-cpu.conf``::

 * arq_binding_timeout (integer): Time in seconds for Nova compute
   manager to wait for Cyborg to notify that ARQ binding is done.
   Timeout is fatal, i.e., VM startup is aborted with an exception.
   Default: 300.

Developer impact
----------------

Define two new standard resource classes: FPGA and PGPU.

We have VGPU and VGPU_DISPLAY_HEAD RCs defined already. But we propose a
PGPU as a different RC for the following reasons:

 * Both VGPU and VGPU_DISPLAY_HEAD RCs specifically refer to virtual GPUs.
   We need a different one for physical GPUs.
 * It will be subject to separate quotas/limits in Keystone.
 * Using PCI_DEVICE RC is too general: we want quotas for GPU RC
   specifically.

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Sundar Nadathur

Work Items
----------

See the steps marked NEW in `Nova changes for Assignment workflow`_ section.

Dependencies
============

* Specification for device profiles [#dev-prof]_.
* Cyborg API specification [#cy-api]_.

Testing
=======
There need to be unit tests and functional tests for the Nova changes.
Specifically, there needs to be a functional test fixture that mocks the
Cyborg API calls.

There need to be tempest tests for the end-to-end flow, including failure
modes. The tempest tests should be targeted at a fake driver (in addition to
real hardware, if any) and tied to the Nova Zuul gate.

Documentation Impact
====================
Device profile creation needs to be documented in Cyborg, as noted in
[#dev-prof]_.

The need for operator to fold the device profile into the flavor needs to be
documented.

References
==========

.. [#cy-nova-place] `Specification for Cyborg Nova Placement
   interaction <https://review.openstack.org/#/c/603545/>`_

.. [#dev-prof] `Device profiles specification
   <https://review.openstack.org/602978>`_

.. [#cy-api-impl] `Specification for Cyborg API implementation
   <https://review.openstack.org/#/c/608624/>`_

.. [#inst-ops] `Specification for instance operations with accelerators
   <https://review.openstack.org/#/c/605237/>`_

.. [#generic-dev-disc] `Generic device discovery
   <https://review.openstack.org/#/c/603805/>`_

.. [#kosamara] `Modelling passthrough devices for report to placement
   <https://review.openstack.org/#/c/591037/>`_

.. [#req-spec-groups] `Store RequestGroup objects in RequestSpec
   <https://review.openstack.org/#/c/567267/>`_

.. [#requester-id] `Requester_id field in RequestGroup
   <https://git.openstack.org/cgit/openstack/nova/tree/nova/objects/request_spec.py?h=refs/changes/27/619527/16#n818/>`_

.. [#map-rg-to-rp] `Map request groups to resource providers
   <https://review.openstack.org/#/c/616239/33/nova/objects/request_spec.py/>`_

.. [#cy-api] `Specification for Cyborg API Version 2
   <https://review.opendev.org/658263/>`_

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
   * - Ussuri
     - Re-proposed
