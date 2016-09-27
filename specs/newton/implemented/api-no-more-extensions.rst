..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Remove support for API extensions
=================================

https://blueprints.launchpad.net/nova/+spec/api-no-more-extensions

In the before times, and the long long ago, OpenStack started as 2
services: Swift and Nova. The original architecture and plan was that
Nova was the monolithic cloud resource manager. All work in managing
resources in the cloud would be done with Nova and the Nova API. To
support experimenting with and expanding this scope the Nova API was
written with an externalized extensions facility that allowed anyone
to add new resources, or even modify existing resources (like servers
/ flavors).

But things changed. The scope of cloud resource management very
clearly could not be contained in a single project. OpenStack began
splitting up into a set of microservices that communicate with each
other over documented REST API calls. Nova and other services started
exposing administrative features over the API (not just via direct db
manipulation commands). Adding new features could now largely be done
by adding a new service instead of sideloading that code into Nova
itself. With the creation of the Big Tent, these additional services
can now very easily have a home to collaborate and thrive.

With thousands of OpenStack clouds in the wild, interoperability is a
key important value for OpenStack's long term success. It is what
enables an Application Ecosystem consuming standard OpenStack APIs to
thrive, which further expands the OpenStack ecosystem.

The Nova team has been on a multi year quest to remove the extension
facility in the API to support this goal of interoperability, and to
massively simplify the Nova code base so that it is easier to add new
features over time. This spec is intended as a historical and
architectural document to be really explicit about what this means.

Problem description
===================

The Nova API extensions framework encourages all the wrong behavior in
deploying Nova. It brings a ton of really complicated code debt, that
few people understand, and requires that Nova not use any of the
standard wsgi frameworks. It encourages people to add new resources to
Nova, out of tree, instead of collaborating around common constructs
in Nova, or a common separate service. It discourages people from
being involved in the upstream conversations around API changes,
because they have the option to just turn things off later. Even
worse, it makes it easy to change core objects like servers or
flavors, and change their behavior and representation.

In the pre-microversion days the extensions facility was used as a
really terrible versioning mechanism in tree, which led to a model of
extensions on extensions on extensions to attempt to make the API
discoverable in some way. We changed tact 4 cycles ago and built an
explicit versioning mechanism instead.

Use Cases
---------

As a consumer of multiple OpenStack clouds I would like to have
software that works the same between them and not have to anticipate
changes in the API brought by API extensions.

As a developer of OpenStack, I would like the API code to be
understandable so that it is easy to ensure future changes don't break
existing users.

As a creator of OpenStack Applications, I would like convergence in
the APIs of OpenStack to make it possible for my OpenStack Application
to be used broadly in public and private clouds.

Proposed change
===============

The Nova API extension facility is completely removed by the end of
Ocata.

In Liberty we deprecated the concept of API extensions and removed it
from the documentation -
http://docs.openstack.org/developer/nova/stable_api.html. In Liberty
we also deprecated the use of the v2 legacy code stack (which most
extensions were written against). This was an attempt to prevent the
use of extensions by new member of the OpenStack Ecosystem.

In Mitaka we deprecated the configuration options in the v2.1 API that
allowed configuration based control of which extensions are
loaded. This was an additional signal of this direction.

In Newton we have deleted the v2 legacy code stack which resulted in a
net drop of 15KLOC of quite obtuse code. We have deleted the
configuration options that allow config based modification of the
extension loading, which greatly simplified all the API documentation,
and has enabled the ability to start folding back in extensions that
require hundreds of lines of code to add a single attribute. This,
however, has still left the stevedore configuration available to side
load code (even though this is not supported).

In Newton we will eliminate the ability to stevedore load extensions
that modify existing resources (servers / flavors), and start
re-folding these extensions into the core servers / flavors code. This
will greatly simplify the API code stack and testing, and make future
additions much easier. We will remove the pre / post resource
modification facilities.

