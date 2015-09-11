..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Servicegroup foundational refactoring for Control Plane
=======================================================

https://blueprints.launchpad.net/nova/+spec/servicegroup-api-control-plane

At present, there are various interfaces through which services data can
be manipulated - admin interface(nova-manage), extensions
(contrib/services.py), etc. Every interface relies on the servicegroup
layer API is_up() to get details about service liveness. The proposal
is keep service data in nova database nova.services table and fetch
the liveness information from the configured servicegroup(SG) driver.
Liveness will be a combination of service liveness and RPC liveness,
where the latter will be computed based on information in nova.services.


Problem description
===================

Nova's way for determining service liveness is not pluggable. In
its current state of art, the services information is stored in nova
database in nova.services tables. Whereas, the service liveness
information is computed by the is_up() call. This is_up() call is
implemented depending on what backend servicegroup driver is chosen.

Right now other SG drivers are not functional and need to be
revamped to allow them be involved in giving details about service
liveness. That will be covered as part of separate spec.

The scope of this spec is limited to :-

1. Making sure the 2 separate interfaces mentioned above namely the
REST API interface and admin interface use the servicegroup layer API
while fetching service liveness.

2. Service.is_up will be an attribute for the Service object which
will be computed as a combination of service liveness and rpc
liveness. Service liveness will be implemented by the respective
SG driver and depending whether the service is up/down a boolean will
be returned. Whereas to check rpc liveness Nova will still rely on
the nova.services table stored in Nova database.

Use Cases
---------

This is a refactoring effort and can be applicable for following
usecases:

1. As an operator, I want to use zookeeper to achieve quick detection
of service outages. Zookeeper servicegroup driver will be used to report
service liveness although service data will still reside in
nova.services.

2. As an operator, I want to be sure that when Nova service
delete (REST api) is invoked the service record from respective backend
either Zookeeper or Memcache is removed. A SG api to leave() the group, which
will be added as part of this change, will be invoked.

Deployment using Database servicegroup driver to manage service
liveness will remain the same apart from including the logic to include
is_up as service object attribute and computing as proposed in the
"Proposed change" section.

Project Priority
----------------

None

Proposed change
===============

1. Proposed change is to fetch service data from DB and verify service
liveness using configured SG driver. The details of how the service
liveness will be configured by each driver is upto the implementation
details of each SG driver. Point #3.2.2 has details for how the Zookeeper
SG will compute it.

2. By storing the Service data in the database but the service liveness
information can be managed by the respective servicegroup driver
configured. Also, we have things like service version, which will require
some efficient version calculations in order to drive things like compute
rpc version pinning and object backporting. That can be done efficiently
if the services data is stored in database (as database supports max/min
functionality) as opposed to storing in Zookeeper or Memcache.

3. Change for the service liveness API we can have two options like this :

    def service_is_up(self, member):
    """Check if the given member is up."""

        A] For DB SG driver:

          #1. Check RPC liveness using the updated_at attribute
              in nova.services table.

          #2. Check Service liveness depending upon the SG database
              drivers is_up() method.

        B] For Zookeeper/Memcache SG drivers:

          The Service object will be the interface by which we determine
          whether a service is up or down. It will necessarily look up the
          updated_at stamp like it does now, and will optionally consult an
          external interface (such as zookeeper, memcache) through a defined
          interface. The external interface depends on the kind of SG driver
          configured as part of CONF.servicegroup_driver. If either indication
          results in a "down" verdict, the service will be considered
          down. Please note both the steps below will be needed to detect
          service liveness.

          #1. Check RPC liveness using the updated_at attribute
              in nova.services table.

          #2. Check Service liveness depending upon the Zookeeper
              SG driver or Memcache SG driver is_up() method.

              #2.1: If Znode for the compute host has not joined
                    the topic 'compute' then the nova-compute service
                    is not running on this compute host. The details
                    on how the Zookeeper ephemeral znode will maintain
                    the service representational state and how to migrate
                    from existing database servicegroup driver to
                    zookeeper/memcache SG driver has been covered
                    in https://review.openstack.org/#/c/138607.

4. A SG api to leave a group need to be introduced to the SG layer
and will be implemented by backend drivers. The drivers that don't need
the leave functionality will not provide any additional logic to
free up the service record associated with the service. For example
the znodes used to keep track of service when using Zookeeper SG driver
are ephemeral which means that they will be automatically deleted
when the service is deleted. But for other backends like memcache which
are key/value stores the record needs to be cleared off explicitly. The
api at the SG layer might look like :

    def leave(self, group_id, member)

As mentioned above depending on the driver used this can be already supported
if not need to explicitly call out to clean up the service entry.

5. The call will now just invoke service.is_up to check rpc liveness and
service liveness. Whereas at the object layer is_up will be computed as
a combination of when the service record was last updated which will give
details about RPC liveness and querying the respective CONF.sg_driver
for service liveness.

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

Service liveness is fetched from configured SG driver where as
service details will be fetched from nova database nova.services
tables. RPC liveness will also be computed based on the data in
nova.services table.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  vilobhmm

Other contributors:
  jaypipes, harlowja


Work Items
----------

- Introduce an additional attribute is_up to nova.objects.service.
- Fix admin interface, nova-manage where a service is_up/is_down
  will depend on the combination of service liveness depending on
  what SG driver is configured and RPC liveness computed based of
  information stored in nova.services table.
- Introduce leave() API at the SG layer to make sure when a service
  is deleted in situations where service liveness is maintained by
  backends other than db, the znode or the associated structure for
  the service is freed up.

Dependencies
============

None


Testing
=======

1. Existing unit tests will be updated to make sure the services
   data is fetched from nova.services tables and service liveness
   using servicegroup API.


Documentation Impact
====================

None


References
==========

- http://lists.openstack.org/pipermail/openstack-dev/2015-May/063602.html
- https://review.openstack.org/#/c/138607
- http://lists.openstack.org/pipermail/openstack-dev/2015-September/075267.html

.. _etherpad: https://etherpad.openstack.org/p/servicegroup-refactoring
