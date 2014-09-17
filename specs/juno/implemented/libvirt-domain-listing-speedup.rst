..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Speedup listing of domains in libvirt driver
============================================

https://blueprints.launchpad.net/nova/+spec/libvirt-domain-listing-speedup

The libvirt driver currently uses the legacy libvirt APIs for getting
lists of domains. These are inefficient and prone to race conditions,
so have been replaced by much better designed APIs.

Problem description
===================

The libvirt driver in Nova currently uses a combination of calls to
numOfDomains, listDomainsID, numOfDefinedDomains, listDefinedDomains,
lookupByID and lookupByName to list domains on a host. This is very
inefficient as it requires O(N) libvirt API calls to list 'N' guests.
It also has designed in race condition where Nova can loose a guest
if it transitions from shutoff to running while the list of domains
is being fetched.

The 0.9.13 version of libvirt introduced a new method listAllDomains
which can be used to replace all those calls with a single API call,
thus providing a way to get a list of domains which has constant
execution time regardless of how many domains there are.

Proposed change
===============

A new method 'list_instance_domains' will be introduced that will
attempt to use the listAllDomains method to fetch the list of domains,
and fallback to using the old method if it is not supported by the
libvirt version or the hypervisor driver in use.

Rather than just returning a list of domain IDs, names or UUIDs,
it will return a list of libvirt.virDomain object instances avoiding
the need todo separate lookups.

By default it will only return running instances which were originally
launched by Nova. It can be optionally told to include inactive
instances, instances launched by other systems (eg libguestfs) or
the Xen Domain-0 instance.

Everywhere in the libvirt driver which calls list_instances or
list_instance_ids will then be changed to use this new method, thus
significantly improving their scalability.

Alternatives
------------

Continue to use current APIs, but this is inefficient and prone to
race conditions, so not at all desirable

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

It will improve the performance of the libvirt driver when used against
libvirt >= 0.9.13, particularly when there are lots of instances of the
host.

Other deployer impact
---------------------

Deployers are strongly recommended to use libvirt >= 0.9.13 to take
advantage of the performance improvements.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  berrange

Work Items
----------

 - Implement new list_instance_domains method
 - Write test cases for list_instance_domains
 - Convert libvirt driver to use list_instance_domains

Dependencies
============

* Current min libvirt is 0.9.6, but this requires 0.9.13. Fallback
  code will be provided for use with 0.9.6 versions.

Testing
=======

The current tempest gate tests should fully exercise the new code
paths.

Documentation Impact
====================

Recommend deployment of libvirt >= 0.9.13 for best scalability.

References
==========

None
