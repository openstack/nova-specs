..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Neutron DNS Using Nova Hostname
===============================

https://blueprints.launchpad.net/nova/+spec/neutron-hostname-dns

Users of an OpenStack cloud would like to look up their instances by name in an
intuitive way using the Domain Name System (DNS).

Problem description
===================

Users boot an instance using Nova and they give that instance an "Instance
Name" as it is called in the Horizon interface.  That name is used as the
foundation for the hostname from the perspective of the operating system
running in the instance. It is reasonable to expect some integration of this
name with DNS.

Neutron already enables DNS lookup for instances using an internal dnsmasq
instance.  It generates a generic hostname based on the private IP address
assigned to the system.  For example, if the instance is booted with
*10.224.36.4* then the hostname generated is *host-10-224-36-4.openstacklocal.*
The generated name from Neutron is not presented anywhere in the API and
therefore cannot be presented in any UI either.

Use Cases
----------

#. DNS has a name matching the hostname which is something that sudo looks for
   each time it is run [#]_.  Other software exists which wants to be able to
   look up the hostname in DNS.  Sudo still works but a number of people
   complain about the warning generated::

    $ sudo id
    sudo: unable to resolve host vm-1
    uid=0(root) gid=0(root) groups=0(root)
#. The End User has a way to know the DNS name of a new instance.  These names
   are often easier to use than the IP address.
#. Neutron can automatically share the DNS name with an external DNS system
   [#]_ such as Designate.  This isn't in the scope of this blueprint but is
   something that cannot be done without it.

.. [#] https://bugs.launchpad.net/nova/+bug/1175211
.. [#] https://review.openstack.org/#/c/88624/

Proposed change
===============

This blueprint will reconcile the DNS name between Nova and Neutron.  Nova will
pass the *hostname* to the Neutron API as part of any port create or update
using a new *dns_name* field in the Neutron API.  Neutron DHCP offers will use
the instance's hostname. Neutron DNS will reply to queries for the new
hostname.

To handle existing installations, Neutron will fall back completely to the
current behavior in the event that a dns_name is not supplied on the port.

Nova will pass its sanitized hostname when it boots using an existing Neutron
port by updating the port with the dns_name field.  This will be augmented in
the following ways:

#. Nova will pass the VM hostname using a new *dns_name* field in the port
   rather than the *name* field on create or update. The handling of the
   hostname will be consistent with cloud-init.

   - If Nova is creating the port, or updating a port where dns_name is not
     set, then it sets dns_name to the VM hostname.
   - If an existing port is passed to Nova with dns_name set then Nova will
     reject that as an invalid network configuration and fail the request,
     unless the hostname and the port's dns_name match. Nova will not attempt
     to adopt the name from the port.  This is confusing to the user and a
     source of errors if a port is reused between instances.

#. Nova will recognize an error from the Neutron API server and retry without
   *dns_name* if it is received.  This error will be returned if Neutron has
   not been upgraded to handle the dns_name field.  This check will be
   well-documented in the code as a short-term issue and will be deprecated in
   a following release.  Adding this check will save deployers from having to
   coordinate deployment of Nova and Neutron.
#. Neutron will insure the dns_name passed to it for DNS label validity and
   also for uniqueness within the scope of the configured domain name. If it
   fails, then both the port create and the instance boot will fail. Neutron
   will *only* begin to fail port creations *after* it has been upgraded with
   the corresponding changes *and* the user has enabled DNS resolution on the
   network by associating a domain name other than the default openstack.local.
   This will avoid breaking existing work-flows that might use unacceptable DNS
   names.

.. NOTE:: If the user updates the dns_name on the Neutron port after the VM has
   already booted then there will be an inconsistency between the hostname in
   DNS and the instance hostname.  This blueprint will not do any special
   handling of this case.  The user should not be managing the hostname through
   both Nova and Neutron.  I don't see this as a big concern for user
   experience.

Alternatives
------------

Move Validation to Nova
~~~~~~~~~~~~~~~~~~~~~~~

Duplicate name detection could be attempted in Nova. I've seen duplicate names
in the wild.  Nova likely does not have the information necessary to check for
duplicate names within the appropriate scope.  For example, I would like to
check duplicate names per domain across networks, this will be difficult for
Nova.

Move Port Creation Earlier
~~~~~~~~~~~~~~~~~~~~~~~~~~

It may be better if Nova could attempt port creation with Neutron before the
API operation completes so that the API operation will fail if the port
creation fails.  In the current design, the Nova API call will succeed and the
port creation failure will cause the instance to go to an error state.  I
believe the thing preventing this is the use case where a bare-metal instance
is being booted.  In that use case, Nova must wait until the instance has been
scheduled before it can get the mac address of the interface to give to port
creation.

This change will make for a better user experience in the long run.  However,
this work is out of the scope of this blueprint and can be done as follow up
work independently.  One possibility that should be explored is to allow
updating the Neutron port with the mac address when it is known.

Send Neutron DNS name back to Nova
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I briefly considered a design where instead of returning an error to Nova,
Neutron would accept whatever Nova passed as the hostname.  If it failed
validation then Neutron would fall back to its old behavior and generate a DNS
name based on the IP address.  This IP address would've been fed back to Nova
through the existing port status notifications that Neutron already sends back
to Nova.  It would then be written in to the Nova database so that it can be
shown to the user.

Feedback from the community told me that this would create a poor user
experience because the system would be making a decision to ignore user input
without a good mechanism for communicating that back to the user.

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

This will provide a better user experience overall.  With the hostname being
fed to Neutron, it will be available in the DNS in Neutron and optionally -- in
the future -- in DNSaaS externally, as specified in [#]_. This improves the
integration of these services from the user's point of view.

.. [#] https://review.openstack.org/#/c/88624/

Performance Impact
------------------

If the Nova upgrade is deployed before the corresponding Neutron upgrade then
there will be a period of time where Nova will make two calls to Neutron for
every port create.  The first call will fail and then Nova will make a second
call without the *dns_name* field which will be expected to pass like before.

To avoid undue performance impact in situations where the Nova upgrade is
deployed but Neutron is not upgraded for a significant period of time, a
configuration option will be implemented to enable or disable the behavior
described in the previous paragraph. The default value will be disabled.

Other deployer impact
---------------------

This change was carefully designed to allow new Nova and Neutron code to be
deployed independently.  The new feature will be available when both upgrades
are complete.

DNS names will only be passed for new instances after this feature is enabled.
Nova will begin passing dns_name to Neutron after an upgrade only for new
instances.

If Neutron is upgraded before Nova, there is no problem because the dns_name
field is not required and behavior defaults to old behavior.

If Nova is upgraded before Neutron then Nova will see errors from the
Neutron API when it tries passing the dns_name field.  Once again, Nova
should recognize this error and retry the operation without the dns_name.

The deployer should be aware of the `Performance Impact`_ discussed.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  `miguel-lavalle <https://launchpad.net/~minsel>`_

Other contributors:
  `zack-feldstein <https://launchpad.net/~zack-feldstein>`_

Work Items
----------

#. Modify existing proposal to pass hostname using *dns_name* field rather
   than *host*.
#. Handle expected errors by retrying without dns_name set.

Dependencies
============

In order for this to work end to end, the corresponding changes in Neutron
merged during the Liberty cycle.

https://blueprints.launchpad.net/neutron/+spec/internal-dns-resolution


Testing
=======

Tempest tests should be added or modified for the following use cases

- An instance created using the nova API can be looked up using the instance
  name.

Documentation Impact
====================

Mention in the documentation that instance names will be used for DNS.  Be
clear that it will be the Nova *hostname* that will be used.  Also, detail the
scenarios where instance creation will fail.

#. It will only fail when DNS has been enabled for the Neutron network by
   associating a domain other than openstack.local.
#. An invalid DNS label was given.
#. Duplicate names were found on the same domain.

References
==========

None
