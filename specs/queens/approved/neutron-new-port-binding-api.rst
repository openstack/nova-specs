..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Use Neutron's new port binding API
===================================

Make use of Neutron's new port binding API in all cases where port binding
occurs. In the special case of move operations, the new API will allow us to
model both source and destination hosts having a port binding
which is not accounted for during live migration today.

https://blueprints.launchpad.net/nova/+spec/neutron-new-port-binding-api

Problem description
===================

The main motivation for the change is a selection of problems around
live-migration, in particular:

* If port binding would fail at destination, we would know that before
  starting the live-migration.
* In many cases the two hosts need a very different binding on source host
  vs destination host, but that's not possible today. In particular, macvtap
  live migration often needs different libvirt XML on source vs destination.
* In Mitaka, Neutron introduced a connection tracker based security group
  driver for ovs based backends. Live migrating between a host with a
  different security group driver is another motivating special case of
  the more general act of live migrating between different ml2 drivers which
  both require different libvirt XML definitions on the source and
  destination hosts.
* To make the switch between source and destination host as quickly as
  possible, it's good to get most things ready before the migration is started.
  We have added a short-term hack https://review.openstack.org/#/c/275073/
  for DVR, but let's do it properly.

More details can be found in the neutron spec:
https://specs.openstack.org/openstack/neutron-specs/specs/pike/portbinding_information_for_nova.html

When thinking about this spec, we should be clear on the difference between:

* port binding, the DB record in Neutron of what host and instance a port is
  associated with, and its current state.
* plug/unplug VIFs, where information from Neutron is passed to OS-VIF (or
  a legacy driver) to get the port ready on the host
* attaching the instances to the above preparations (via a tap device or
  PCI passthrough, etc)
* an active binding, the host where the traffic for associated port should
  go to, because that's where the VM is actually running

To address this problem statement we need to consider all the places where
we deal with port bindings, to use the new API flow.
We generally update the port bindings when a VM is moved.
The main API actions to consider are:

* Attach a port to an instance, including during spawning an instance
* Detach a port from an instance
* Live-migrate an instance, involves setting up the VIF on the destination
  host, before kicking off the live-migrate, then removing VIFs on source
  host once the live-migrate has completed.
* Migrate and resize are very similar to live-migrate
* Evacuate, we know the old host is dead, we want to kill any record of that
  old connection, and attach the port on the new host.
* Shelve, we want the port to stay logically attached to the instance, but
  we need to unbind the port for the host when the instance is offloaded.

In the move operations above neutron should be notified when the traffic needs
to be switched to the destination by activating the new port binding.

Use Cases
---------

As an admin, I want live migration to fail early during pre_live_migration
if it can be detected that network setup on the destination host
will not work.

As a user, I want minimal network downtime while my instance is
being live migrated.

As an operator, I want to start using new ML2 backends but need
to live migrate existing instances off of a different backend
with minimal network downtime.

As an operator, I want to leverage new security group implementations
and need to be able to live migrate existing instances from my
legacy hosts.

Proposed change
===============

There is no additional configuration for deployers.
The use of multiple bindings will be enabled automatically.
We decide whether to use the new or old API flow, if both compute nodes
support this feature and based on the available Neutron API extensions.
We cache extensions support in the usual way utilizing the existing
neutron_extensions_cache.

Note: The new neutron API extension will be implemented in the ml2 plugin
layer, above the ml2 driver layer so if the extension is exposed it will be
supported for all ml2 drivers. Monolithic plugins will have to implement
the extension separately and will continue to use the old workflow until
their maintainers support the new neutron extension.

The old interaction model should be removed when sufficient time has elapsed
for all neutron backends to support this model with an aim of completing this
in two cycles. We should keep this in mind in how the code is structured.
Given we are also looking at removing nova-network, we should see if this can
be added as a new set of network API calls, that are only for neutron, making
the existing calls needed for nova-network be no-ops for Neutron.

Migration across mixed software versions
----------------------------------------

If an old neutron is present then the existing workflow will be followed
regardless of the compute node version. Where a new neutron is deployed
that supports this feature the following behaviour will be implemented.

* If both compute nodes are queens or newer. In this case the new workflow
  will be used as described below.

* In all other cases the old workflow is used

Let's consider live-migration and what the calls to neutron will look like.

Today the workflow is documented here:
https://docs.openstack.org/nova/latest/reference/live-migration.html

Going forward the workflow will be altered as follows:

* Conductor does its pre-checks on the dest and source which
  creates the migrate_data object.

* Conductor checks the source and dest version to see if
  they support the new flow.

  * If new enough, conductor calls a new method on the dest
    compute to bind the port on the destination host.
    The new method will POST to /v2.0/ports/{port_id}/bindings passing
    just the destination host_id::

        {
          "binding": {
            "host_id": "target-host_id"
          }
        }

  * If this fails, the live migrate task can ignore that host and
    reschedule / retry another host because it's before we've cast
    to the source to start the live migration on the hypervisor.

  * If this succeeds, the port binding results are put into the
    migrate_data object which is sent to the source live_migration
    method, and after that all code that cares checks the new
    attribute in the migrate_data object.

  * The new attribute will consist of the minimal subset of the port
    binding response and will be encoded in a new nova object::

        fields = {
            'port_id': fields.StringField(),
            'host_id': fields.StringField(),
            'vnic_type': fields.StringField(),  # could be enum
            'vif_type': fields.StringField(),
            'vif_details': fields.DictOfStringsField(),
        }

    During implementation we will try to restrict the ``vif_details``
    field to the subset of vif_details required by nova to generate
    the updated domain xml and plug the vif. This is to avoid random
    ML2 backend-specific data from changing behavior in our versioned
    object. In the future this object will be replaced by one defined
    by os-vif.

