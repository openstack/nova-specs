..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Libvirt driver domain metadata
==============================

https://blueprints.launchpad.net/nova/+spec/libvirt-driver-domain-metadata

Metadata will be recorded in the libvirt domain XML configuration to provide
information about the Nova instance that the domain corresponds to. The aim
is to provide information that can be useful to administrators troubleshooting
compute hosts.

Problem description
===================

When troubleshooting a compute node there will be a number of running libvirt
domains which correspond to Nova instances. There may also be other running
domains which were not launched by Nova, for example, utility guests run by
libguestfs for file injection. The libvirt domain uuid will match that of the
Nova instance, but there is more information about a Nova instance that could
usefully be provided to administrators. For example, the identity of the
tenant who launched it, the original flavour name and/or settings, the time at
which the domain was launched, and the version number of the Nova instance that
launched it (can be relevant if Nova is upgraded while a VM is running).

Proposed change
===============

The Libvirt domain XML configuration schema allows for applications to insert
arbitrary metadata under a private XML namespace. The proposal is to make use
of this to define some metadata that is relevant to Nova, specifically it will
record

 - The nova package version
 - The display name of the instance (as matching 'nova list')
 - The name of the flavor
 - The creation time of the instance
 - The user and project ID/name of owner
 - The root disk glance image or cinder volume UUID

This would correspond to the following XML blob

::

  <domain type='kvm'>
    ...rest of domain XML config...
    <metadata>
      <nova:instance xmlns:nova="http://openstack.org/nova/instance/1">
        <nova:package version="2014.2.3"/>
        <nova:flavor name="m1.small">
          <nova:memory>512</nova:memory>
          <nova:disk>10</nova:disk>
          ....
        </nova:flavor>
        <nova:name>demo1vm</nova:name>
        <nova:creationTime>2014-12-25 12:03:20</nova:creationTime>
        <nova:owner>
          <nova:user uuid="85bd45c0...213684">joe</nova:user>
          <nova:project uuid="d33b8c0e...342d69">acmecorp</nova:project>
        </nova:owner>
        <nova:root type="image|volume" uuid="69f2991b...f29a8bc"/>
      </nova:instance>
    </metadata>
  </domain>

Alternatives
------------

Administrators can ask libvirt for the UUID of the running instance and then
attempt to trace all the information back via Nova APIs. If Nova itself is in
some failure scenario though, this would not be possible. It also places more
burden on the administrator to trace the info which could be provided directly
in the Libvirt XML.

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

The compute host administrator will be able to ask libvirt to provide the XML
config for the running instance and from there find out various useful pieces
of metadata about the instance.

Developer impact
----------------

None, this is entirely within the libvirt driver impl

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  berrange

Work Items
----------

* Extend the nova/virt/libvirt/config.py object model to represent the
  proposed metadata schema for Nova
* Extend the nova/virt/libvirt/driver.py get_guest_config() method to fill
  in the metadata when generating guest XML config

Dependencies
============

None

Testing
=======

None required beyond unit tests

Documentation Impact
====================

Document that the libvirt XML config contains this metadata as an aid
for administrators debugging compute nodes.

References
==========

* Libvirt XML format docs http://libvirt.org/formatdomain.html#elementsMetadata
