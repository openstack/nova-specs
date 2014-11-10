..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Remove glanceclient wrapper
===========================

https://blueprints.launchpad.net/nova/+spec/use-glance-v2-api

This spec proposes removing the wrapper code around glanceclient and
allow nova to use glanceclient directly.

Problem description
===================

Nova currently uses a wrapper on top of glanceclient, which is a
close-enough implementation of the same API exposed by the client
itself. This wrapper has evolved over the years allowing nova to move
from older versions of glance's API to newer ones. Unfortunately, this
code is quite old and contains some workarounds to allow nova for
using some of the latest features exposed through Glance's API.

As of Kilo, Glance's team plans to deprecate the version 1 of the API
but to do that, it is necessary to ensure that all projects depending
on it are able to function correctly with the latest version and that
the transition from the previous version to the new one is as painless
as possible.

Use Cases
----------

The idea behind this cleanup is to reduce the code that needs to be
maintained by the nova team and allow Glance to evolve without being
blocked by other projects. The changes proposed in this spec shouldn't
have any impact on developers, end users or operators.

Project Priority
-----------------

Not applicable

Proposed change
===============

The proposed change is to remove entirely the `nova.image.glance`
module and keep the existing `nova.image.api` module until we're able
to get rid of `nova.image.download` too.

The `nova.image.glance` modules contains the code for the
above mentioned wrapper that we'd like to cleanup. This code contains
some logic duplications from glanceclient and most of it is not
needed. The bits that are needed - those that at least could be
reused - are the ones enhancing image downloads. That is, the piece of
code that allows to access the image data directly depending on the
store and whether it's been enabled in the configuration file. In
order to keep supporting this behavior, we must keep the code under
`nova.image.download` until `glance_store` is adopted by nova - a
separate blueprint will be written for this.

Once `glance_store` is refactored and adopted, there won't be any need
to maintain the code under `nova.image.api` either. This will be
addressed in the `glance_store` spec as well.

During these changes, the existing glance specific config options will
be updated too. There are some old and not useful options - host, port,
protocol - that could be deprecated in favor of better ones -
api_servers.

In addition to the above changes, the default version of the glance
api will be bumped to v2. This change will require updating nova tests
to test this version of the API as well.

Alternatives
------------

Keep the wrapper and clean it up until it matches exactly glance's
client API. Please, don't! :)

Another way to make this transition to use v2 more lightweight is by
removing the wrapper code but keep using the v1 of the API. This will
allow users to opt-in to glance v2 by just changing the glance api url
in Nova's conf. Although conservatives may like this option better,
I'd recommend to move straight to v2. The main reason being that
Glance's v1 has some issues, including security ones - see unchecked
image membership - that are not going to be fixed since
anymore. Furthermore, v2 of the API allows for smarter implementations
for image data access and it's the current maintained and fully
supported version.

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

The change will keep backwards compatibility with the existing
configuration options and work on a upgrade path for deployers.

This change will introduce Glance's API v2 as the default version to
use. Deployers of this service will need to downgrade the version if
they don't want to use it. For what is worth, Glance enables the API
v2 by default.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  flaper87

Other contributors:
  jokke
  kragniz

Work Items
----------

- Rewrite `nova.image.api.Api` methods using glanceclient directly
- Move current glance specific options and remove `nova.image.glance`
  code
- Deprecate old `nova.image.glance` options like: host, port, protocol

Dependencies
============

None

Testing
=======

All existing test will continue to function as they do but they'll
test Glance's v2. It'll be necessary to add a test for Glance's v1 as
well until it's fully deprecated.

For functional and integration tests to work properly, it'll be
necessary to register Glance's API v2 in keystone as the default
one. Devstack currently registers just the v1. This will allow us to
test everything in the gate as well.

Documentation Impact
====================

Commits with the configuration changes will be marked with DocImpact

References
==========

- https://etherpad.openstack.org/p/kilo-nova-glance
