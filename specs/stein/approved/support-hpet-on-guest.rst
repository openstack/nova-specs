..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Support High Precision Event Timer (HPET) on x86 guests
=======================================================

https://blueprints.launchpad.net/nova/+spec/support-hpet-on-guest

Problem description
===================

Use Cases
---------

As an end user looking to migrate an existing appliance to run in a cloud
environment I would like to be able to request a guest with HPET so that I can
share common code between my virtualized and physical products.

As an operator I would like to support onboarding legacy VNFs for my telco
customers where a guest image cannot be modified to work without a HPET.

Proposed change
===============

End users can indicate their desire to have HPET in the guest by specifying a
image property ``hw_time_hpet=True``.

Setting the new image property to "True" would only be guaranteed to be valid
in combination with ``hypervisor_type=qemu`` and either ``architecture=i686``
or ``architecture=x86_64``.

.. note:: A corresponding flavor extra spec will not be introduced since
   enabling HPET is really a per-image concern rather than a resource concern
   for capacity planning.

A few options to use Traits were considered as described in the next section,
but we end up choosing the simpler approach due to the following reasons:

1) HPET is provided by qemu via emulation, so there are no security
   implications as there are already better clock sources available.

2) The HPET was turned off by default purely because of issues with time
   drifting on Windows guests. (See nova commit ba3fd16605.)

3) The emulated HPET device is unconditionally available on all versions of
   libvirt/qemu supported by OpenStack.

4) The HPET device is only supported for x86 architectures, so in a cloud with
   a mix of architectures the image would have to be specific to ensure the
   instance is scheduled on an x86 host.

5) Initially we would only support enabling HPET on qemu.  Specifying the
   hypervisor type will ensure the instance is scheduled on a host using the
   qemu hypervisor.  It would be possible to extend this to other hypervisors
   as well if applicable (vmware supports the ability to enable/disable HPET,
   I think), and which ones are supported could be documented in the "useful
   image properties" documentation.


Alternatives
------------

The following options to use Trait were considered, but ultimatedly we chose
a simpler approach without using Trait.

Explicit Trait, Implicit Config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Operators can indicate their desire to have HPET in the guest by specifying a
placement trait ``trait:COMPUTE_TIME_HPET=required`` in the flavor extra-specs.

End users can indicate their desire to have HPET in the guest by uploading
their own images with the same trait.

Existing nova scheduler code picks up the trait and passes it to
``GET /allocation_candidates``.

Once scheduled to a compute node, the virt driver looks for
``trait:COMPUTE_TIME_HPET=required`` in the flavor/image or
``trait*:COMPUTE_TIME_HPET=required`` for numbered request group in flavor and
uses that as its cue to enable HPET on the guest.

If we do get down to the virt driver and the trait is set, and the driver for
whatever reason (e.g. value(s) wrong in the flavor; wind up on a host that
doesn't support HPET etc.) determines it's not capable of flipping the switch,
it should fail. [1]_

**CON:** We're using a trait to effect guest configuration.

Explicit Config, Implicit Trait
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Operator specifies extra spec ``hw:hpet=True`` in the flavor.
* Nova recognizes this as a known special case and adds
  ``required=COMPUTE_TIME_HPET`` to the ``GET /allocation_candidates`` query.
* The driver uses the ``hw:hpet=True`` extra spec as its cue to enable HPET on
  the guest.

**CON:** The implicit transformation of a special extra spec into
placement-isms is arcane. This wouldn't be the only instance of this; we would
need to organize the "special" extra specs in the code for maintainability, and
document them thoroughly.

Explicit Config, Explicit Trait
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Operator specifies **both** extra specs, ``hw:hpet=True`` and
  ``trait:COMPUTE_TIME_HPET=required``, in the flavor.
* Existing nova scheduler code picks up the latter and passes it to ``GET
  /allocation_candidates``.
* The driver uses the ``hw:hpet=True`` extra spec as its cue to enable HPET on
  the guest.

**CON:** The operator has to remember to set both extra specs, which is kind of
gross UX. (If she forgets ``hw:hpet=True``, she ends up with HPET off; if she
forgets ``trait:COMPUTE_TIME_HPET=required``, she can end up with late-failing
NoValidHosts.)

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

Negligible.


Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

The new image property will only work reliably after all nodes have been
upgraded.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jackding

Other contributors:
  jaypipes, efried

Work Items
----------

* libvirt driver changes to support HPET

Dependencies
============

None

Testing
=======

Will add unit tests.


Documentation Impact
====================

Update User Documentation for image properties [2]_.

References
==========

.. [1] http://lists.openstack.org/pipermail/openstack-dev/2018-October/135446.html
.. [2] https://docs.openstack.org/glance/latest/admin/useful-image-properties.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
