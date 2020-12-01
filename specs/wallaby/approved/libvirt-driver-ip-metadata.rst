..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add IP address to libvirt guest metadata
==========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-driver-ip-metadata

Past Blueprint [1]_ has provided useful instance information to system
administrators through the libvirt domain XML configuration. This time,
I propose to extend this metadata to include IP addresses of instances.

Problem description
===================

In a virtualized environment using libvirt, qemu and kvm, the instance
configuration information is stored in XML and used by libvirt to launch
and manage instances.

This XML contains useful configuration information such as instance names,
flavors and images as metadata [2]_. Here, I noticed that IP addresses are
not included.

Use Cases
---------

With this proposal, we can get IP addresses of instances on the nova-compute
node without going through nova or neutron's REST API. As an example, operators
can collect and monitor statistics based on an instance's IP address at the low
cost of simply loading XML. In addition, from the vendor's point of view,
the IP addresses of the instances can be easily obtained. This will reduce
unnecessary communication between users and vendors.

Proposed change
===============

So I propose to add IP addresses to the metadata in this Blueprint.
Here is an example of the metadata description with the IP address.
If an instance has more than one IP address, enumerate those IP addresses.

The port attach or detach is performed dynamically after the creation of the
instance. Every time there is a change, it is reflected in the contents of
the XML.

::

  <domain type='kvm' id='5'>
    ...
    <metadata>
      <nova:instance xmlns:nova="http://openstack.org/xmlns/libvirt/nova/1.0">
        <nova:package version="18.1.1"/>
        <nova:name>sample-instance-name</nova:name>
        <nova:creationTime>2020-10-23 05:36:41</nova:creationTime>
        <nova:flavor name="sample-flavor">
          <nova:memory>348160</nova:memory>
          <nova:disk>100</nova:disk>
          <nova:swap>0</nova:swap>
          <nova:ephemeral>0</nova:ephemeral>
          <nova:vcpus>80</nova:vcpus>
        </nova:flavor>
        <nova:owner>
          <nova:user uuid="2997526f-669c-4bd9-af5f-68c6ba0cc2f0">sample-user</nova:user>
          <nova:project uuid="acf923f2-9b4d-4e0d-acfb-1b2976dd480f">sample-project</nova:project>
        </nova:owner>
        <nova:root type="image" uuid="66e81ebe-9d4f-45ae-b79b-b3d9dc989b21"/>

        <!-- I suggest adding following lines -->
        <nova:ports>
          <nova:port uuid="567a4527-b0e4-4d0a-bcc2-71fda37897f7">
            <nova:ip type="fixed" address="192.168.1.1" ipVersion="4"/>
            <nova:ip type="fixed" address="fe80::f95c:b030:7094" ipVersion="6"/>
            <nova:ip type="floating" address="11.22.33.44" ipVersion="4"/>
          </nova:port>
          <nova:port uuid="a3ca97e2-0cf9-4159-9bfc-afd55bc13ead">
            <nova:ip type="fixed" address="10.0.0.1" ipVersion="4"/>
            <nova:ip type="fixed" address="fdf8:f53b:82e4::52" ipVersion="6"/>
            <nova:ip type="floating" address="1.2.3.4" ipVersion="4"/>
          </nova:port>
        </nova:ports>

      </nova:instance>
    </metadata>
    ...
  </domain>


Alternatives
------------

Of course, we can get IP addresses of instances via the REST API.
However, in the above use case, we can get that information at a lower
cost by loading XML.

Data model impact
-----------------

None.

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

None. Existing metadata is not manipulated.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

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
  nmiki

Other contributors:
  None

Feature Liaison
---------------

Liaison Needed.

Work Items
----------

* Add a new object that corresponds to the IP address in
  nova/virt/libvirt/config.py. For example, it would be named something
  like LibvirtConfigGuestMetaNovaIp.

* Add network_info as an argument to _get_guest_config_meta to retrieve
  information about networks, including IP addresses.

* Add set_metadata method to Guest class in nova/virt/libvirt/guest.py.
  By calling libvirt's virDomainSetMetadata API [3]_ , it updates the metadata
  in the XML in real time when the port attaches and detaches.

* In nova/virt/libvirt/driver.py, call guest.set_metadata in the
  attach_interface and detach_interface methods.

* Implement unit tests in nova/tests/unit/virt/libvirt/test_config.py.


Dependencies
============

None.

Testing
=======

There is no integration with other systems, so only unit tests can ensure
correctness. It covers the case of having no IP address, only one, or
multiple IP addresses. This feature is mainly intended for debugging purposes
for developers and administrators. It is not an official external interface.

Documentation Impact
====================

Documentation for administrators describing that IP addresses are added
as metadata in libvirt xml.

References
==========

.. [1] https://blueprints.launchpad.net/nova/+spec/libvirt-driver-domain-metadata
.. [2] https://libvirt.org/formatdomain.html#elementsMetadata
.. [3] https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainSetMetadata

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
