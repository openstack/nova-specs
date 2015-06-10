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
(contrib/services.py), servicegroup API layer. Having different
interfaces to manipulate the source of truth can lead to severe
data inconsistency for something as useful as stored in nova.services.
The proposal is to follow a common path, while interacting with services
data, for all the three interfaces mentioned above. This common path will
go through the servicegroup API layer, who's primary purpose is to manage
and check for service liveliness. Doing so will help to overcome the
tight coupling between nova and services table and also have a
consistent view of services data, service liveliness, etc.


Problem description
===================

1. There is a tight coupling between nova and the nova.services
table. Before making a decision about liveliness of a service running
on a particular host nova refers to the services table which is
considered as a source of truth.

2. At present there are 3 interfaces, namely admin interface(nova-manage),
extensions, servicegroup API layer, from which the service information
is either accessed or modified.

3. Database servicegroup driver is the primary driver used by most of
the deployments. But for deployments using Zookeeper or Memcache
servicegroup driver, we will end up in severe data inconsistency given
that we have 3 different interfaces to modify the critical services
information which is stored in nova db.

4. There is no abstraction provided to choose a different backend
to store the service data. It is tightly coupled with database
as a backend and stored in nova.services table. Before Nova was
introduced to the world of objects, services data was fetched by making
database queries through the sqlalchemy layer. After the implementation
of the objects layer also the data is fetched from database. Just
the means to access data has changed not the location where the
services data is placed. This has been covered in more detail in
https://review.openstack.org/#/c/138607/. The scope of
of this spec is limited to calls accesing and fetching service data
and service liveliness information by enforcing all the
interfaces go through the servicegroup api layer.


Use Cases
---------

1. Deployment using Zookeeper servicegroup driver to manage service
liveliness : In this case, even though Zookeeper servicegroup
driver is being used to manage services and to report service
liveliness but the admin interface(nova-mange) and the extension
interface which act on nova.services table, which they consider
as the source of truth for services information, can lead to
severe data inconsistencies.

2. An operator uses admin interface, nova-manage service disable, to
mark a service down. Zookeeper won't be aware of this change and
still thinks service is up and running. So nova-manage only works
with database as the underlying backend. The admin interface uses
servicegroup layer for checking service liveliness but then does
db query to get the list of services. This is inconsistent with the
servicegroup driver API 'get_all' view on what is enabled/diabled.

3. An operator using Nova service delete(REST api) seems to follow
the similar broken pattern mentioned above and only works with
database as the underlying backend. This implementation is also
inconsistent with servicegroup driver API 'get_all' view of
services data.


Project Priority
----------------

None


Proposed change
===============

1. Proposed change is to enforce all the changes to services
data go through the servicegroup APIs.

2. Fix all places in the code which access/modify the services
data by querying/modifying nova.services and there are many
places in nova codebase which do that.

3. If the services information is stored in database, all the
interfaces will go through servicegroup API layer. New interfaces
will be added to servicegroup API to handle these changes. For
example update() call needs to be added so that admin interface
can change the state of the service using nova-manage, which will
eventually go through servicegroup API update().

4. If the services information is stored in Zookeeper or Memcache
all the interfaces which access/modify services data, service
liveliness information will go through servicegroup API. The details on
how the Zookeeper ephemeral znode will maintain the service
representational state and how to migrate from existing
database servicegroup driver to zookeeper servicegroup driver
has been covered in https://review.openstack.org/#/c/138607.


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

1. Inorder to fetch services details like service information, service
liveliness, the call should go through servicegroup API rather than directly
fetching the information either through sqlalchemy layer and then db or
using service objects.


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

- Fix admin interface, nova-manage, to use servicegroup API rather than
  directly querying database.
- Fix REST API extensions for os-hosts, os-hypervisors, os-services
  and os-availability-zones to use servicegroup API. All of these use
  direct calls to objects. ServiceList or host_api.service_get_all (which
  is hard-coded to use objects.ServiceList.get_all, which queries the
  database services table and does not actually hit the servicegroup API
  at all).


Dependencies
============

None


Testing
=======

1. Unit tests will be added if needed.
2. Existing unit tests will be updated to make sure the services
   data is accessed/updated using the servicegroup API.


Documentation Impact
====================

None


References
==========

- http://lists.openstack.org/pipermail/openstack-dev/2015-May/063602.html
- https://review.openstack.org/#/c/138607
