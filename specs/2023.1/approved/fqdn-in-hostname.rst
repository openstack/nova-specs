..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Allow FQDN in hostname field
============================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/fqdn-in-hostname

Enable end users to specify an FQDN as the instance hostname


Problem description
===================
Originally when nova was created the instance hostname was set from the
instance display-name. Nova did not allow FQDNs in the display name and
explicitly blocked it, but that was later removed as a bugfix.

Given the filtering of FQDN like strings was not done as a spec or feature
nova never provided an API guarantee that FQDNs can be used when creating a
server. After several bug reports of undesirable interactions with Designate
we decided to extend the normalization that removes non-ASCII alpha-numeric
character to also remove periods ``.`` from the hostname when
initializing it form the display name.

In the Xena release we also introduced configurable instance hostnames by
exposing the hostname field directly in the API but maintained our
prohibition on FQDNs.
https://specs.openstack.org/openstack/nova-specs/specs/xena/implemented/configurable-instance-hostnames.html

This spec seeks to extend the hostname field to allow FQDNs to be used as the
hostname of an instance.


Use Cases
---------

As an operator, I want to allocate domains to my tenants and use automation to
validate that the VMs are created with an FQDN that is derived from that
domain.

As a VNF vendor, I want to set the value of /etc/hostname to an FQDN
automatically when creating an instance via the api leveraging cloud-init
or another tool without using user-data.

Proposed change
===============
- add a new api microversion to opt into using an FQDN in the hostname field.
- increase the character length limit on the host name filed form 63 to 255
- remove the rejection of "." and other legal characters in a FQDN.
- currently, attempting to use multi-create with the ``--hostname`` parameter
  results in an error 400. This spec continues this behavior: multi-create with
  ``--hostname``, be it FQDN or short name, continues to be disallowed.

..NOTE::

  Today the instance.hostname field is propagated into the hostname field of
  the instance metadata. With this change the instance.hostname field can be an
  FQDN and that will also be propagated as done today without alteration.



Alternatives
------------

Nova could add a FQDN field
e.g. openstack server create --FQDN ...

This raises ambiguity of when to use --hostname vs --FQDN and requires a
change to the data model to store the new field.

Nova could add a domain field
e.g. openstack server create --hostname my-host --domain my.domain.com ...

This is better then --FQDN but still requires a db and object changes for
little benefit.

Nova could try to propagate hostname changes to neutron ports and floating IPs.
This is seen as risky, complex and hard to understand.

First if nova was to propagate hostname changes to the port dns_name field it
would only be able to do so on ports that were created by nova, not pre created
ports passed in by the API user. If we updated ports that were passed in
it could break existing use-cases where an end user set the desired name.

Second the floating IP ``dns_name`` is not typically the same as the instance
FQDN. The instance hostname or FQDN is typically an internal name used in the
application and the floating ip is used to expose a public name for the
service. i.e. the instance might be called ``webserver.cloud.com`` where
as the ``dns_name`` of the floating IP might be ``blog.mysite.example.com``.

Given the two reasons above, and the fact nova does not want to manage
networking, propagation of hostname changes to neutron ports is out of scope.

Since this is only useful when using designate and designate already
monitors nova's notification endpoint to update dns records using the
designate-sink component, this functionality can be implemented using designate
if designate desire in the future.

For these reasons updating the hostname in other services, when its updated in
nova, is out of scope.

..NOTE::

  As is done today, if the instance.hostname is updated on an instance it will
  be updated in the metadata service but not in the config-drive. If the
  config-drive is ever regenerated such as via a cross cell
  resize then the new value will be available to the guest via the
  config drive. This does not change the behavior from before this change.


Data model impact
-----------------

None

The database field is already large enough to hold any valid FQDN so no changes
are required to the db. The instance object declares the hostname field as a
string and also requires no changes.

REST API impact
---------------

A new API microversion will be introduced to allow FQDNs in the hostname field.
Minor changes will be required to conditionally change the length restriction
and disable some of the current validation when the new microversion is used
but the code will remain for older microversions.


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Users will be able to set the hostname of their vm to an FQDN, however without
using an external service like designate to advertise the FQDN it may not be
resolvable without manual intervention.

Nova provides no guarantee of uniqueness or reachability of the FQDN provided
by the end user.

As is the case today, nova will only set the ``dns_name`` on a neutron port
once when the server is first created. If the end user updates the
instance.hostname, it will be updated in the nova db and become visible in
the metadata API hostname field. It is out of scope of the nova project to
propagate this hostname change to any neutron ports, floating IPs or
dns records.


Performance Impact
------------------

None

Other deployer impact
---------------------

Deployers should be aware that unique FQDNs or hostnames cannot be enforced
using the existing ``[DEFAULT]/osAPI_compute_unique_server_name_scope``
config option as that provides uniqueness of the display name,
not the hostname.

This spec does not introduce a way to force the hostnames or FQDNs
to be unique in any scope.


Developer impact
----------------

osc should be extended to support the new microversion.

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  notartom

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  sean-k-mooney

Work Items
----------

* remove API restriction
* update API sample tests
* provide new microversion and API ref
* update osc

Dependencies
============

None


Testing
=======

This can be entirely tested with API/functional tests.


Documentation Impact
====================

The API ref will be updated

References
==========

None


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 Antelope
     - Introduced
