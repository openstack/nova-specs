..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Update Microversion Header
==========================

https://blueprints.launchpad.net/nova/+spec/modern-microversions

Nova pioneered the microversion concept. The success of the concept
has led other projects to follow suit, exposing limitations in the
original implementation. One of those limitations is that the
specificity of the microversion header name leads to some
inflexibility on at least two dimensions:

* The use of project name instead of service type is not aligned
  with cross-project goals of using service type wherever possible.

* The placement of the name or type in the header name misrepresents
  that the type is actually a value of the header.

These issues have been addressed in a new `microversion specification`_
from the API working group and a related guideline on avoiding
`header proliferation`_.

.. _microversion specification: http://specs.openstack.org/openstack/api-wg/guidelines/microversion_specification.html
.. _header proliferation: http://specs.openstack.org/openstack/api-wg/guidelines/headers.html#avoid-proliferating-headers


Problem description
===================

With the advent of the new microversion header specification, nova
is not compliant.

Use Cases
---------

As a user of OpenStack APIs I expect them to be consistent, coherent
and sensible.

Proposed change
===============

Nova's microversion handling will be updated to accept the new style
request headers and send the required response headers. Specifically
this means that in a request the following will be accepted to
indicate a microversion negotation::

    OpenStack-API-Version: compute <the version requested>

In a response the following will be sent::

    OpenStack-API-Version: compute <the version used>
    Vary: OpenStack-API-Version

These headers will be in addition to the existing
``X-OpenStack-Nova-API-Version`` headers, to preserve compatibility
in both directions. If both headers are present in a request, the
newer `OpenStack-API-Version` style header must be preferred.

Adding these headers will, with some irony, require a microversion
bump.

A `microversion-parse`_ library already exists to facilitate this
change.

.. _microversion-parse: https://pypi.org/project/microversion_parse

Alternatives
------------

This specification makes no effort to deprecate and eventually
remove the older microversion headers under the assumption that doing so
is more trouble than it is worth. In other contexts there has been some
concern that this wastes header bytes. If this is a concern shared by
many we may be able to figure out a way to address it. If there is a
useful way to do so, that would be an alternative.

Data model impact
-----------------

None.

REST API impact
---------------

No API methods are added, but every request will now have additional
headers in each request and response. Luckily the change to do this is
centralized.

The mechanics of incorrect values in the new header are the same as
with the old (e.g. responding with a ``406``).

Security impact
---------------

None.


Notifications impact
--------------------

None.

Other end user impact
---------------------

python-novaclient will eventually need to be updated to deal with
this header. If the minimum API version is ever raised above the
threshold set at the change to a new microversion header then
support for the old microversion header could be removed from
novaclient.

Performance Impact
------------------

None, unless you think a few more bytes in the headers is a
significant problem relative to the other real issues in
performance.

Other deployer impact
---------------------

If there are header filtering proxies somewhere in a deployer's
stack, they will need to update to allow the new header to pass.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cdent

Other contributors:
  sdague

Work Items
----------

* Update nova's WSGI framework to use microversion-parse.
* Update the WGSI framework to send and receive both headers.
* Update unit and functional tests.
* Bump microversion.


Dependencies
============

None, other than the aforementioned microversion-parse, which is
already accepted into global requirements.


Testing
=======

In testing it is important to make sure that we cover situations
using the old header, the new header, both headers and neither of
the headers.


Documentation Impact
====================

The api-ref will need to be updated at some point to reflect the
availability of the new header. This does not need to be immediate
as the old headers will continue to work indefinitely.

References
==========

* Proof of concept at: https://review.openstack.org/#/c/300077/


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
