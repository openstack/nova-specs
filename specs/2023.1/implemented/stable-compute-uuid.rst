..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Stable Compute UUIDs
====================

https://blueprints.launchpad.net/nova/+spec/stable-compute-uuid

Nova has long had a dependency on an unchanging hostname on the
compute nodes. This spec aims to address this limitation, at least
from the perspective of being able to detect an accidental change and
avoiding catastrophe in the database that can currently result from a
hostname change, whether intentional or not.

Problem description
===================

The nova-compute service does not have a strong correlation with the
unique identifier used to represent itself. In most cases, we use the
system hostname as the identifier by which we locate our Service and
ComputeNode records in the database. However, hostnames can change
(both intentionally and unintentionally) which makes this
problematic. The Nova project has long said "don't do that" although
in reality, we must be less fragile and able to detect and protect
against database corruption if it happens.

Use Cases
---------

As an operator, I want nova to be able to survive an accidental system
hostname change without damage or silent data corruption.

As an operator, I want nova to detect a hostname mismatch and avoid
corrupting its database.

As a deployment tool developer, I want to be able to pre-generate the
UUID for a given compute host being deployed so that I will know it
ahead of time, before starting the service.

Proposed change
===============

Nova will use a persistent file for storing the compute node UUID for
non-Ironic environments. If this file does not exist on startup, then
it will be created once and only once. This UUID will serve to provide
a stable lookup of the ComputeNode object in the database which
represents a given nova-compute instance. This identification file
should be able to live in a non-writable (by `nova-compute`) location
and treated like config, but also in a writable location and treated
like state. The latter is important to avoid adding a required
mandatory deployment step.

The compute service will use this locally-persisted UUID to reliably
find the ComputeNode record, and will check for a potential hostname
(or CONF.host) change on startup. If such a rename is detected,
`nova-compute` will fail to start and warn about the situation.

This file will be named `compute_id` and will be honored in the first
location found in any of the following locations:

- The parent directory of any file in `CONF.config_files`
- The directory specified in `CONF.state_path`

For safety, all of the above locations will always be searched and any
`compute_id` files found will be examined. If there are any
discrepancies (i.e. more than one files with non-identical contents),
an error will be logged and `nova-compute` will refuse to start.

The file format will be a single 36-character string containing a UUID
in canonical text representation (i.e. `uuidgen > /path/to/file`).

If `nova-compute` is started and no `compute_id` file is found, it
will be created once and initialized with a UUID in the
`CONF.state_path` location.

For configurations where the driver is set to Ironic, we will do no
persistence of the compute node, since there is not a 1:1 mapping
between `nova-compute` instances and Ironic nodes. The mapping that
Ironic pushes up (via `get_available_nodes()`) will be assumed to be
correct.

Note that all drivers in Nova other than Ironic manage a single
compute node. Ironic is "special" in this regard and thus will be
special-cased for this effort.

Alternatives
------------

We could choose a more complex format with room for additional data or
attributes in the future. I would argue that files are cheap, easy(er)
for deployment tools to write (i.e. `uuidgen > /path/to/file`), and
avoids the potential need for versioning and migration.

We could make `CONF.hostname` not optional and not defaulted to
`socket.gethostname()`. This may be a simpler approach, but it is
unlikely to be favored by deployers and deployment tool writers. It
also does not provide a path to being able to actually support
hostname changes in the future.

There is already some data persistence in the
`${state_dir}/instances/compute_nodes` file, which is JSON-encoded and
maintained by the image cache code. I think this is a less-good idea
because it's stored in a place that is potentially shared among
multiple (but not all) compute nodes and thus may provide a difficult
path to stable "who am I?" determination.

We could use `/etc/machine-id` or some amount of it. It's not a UUID,
but it's close. It's also a freedesktop/systemd thing and may not
exist everywhere, especially in a containerized environment.

Data model impact
-----------------

Right now we generate new UUIDs for records in `compute_nodes` in two
ways:

- For most drivers, it occurs rather deep in the object, in the
  remotable `create()` method. That means they actually get generated
  on the conductor node, if the virt driver does not provide a uuid
  resulting in the resource tracker calling `create()` with no UUID
  specified.
- For Ironic, the virt driver provides a uuid in the resources dict,
  which causes it to be created with the desired node id from the
  start.

So, while not a data model impact directly, this effort will move to
always providing a `ComputeNode.uuid` value when the record is
created, either because we read it from the persistent file, or
pre-generated it to write the file.

REST API impact
---------------

None.

Security impact
---------------

The preferred location for the `compute_id` file is in one of the
config file directories, which should be non-writable by Nova
itself. If one is not provided, nova will create that file in
`CONF.state_dir` which will leave it writable by the user under which
`nova-compute` runs. This could potentially provide a path to
disruption, although if an attacker gains access to write things owned
by that user, all the instance disks and configs are similarly
exposed.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

The deployer will not be impacted by default, but will gain the
ability to pin the compute node's UUID as config, if desired.

Developer impact
----------------

None.

Upgrade impact
--------------

For the 2023.1 cycle, nova-compute will need to gracefully handle the
case where there *is* a `ComputeNode` that represents its service,
which has not yet been persisted to the `compute_id` file. We will
need to communicate this in the release notes, warning of the danger
of getting it wrong (which is pretty much the same as a rename
today). For the period in which we support this compatibility
behavior, we can use the `Service.version` that we find attached to
our `ComputeNode` object to determine whether or not we should write
an existing UUID to the `compute_id` file or generate it from
scratch. In a subsequent release we should remove that behavior
(although potentially retain a start-blocking check if the version is
being upgraded across that boundary).


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Feature Liaison
---------------

Feature liaison:
  sean-k-mooney


Work Items
----------

- Write and test routines for reading, writing, and sanity-checking
  the `compute_id` files.
- Wire up the `init_host()` logic to ensure the compatibility behavior
  of writing existing compute node UUIDs to the file.
- Modify the existing compute node creation logic to honor/generate
  the persistent `compute_id`.

Dependencies
============

None.

Testing
=======

Unit and functional testing will be sufficient coverage for
this. We will get grenade and greenfield devstack coverage by default,
and perhaps we can ensure that the file is created in job post scripts.


Documentation Impact
====================

The installation guide will need changes to describe the purpose and
behavior of this file. Obviously release notes will be needed for
signaling.

References
==========

- This is part of a larger multi-cycle effort to
  `robustify compute hostnames`_.

.. _`robustify compute hostnames`: https://specs.openstack.org/openstack/nova-specs/specs/backlog/robustify-compute-hostnames.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 Antelope
     - Introduced
