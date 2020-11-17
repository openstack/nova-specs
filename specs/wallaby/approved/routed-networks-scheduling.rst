..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Scheduling support for Routed Networks
======================================

https://blueprints.launchpad.net/nova/+spec/routed-networks-scheduling

Neutron provides network segments support thanks to Routed Networks where you
can create a port allocated to a specific segment. Unfortunately, Nova doesn't
verify the segment at every instance operation, including those where you move
an instance, which leads to inconsistencies.


Problem description
===================

Although it's possible to create a Neutron port with a routed networks setup
and boot an instance with this port, the network locality of the compute node
associated with the instance won't be verified by the scheduler and could
lead to a wrong scheduling decision. This is problematic when a move operation
sends an instance to a compute node that isn't in the network segment that is
related to the IP address that was allocated at boot time.

As a result of this gap, the only way to use routed networks in Nova currently
is by creating a port having the ``ip_allocation`` value be ``deferred`` and
making sure that all compute services are assigned to at least one network
segment.

Use Cases
---------

As an operator, I'd like to make sure that instances IP addresses can be
correctly separated between the network segments I provided.

As an operator, I don't want to see instances going to compute services that
aren't in network segments if the user asks for either a port or a routed
network.

As a user, I'd like Nova to place my instance on the correct host  according to
the port or network I've requested for my instance, without having to
specifically create a port with a ``ip_allocation=deferred`` value.


Proposed change
===============

Once you `configure routed networks in Neutron`_, network segments are
represented as Placement Resource Providers. Neutron will then ask Nova to
create a Nova host aggregate for each segment and will add compute services
that are mapped with respective segments into the related aggregates.
Eventually, Nova will mirror those aggregates into Placement aggregates.

What we then need for Nova is to have a way for asking the Placement API to
only get resource providers (i.e. compute nodes) that are in the aggregate
related to the segments that are in the network passed by the user (or related
to the port that is asked).

As Nova needs to find which segments are related and then which aggregates,
we could just provide a new pre-filter that would look at it if some
configuration option (say ``query_placement_for_routed_network_aggregates``)
would be ``True``.

A pseudo-code for it would be :

.. code::

  def support_routed_networks(ctxt, request_spec):
    if not CONF.query_placement_for_routed_network_aggregates:
      return False
    segment_ids = <get_all_segments_ids_from_network_or_port>
    for segment in segment_ids:
       agg_info = <get_provider_aggregates_from_segment_id>
       <append_agg_info_to_required_aggregates>

.. note::

  As said below in the `Alternatives`_ section, we could have Neutron passing
  directly the aggregates, so this pre-filter could be deprecated once we
  do it.


Alternatives
------------

Instead of having a new pre-filter, we could provide a specific scheduler
filter. This said, given we limit the number of allocation candidates returned
by Placement, we could miss some good resource providers so the filter couldn't
work.

Another alternative would be to have Neutron passing directly the needed
aggregate to Nova instead of Nova asking Neutron for it, but that would mean
that we should modify Neutron to return the Placement needed query in the
``port.resource_request`` attribute.

Data model impact
-----------------

We may need to augment the ``RequestSpec`` object to be able to provide in its
nested ``RequestLevelParams`` object attribute the specific aggregate.

REST API impact
---------------
None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

There could be a performance impact if we would verify the segments for every
instance in every cloud, but given we ask the operator to modify an option
if they want to use routed networks, we don't really think this would be an
issue.

Other deployer impact
---------------------

A new configuration option would be::

  cfg.BoolOpt("query_placement_for_routed_network_aggregates",
              default=False),

Developer impact
----------------

None.

Upgrade impact
--------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  bauzas

Other contributors:
  None

Feature Liaison
---------------

bauzas

Work Items
----------

* Create a new pre-filter that would find the related aggregate
* Pass the aggregate to the RequestSpec asking to verify it by Placement
* That's it.

Dependencies
============

None.

Testing
=======

Functional tests of course, but Tempest tests would be nice as well.

Documentation Impact
====================

Maybe modifying https://docs.openstack.org/neutron/latest/admin/config-routed-networks.html

References
==========

None.

.. _`configure routed networks in Neutron`: https://docs.openstack.org/neutron/latest/admin/config-routed-networks.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Victoria
     - Introduced, Approved
   * - Wallaby
     - Re-proposed
