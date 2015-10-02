..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Check flavor type before add tenant access
==========================================

https://blueprints.launchpad.net/nova/+spec/check-flavor-type-before-add-tenant


Problem description
===================

We can't add tenant access to a public flavor.
Trying to do such a thing results in a confusing error message
when later we show the flavor::

 $ nova flavor-access-add 1 2
 +-----------+-----------+
 | Flavor_ID | Tenant_ID |
 +-----------+-----------+
 | 1         |         2 |
 +-----------+-----------+

 $ nova flavor-access-list --flavor 1
 ERROR (CommandError): Failed to get access list for public flavor type.

We should check whether the flavor is public or not
and reject add access to public flavor API call.
But this is backward incompatible bug, every API change need spec,
so a microversion is needed to handle this problem.

Use Cases
----------

User will be nofified they can't add an access to flavor if it's
public flavor with some exceptions.

Project Priority
-----------------

None

Proposed change
===============

In API layer, for "addTenantAccess" for flavor, we did following
to add access to flavor, so the proposed change is before
the access is added, add a validation to check the type and raise
exception in case the flavor is private type.

api/openstack/compute/plugins/v3/flavor_access.py

.. code:: python

  flavor = objects.Flavor(context=context, flavorid=id)
  try:
      flavor.add_access(tenant)

This is not a backward compatible fix, so a new microversion will
be added and the check will be done only when the incoming API version
is equal or higher to this one.

Alternatives
------------

Let user continue to use existing code, though it's a bug.

Data model impact
-----------------

None

REST API impact
---------------

Per 'Proposed change' discussed, a check will added before
add_access is called.
It will be something like:

.. code:: python

  def _check_flavor_type(self, req, flavor):
      if req.version > target_version:
           if flavor.type is public:
               raise HTTPBadRequest

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

None

Implementation
==============

Assignee(s)
-----------

jichenjc <jichenjc@cn.ibm.com>

Work Items
----------

Add API change through microversion because it's backward incompatible.
1) Add microversion to os-flavor-access/addTenantAccess
2) Add validation before add access.

Dependencies
============

None

Testing
=======

None

Documentation Impact
====================

None

References
==========
[1] https://bugs.launchpad.net/nova/+bug/1361476
[2] https://review.openstack.org/#/c/124338/
