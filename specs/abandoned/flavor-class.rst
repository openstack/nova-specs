..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============
Flavor classes
==============

.. note:: This spec was abandoned by efried on account of having been
          sitting in the backlog directory since 2015.

As an operator I would like to be able to define policy and quotas differently
for different sets of hardware.

As an example of why this might be desirable consider that some hardware could
be running libvirt and some could be part of an ironic cluster.  Since the
baremetal hardware managed by ironic won't support operations like rescue or
attaching volumes it is desirable to disallow those actions via policy for
instances built on that hardware while allowing it for instances on libvirt.
It may also be desirable to only allow building x instances on baremetal
hardware and y instances on the virtualized hardware.

This can be accomplished by scoping policy and quotas based on the "class" of a
flavor.  Each flavor would be assigned a class and multiple flavors could share
the same class.  Continuing with the example above this would allow for
baremetal flavors to be grouped and virtual flavors to be grouped.  Additional
work later could allow for policy rules to be scoped by flavor class and quotas
to be scoped as well.  This could be the basis that work like
https://review.openstack.org/#/c/206160/ (a spec to do a per flavor or AZ
quota) builds upon.

Some mechanism for scheduling the flavors properly is also needed and it could
be accomplished by configuring the advertised capabilities of a compute.
However there is probably a better way to handle that but could be discussed in
a future spec.

So the basic proposal here is to add a field to flavors in the db/object/API
that scoped policy and quotas can be built upon and the scheduler can make use
of.  I have called it "class" but it could be called group or aggregate or some
other overloaded term, but there is almost certainly a better name for this.


This concept is being used at Rackspace quite successfully at the moment for
policies and quotas but we have built it on top of flavor extra specs.  The
scheduling is handled at the cell level as different cells contain different
hardware types.  We would like to push this code upstream but we first need
acceptance of the initial idea of a flavor class and an implementation that we
can adapt our code to.


Problem description
===================

None

Use Cases
----------

None

Proposed change
===============

Lets take an example for Flavor class for Virtual instances. Different
Flavor classes can be created depending on the need. For example something
like Baremetal Flavor class can be created for Baremetal instances.

vm_flavor_class {cpu: 100 cores, ram: 20 GB, disk: 1  TB}

vm.small {cpu : 2 cores, ram : 5 GB, disk: 100 GB, class: 'vm_flavor_class'}

vm.large {cpu : 2 cores, ram : 8 GB, disk: 500 GB, class: 'vm_flavor_class'}

Which means a maximum of 2 VM's with vm.large and 1 VM with vm.small
will be created. These has been work related to Quota policy engine
proposed which makes sure that these validation for quota allocation,
reservations are done and governed by a quota engine framework but discussion
about it is out of the scope of this spec.

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

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  None

Other contributors:
  alaski, vilobhmm

Work Items
----------

1. An extension for manage flavor classes needs to be introduced.
2. Methods to create/update/delete/get flavor class details needs to
   be introduced.

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

None


History
=======

Optional section for liberty intended to be used each time the spec
is updated to describe new design, API or any database schema
updated. Useful to let reader understand what's happened along the
time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
   * - Train
     - Abandoned
