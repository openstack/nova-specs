..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
Deprecate API Proxies
=====================

https://blueprints.launchpad.net/nova/+spec/deprecate-api-proxies

Deprecate the API Proxies that exist in Nova for services that are no
longer a part of Nova. Also Deprecate Nova Network API so that all
Network APIs are deprecated at the same time regardless of network
backend.

Problem description
===================

Many services originally existed in Nova (images, volumes, baremetal,
networking) and were later spun out. At the time the ramifications for
the Nova API remaining stable through this process weren't really
considered.

Over time all of these services have evolved, and in many cases the
API that is current in these services doesn't match the semantics of
the original Nova API. Maintaining a proxy layer for these services
gets increasingly difficult over time, and the validity of the data
returned becomes more suspect.

As the Nova team we'd like to point API consumers to the native API
whenever possible, and get out of the habit of being a pure proxy for
other REST APIs.

Use Cases
---------

End users should hit the native API for images, volumes, baremetal,
and networking (when using Nova Network).

Proposed change
===============

The API Ref site will be updated to state that all the following
resources are deprecated:

* /images
* /os-baremetal-nodes
* /os-volumes
* /os-snapshots
* /os-fixed-ips
* /os-floating-ips
* /os-floating-ip-dns
* /os-floating-ip-pools
* /os-floating-ips-bulk
* /os-fping - (this only really works with nova-net)
* /os-networks
* /os-security-group-default-rules
* /os-security-group-rules
* /os-security-groups
* /os-tenant-networks

The documentation for all of these will be moved to the end of the API
Ref site, and it will be visually clear this is part of the deprecated
portion of the API.

There will also be links to the correct corresponding parts of the
documentation for the relevant APIs.

Image Links
-----------

The /images resource included HATEOS links for images, which has had
an ``alternate`` field that points back to the glance server directly.

.. code::

    "images": [
        {
            "id": "70a599e0-31e7-49b7-b260-868f441e862b",
            "links": [
                {
                    "href": "http://openstack.example.com/v2/6f70656e737461636b20342065766572/images/70a599e0-31e7-49b7-b260-868f441e862b",
                    "rel": "self"
                },
                {
                    "href": "http://openstack.example.com/6f70656e737461636b20342065766572/images/70a599e0-31e7-49b7-b260-868f441e862b",
                    "rel": "bookmark"
                },
                {
                    "href": "http://glance.openstack.example.com/images/70a599e0-31e7-49b7-b260-868f441e862b",
                    "rel": "alternate",
                    "type": "application/vnd.openstack.image"
                }
            ],
            "name": "fakeimage7"
    },

After we drop /images there will be no need for images references. The
``imageRef`` field in ``servers`` is a UUID, which is valid against
glance directly.

At the same time we will enforce that all our handling of ``imageRef``
is a UUID. Today it accept a vast range of values and does some really
`sloppy heuristics
<https://github.com/openstack/nova/blob/cdfbb9a668fdcf289ffdfa5252d102e9d3e2ec35/nova/image/glance.py#L669-L671>`_
to hope it is a valid image ref.

Networking API
--------------

Nova Network is deprecated, as such the APIs around that networking
will also be marked as deprecated, as is their use in talking to the
proxy. A preamble will be written for this section to clarify the
deprecation of the network API as well as the proxy to Neutron
functionality.

Users who wish to continue to use the Network API in Nova must just
freeze their code to work at microversions before this change.

Limits and Quotas
-----------------

Some of the limits and quotas presented to the user are for network
resources. These never worked correctly when using Neutron.

The keys related to network resources (security groups, fixed ips,
floating ips) will also be removed from limits in this microversion.

Maintenance Status
------------------

The following rules will exist for all of these APIs.

* No new features will be added to them
* The code behind these APIs will be in soft freeze, bug fixing kept
  to a minimum.
* Bugs that do not cause a 500 error are likely to be unfixed.

Internal Representations Remain
-------------------------------

The Nova server includes items such as:

.. code:: javascript

   "accessIPv4": "1.2.3.4",
   "accessIPv6": "80fe::",
   "addresses": {
          "private": [
                {
                    "addr": "192.168.0.3",
                    "OS-EXT-IPS-MAC:mac_addr": "aa:bb:cc:dd:ee:ff",
                    "OS-EXT-IPS:type": "fixed",
                    "version": 4
                }
            ]
        },

This is network information, however it's really a part of our server
model. In these cases we will continue to keep this representation in
our server object, even though it comes from another service.

This can best be thought of as full paths in the REST API are being
deprecated, resource definitions aren't changing (with the possible
exception of link content changing).

Alternatives
------------

Keep these proxies forever. This will increase the cost of the
maintenance of Nova and slow down our ability to adapt to new features
and requirements.

Data model impact
-----------------

No immediate data model changes, however once the above APIs are
actually removed from tree there is database cleanup that can be done.

REST API impact
---------------

This change will be done in concert with an API microversion, after
which all the following resources will return a ``404``.

This is a ``404`` because we are removing the whole resource in all of
these cases. Other suggestions of ``400`` are not appropriate, because
that's almost never appropriate for GET (because how did you malform
that request), and ``405`` is not appropriate because the resource
doesn't exist at all (``405`` is for a /resource that some verbs work
on, but others do not).

* /images
* /os-baremetal-nodes
* /os-volumes
* /os-snapshots
* /os-fixed-ips
* /os-floating-ips
* /os-floating-ip-dns
* /os-floating-ip-pools
* /os-floating-ips-bulk
* /os-fping - (this only really works with nova-net)
* /os-networks
* /os-security-group-default-rules
* /os-security-group-rules
* /os-security-groups
* /os-tenant-networks

To users of ``nova-net`` based clouds, we'll recommend just using a
max microversion of N-1 (where N is the change this lands in). This
effectively means that nova-net users and clouds don't get new API
features, which is appropriate for clouds using a deprecated backend.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The nova cli will make sure to deprecate all these features as well,
and we'll plan to remove those in O.

Performance Impact
------------------

This should reduce some load on Nova once these APIs are gone, as
users will go and directly hit the APIs they need to access.

Other deployer impact
---------------------

The value of ``glance.api_servers`` becomes more relevant than it was
before.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sdague

Work Items
----------

* Updated API Ref site with items as deprecated
* Introduce microversion to trigger 404 on these resources
  * Remove limits keys in this microversion
  * Tighten up imageRef validation in this microversion
* Create Tempest tests for items such as setting addresses on ports in
  neutron, then verifying they look correct in the server object via nova

Dependencies
============

None

Testing
=======

There will be in tree functional testing that these APIs do the right
thing after this microversion and return 404s.

There exist many tempest tests which provide round trip on the APIs in
question, but very few that actually attempt to set the resource data
with the native API, then get it via the Nova API (such as IPs /
Security groups that are embedded in the server representation).

This should be tested more fully, and the deprecation of the proxies
will be a good opportunity for that.

Documentation Impact
====================

API Reference will be updated as described above.

References
==========

Newton Summit Session on API deprecations - https://etherpad.openstack.org/p/newton-nova-api

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Newton
     - Introduced