* In pre_live_migration on destination:

  * Prior to the RPC call from live_migration on the source host to
    pre_live_migration on the dest host, start a wait thread for the
    vif-plugged event from Neutron, similar to during initial spawn.

    .. note:: This vif-plugged wait change can be made irrespective of this
        blueprint - it could be done as a bug fix or hardening opportunity.

  * Check if migrate_data contains new VIFs attribute, if so,
    plug vif on destination host using the new port bindings,
    else fall back to old workflow and plug vif with old vif bindings.

* At this point it is safe to start live migrating the instance.

  * This involves calling the virt driver to live migrate
    the instance and then activating the port binding. If migrate_data
    contains the new dest host port binding VIFs attribute, it will
    be used to configure the dest guest prior to starting the actual
    live migration in the hypervisor. This is in case the VIF type on
    the dest host is different from the source host.

  * In the example of the libvirt virt driver, we will wait for a qemu event
    on the source host called VIR_DOMAIN_EVENT_SUSPENDED_POSTCOPY,
    so we know the VM has just been paused by libvirt and mark the new
    port binding as active. This is described in more detail here:
    https://review.openstack.org/#/c/434870/

  * For other virt drivers the decision of when to activate the port
    binding is left to them. They may serialise the calls by activating
    the port binding immediately before or after migrating the instance
    or they may concurrently wait for an event if the hypervisor allows
    them to reduce the network downtime, or just activate the dest host
    port binding in post_live_migration.

* We should only hit an error here if the migration times out.
  If we hit any other error, there is no rollback and we just
  put the instance into the ERROR state. If we timeout we abort
  as described below.

* During post_live_migration:

  After cleaning up VIFs on the source host, we remove the old port binding
  associated with the source host. Should the operation get interrupted,
  there is enough information in the binding to ensure manual
  cleanup is feasible.

Aborts
------

* If the admin aborts an in-progress live migration, the rollback actions vary
  depending on what phase of the migration we are currently in.

* If we are in the pre_live_migration phase and have not started the migration
  we simply delete the destination port binding.

* If we have started the VM on the remote node and plugged the interface but
  not unpaused the instance, we unplug the instance, activate the source
  binding if required and delete the destination binding.

Other
-----

We can follow this pattern wherever there are VIFs present on two hosts, such
as during resize and migrate.

Evacuate is a special case, where we delete the port binding on the old host,
without knowing if it has had VIFs deleted, as we assume the host is dead and
will never be coming back to life.

With this change, live migration between hosts with different
neutron backends and/or security group drivers should be possible.
While not explicitly described in this spec the implementation of this
feature should not block that effort or the efforts to adopt oslo versioned
objects for nova / neutron portbinding negotiation, however, it is also not
dependent on either activity to be completed.

Alternatives
------------

We could leave live-migration broken for some Neutron drivers.

Note: there are additional plans to allow live-migrate to be used to switch
between different Neutron plugins, and allowing live-migrate for macvtap
attached SR-IOV, but this is not in scope for this change.

We could support live migration between mixed compute nodes.
In this case assuming neutron supported the new flow, the
following behaviour would be introduced.

* old source compute node and a new destination. Taking libvirt as an example,
  as the migration XML generation is done by the source node if the new
  destination compute node detects that an XML change would be required it
  should fail the migration. This changes existing behaviour where
  live migration may complete successfully but result in no network
  connectivity.

* new source compute node and an old destination.
  In this case, the source node can create the port binding and update
  the xml. There are 2 options with regard to activating the binding for
  the destination host. The source node can activate the binding before
  starting the live migration or after it succeeds. Pre-activating the
  binding will lead to more work should the migration fail, whereas
  activating the binding after migration success could increase network
  downtime. The option chosen is left to the review of the
  implementation to define and would be documented as a update to the
  existing live migration devref.

This has not been supported due to complexity of code and testing required.


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

There are extra API calls, but it should have little impact on performance.

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
  Sean Mooney (sean-k-mooney)

Work Items
----------

* Add the source/dest host version checks in conductor and the new
  compute RPC API method for creating the port binding on the destination
  host prior to initiating the live migration on the source host.
* Check for the new migrate_data attribute in the various compute methods
  related to live migration to determine if we are old or new flow.

Dependencies
============

* Neutron API changes, see spec: https://specs.openstack.org/openstack/neutron-specs/specs/pike/portbinding_information_for_nova.html

Testing
=======

Need functional tests for the new path.

Documentation Impact
====================

Need to update the developer docs to include details on
how Nova now interacts with Neutron during live migration.

References
==========

* Neutron spec: https://specs.openstack.org/openstack/neutron-specs/specs/pike/portbinding_information_for_nova.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced



