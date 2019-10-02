..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Image Pre-caching support
=========================

https://blueprints.launchpad.net/nova/+spec/image-precache-support

Nova supports caching images on demand at the compute node level for
performance reasons, but provides no ability to schedule that activity
before a rollout or maintenance window. This long-requested feature
becomes even more important when considering Edge Computing
environments, limited bandwidth, as well as high-scale rapid
application deployment.


Problem description
===================

Several of the virt drivers in Nova support the caching of base images
for improved boot performance. The first time an instance is booted
from a given image, that base image is downloaded from glance, cached,
and either copied or CoW'd to create the actual instance root
disk. Subsequent instance boots from the same image can re-use the
cached copy of the base image instead of downloading it again from
Glance. This behavior provides the following benefits:

- Decreased load on the Glance server(s)
- Decreased network utilization
- Decreased time-to-boot latency for the second and subsequent
  instances

The latter is particularly important for situations where new
application rollouts must be performed within a specific time window,
or where scale-up operations are expected to happen quickly in
response to changing load conditions. Specifically, it can be
important to ensure that a new image is cached on all of the relevant
compute nodes prior to the upgrade window opening, or before load
unexpectedly spikes.

Further, in situations where compute nodes may be remotely located in
environments where network bandwidth is limited (such as many edge
computing environments), it may be very important to push a new base
image to those nodes during times of low utilization or a maintenance
window, such that the image download process does not consume a
massive amount of bandwidth during normal operation.

Because Nova does not provide a way to seed this process from the
outside, operators are currently forced to hack around the
problem. Some of the workarounds we know are being used include:

- Pre-booting throwaway instances on each compute node by hand to
  seed the cache before deploying the real ones
- Copying the images directly into the cache directories on the
  compute nodes out of band
- Modifying the Nova code themselves to provide this functionality
- Using a shared storage volume for the image cache (which is known to
  be broken)
- Using a totally different ephemeral backend, such as ceph which
  side-steps the problem entirely (but requires a substantially larger
  investment)

Use Cases
---------

- As an operator of a cloud with remote compute nodes at the network
  edge, I want to be able to pre-cache images during maintenance
  windows in order to avoid the network spike involved with spinning
  up a new instance and pulling the base image on demand.
- As a user of a cloud which supports an application that is
  frequently re-deployed en masse, I want to be able to pre-cache new
  images at computes before my rollout window to limit my application
  downtime to purely the time needed to respawn or rebuild instances.


Proposed change
===============

This functionality has been proposed and requested multiple times, but
failed to gain traction amongst the team for various reasons. Thus,
this spec proposes a minimally viable initial implementation which
addresses the need for pre-caching, but does not provide specific
visibility, reporting, scheduling, or other advanced features.

Initially we will add a mechanism to Nova, by which a
(sufficiently-privileged) user can request that a set of images be
cached on the set of compute nodes contained within a host
aggregate. This activity will be delegated to a (super-)conductor
worker, which will:

- Validate the images provided (for existence and accessibility, to
  avoid asking a ton of computes to do something impossible)
- Look up the list of hosts in the given aggregate
- Collate the hosts by cell
- Iterate through those hosts making an RPC request to start the
  operation

If we were to fire off all those requests via RPC casts to be handled
asynchronously, we would surely DDoS the image service. Throttling
that appropriately could be done in many ways and is easily the
subject of a dedicated subsequent spec. In this initial revision, we
will introduce a configurable parallelism limit, which will cause
conductor to contact that many computes in parallel to trigger their
downloads, using the long-running RPC call functionality to wait for
completion.

Images will be cached on each compute using a new method on the virt
driver which, when implemented, will re-use the image downloading
routines already employed during image boot. Images that are cached
via this mechanism will be subjected to the same expiry and purge
rules as those downloaded on demand as a result of instance
boots. Subsequent calls to cache an image that is already resident
should reset the expiry timer (if applicable) from the cache. In the
case of the existing drivers that use the ``imagecache`` module, we
will just need to *touch* them to update their ``mtime``.

Alternatives
------------

One alternative is always to do nothing. This has been requested and
proposed many times in the past, and people are currently living
without it and/or working around the limitation on their own.

Another option would be to take a similar approach, but dispense with
the incremental nature. We could implement a larger API, with task and
progress reporting, scheduling (image X should be cached for Y hours,
etc) and other features that have been part of previous requests. The
reason to not do this is to avoid the risk of never completing this
because of the multitude of rabbit holes that open up with a larger
scope. See the references section for a partial list of previous
attempts that were never completed.

Data model impact
-----------------

None in this initial iteration. In the future, it may be desirable to
track images and status per-compute, which would require some
accounting in the database.

REST API impact
---------------

It may technically make more sense to put this function under the
images API in Nova. However, that is marked as deprecated
currently. Since this is primarily based on the aggregate model, this
proposes to add this as an action on an aggregate.

os-aggregates
~~~~~~~~~~~~~

A new route under the aggregate for ``images`` will be added for cache
management.

* ``POST /os-aggregates/{aggregate_id}/images`` (returns 202 on success)

  .. code-block:: json

     {
       "cache": [
         {"id": "a26887c6-c47b-4654-abb5-dfadf7d3f803"},
         {"id": "4d8c3732-a248-40ed-bebc-539a6ffd25c0"}
       ]
     }

Because we are attempting to provide a minimally-viable initial
implementation, the structure of the request is defined so that it
will be possible to add additional information in future
versions. This may include additional per-image information (such as
priority, TTL, etc) or information per-request, such as parallelism,
download rate, etc.

Security impact
---------------

Obviously allowing any user to initiate a wide-scale moving of data
brings some inherent risk. As this proposes to be aggregate-based, the
user would likely need to already have at least the ability to list
host aggregates in order to provide one to the caching API. A policy
knob defining which users have that ability would default to the
existing ones with ability to manage host aggregates.

Notifications impact
--------------------

Without any API-based reporting of progress per-compute, emitting
notifications about the start and completion of image downloads could
be helpful. This would allow operators to monitor the process.

Other end user impact
---------------------

The clients will obviously need to gain the ability to hit this
API. Regular users should be entirely unaffected, other than
potentially noticing improved boot performance.

Performance Impact
------------------

The primary goal of this change is to improve performance of instance
boots after the images are pre-cached. Certainly during the
pre-caching operation, there will be some additional load on the image
service, conductor workers coordinating the task, as well as the
computes doing the work. The actual image download operation on the
computes will use the same code paths that are currently used during
image boot.

Other deployer impact
---------------------

Deployers will need to determine which users should be allowed to
access this caching API, if any, and modify the policy accordingly.

Developer impact
----------------

This will require a new RPC method on the conductor, compute, and a
corresponding call to the virt driver. Currently, the ``libvirt``,
``hyperv``, and ``vmwareapi`` drivers use the imagecache. Initial
support will be provided for the ``libvirt`` driver, but should be
relatively easy for the other two given they re-use the ``imagecache``
module.

Upgrade impact
--------------

As this initial revision of the function is best-effort, with no real
reporting or guarantees that the images are cached and by any
deadline, the upgrade impact is minimal. If the compute RPC API is
pinned to a version lower than required to make this call, then no
computes will be contacted to pre-cache the images.

If the caching call is made against computes running virt drivers that
are not yet (or ever) able to participate, a warning log message will
be emitted by the base virt driver.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

- Extend the base virt driver to contain a ``cache_image()`` method
  which takes an image id. Default behavior is a ``NotImplemented``
  exception.
- Implement the ``cache_image()`` method in the libvirt driver
- Add the new RPC call to the compute manager which delegates to the
  virt driver. If ``NotImplemented`` is raised, a warning message is
  logged about the lack of support.
- Add the new RPC call to the conductor manager to look up, collate
  per cell, and call to the relevant computes.
- Add a new REST API call allowing the user to make this request.
- Add a client implementation for making this call.


Dependencies
============

Patches against openstackclient, novaclient, and nova will be inter-dependent.


Testing
=======

As this initial phase of implementation provides no externally-visible
changes to a running deployment, testing with tempest would have to
rely on something obscure like time-to-boot latency to determine
success. Thus, functional tests will be added to ensure that the image
cache is populated by the new call, and that subsequent instance boots
do not contact the image service to perform the download.


Documentation Impact
====================

This feature needs documentation for the operators in the admin guide,
and of course api-ref changes.

References
==========

- Proposal from 2011 where image caching was initially added, showing that pre-cache was an intended improvement after the initial implementation: https://wiki.openstack.org/wiki/Nova-image-cache-management
- Blueprint from 2013 proposing an alternate way to boot images to initial cache-seeding download: https://blueprints.launchpad.net/nova/+spec/effective-template-base-image-preparing
- Blueprint from 2013 proposing more configurable image cache implementations, offering at least the ability to pin images on computes: https://blueprints.launchpad.net/nova/+spec/multiple-image-cache-handlers
- Blueprint from 2014 proposing an entire new nova service for pre-caching images: https://blueprints.launchpad.net/nova/+spec/image-precacher
- Blueprint from 2014 proposing a P2P-style sharing of image cache repositories between computes (amongst other things): https://blueprints.launchpad.net/nova/+spec/thunderboost
- Blueprint from 2014 proposing multiple mechanisms (including P2P) for pre-caching images on computes: https://blueprints.launchpad.net/nova/+spec/compute-image-precache
- Blueprint from 2014 proposing a VMware-specific way to avoid the initial cache-seeding download from glance: https://blueprints.launchpad.net/nova/+spec/datastore-image-cache-update-improvements
- Blueprint from 2014 proposing adding xenapi driver image caching as a step towards pre-caching: https://blueprints.launchpad.net/nova/+spec/xenapi-image-cache-management
- Blueprint from 2015 proposing a weigher to prefer computes with a specific image already cached: https://blueprints.launchpad.net/nova/+spec/node-cached-image-weigher
- Blueprint from 2015 proposing a pre-caching mechanism: https://blueprints.launchpad.net/nova/+spec/proactive-nova-image-caching
- Mailing list thread from 2015 starting with a request, and containing a response about some of the discussion we have had in the past about such a thing: http://lists.openstack.org/pipermail/openstack-dev/2015-August/072457.html
- Presentation from 2018 by Workday in Berlin about their local modifications (against Mitaka) to do image pre-caching: https://youtu.be/hx_MdGI7fcc?t=947
- Bug from 2018 where someone is trying to work around the lack of pre-caching with shared cache on NFS: https://bugs.launchpad.net/nova/+bug/1804262

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