This will include effectively ignoring the content of
"nova.api.v21.extensions.server.*" extensions, and removal of the
@wsgi.extends facility used by extensions to modify the requests /
responses of other parts of the API.

In Ocata we will eliminate the use of the "nova.api.v21.extensions"
stevedore hook. This is postponed to Ocata mostly because the removal
of the extends facility is a higher priority, and based on the work
ahead of us, it's not realistic that we'd get this far in Newton.

Alternatives
------------

We could keep the status quo. However, this has been long term
direction for standardization of Nova.

Alternatives for extension owners
---------------------------------

We know that even though we've been beating the drum for a long time
about getting rid of the extensions facility, there are still folks
out there that have legacy extensions, or who haven't moved to a new
model. The following are the suggested paths forward.

Upstream your needs
^^^^^^^^^^^^^^^^^^^

Come with your needs to the upstream community. We have a pretty well
established facility for adding features to the API now, and have been
landing about 10 microversions per release since it's inception. If
your change to the resource model is really something that
fundamentally needs to be exposed on servers or flavors, that should
be an upstream conversation. That also means it will be maintained by
the larger community going forward (and will be made to work with new
infrastructure like Cells v2).

Build a new service
^^^^^^^^^^^^^^^^^^^

If you were just using the extension facility to add brand new
resources to Nova, that can just as easily be done in a new service
with a new endpoint. If these are resources that reference servers,
the validity of those servers can be checked using a Nova API call
much in the same way that Neutron / Nova / Cinder cross-communicate.

If there are additional elements of the Nova data model which need to
be exposed via the API, or via notifications, please bring these
forward to the upstream community.

But my extension is very specific to my environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Please bring forward the conversation to the wider community
anyway. There are a lot of OpenStack deploys, and issues that you
think are specific to your environment may not be. And in conversation
with the upstream operator and developer communities we could probably
come up with a generic facility that supports your use. Even if that
is simply adding additional URL sized fields that allows references to
additional services.


Data model impact
-----------------

None. This is solely about the presentation layer in the API stack.

REST API impact
---------------

The REST API itself will not be changed, however the plumbing for the
REST API will be massively simplified.

Security impact
---------------

The only security impact is around the use of policy. Previously there
was a policy point made for every extension, even if that extension
merely added a *single* display attribute to the servers
structure. These policy rules will largely be removed, and each
removal will include a release note. Judgment will be used when we
appear to be exposing a sensitive element, and in those cases we'll
leave some policy control over it.

Notifications impact
--------------------

None.

Other end user impact
---------------------

A more robust contract of what the Nova API means, and what they can
expect when using it.

Performance Impact
------------------

This simplication of resource processing may lead to better
performance of the API. However performance is not a leading driver
here.

Other deployer impact
---------------------

The deployer impact is pretty well laid out above.

Developer impact
----------------

This should dramatically lower the barrier of entry to understanding
and contributing to the API layer in Nova.


Implementation
==============

Assignee(s)
-----------

The Nova API subteam

Work Items
----------

Newton

* Fold in-tree server extensions back into the main servers.py flow
  (the hard part is getting unit tests to pass)
* Remove wsgi.extends support on servers resources
* Remove loading of nova.api.v21.extensions.server.* content
* Fold in-tree flavor extensions back into the main flavors.py flow
* Remove wsgi.extends support on flavors
* Remove pre_process / post_process resource logic from wsgi stack

Ocata

* Remove loading of nova.api.v21.extensions (these allow the creation
  of new resources even if they can't modify existing resources).

Dependencies
============

None


Testing
=======

Both Tempest and functional testing shouldn't need any further
changes. They provide confidence that we have not regressed our API.

Unit testing will be adjusted as in many case that used limited
extension lists to simplify responses for testing.


Documentation Impact
====================

The documentation mostly already reflects this reality. We no longer
talk about the extensions facility in Nova publicly.

References
==========

* The discussion in 2015 where this direction was firmly discussed on
  the mailing list - http://lists.openstack.org/pipermail/openstack-dev/2015-March/059576.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
