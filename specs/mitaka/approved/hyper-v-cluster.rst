..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============
Hyper-V Cluster
===============

https://blueprints.launchpad.net/nova/+spec/hyper-v-cluster

Hyper-V Clustering has been introduced since Windows / Hyper-V Server 2008
and it introduced several benefits such as highly available VMs, better
performance, faster live migrations and other features. [1][2][3]

Problem description
===================

Hyper-V Clustering can bring a set of advantages to advantages that are not
available otherwise and also improve the performance of existing features. A
few examples would be highly available VMs, faster live migrations, network
health detection, etc. A more detailed list of features can be found in the
References section [1][2][3].

Currently, there is no support for Hyper-V Clusters in OpenStack. This
blueprint is addressing this issue and adds an implementation.

Use Cases
----------

This feature is particularly useful for its increased performance, highly
available VMs and virtual machine and virtual machine network health
detection.


Proposed change
===============

There are two methods for creating and deploying a Hyper-V Cluster, each with
their own advantages and disadvantages:

* Option A. Hyper-V Cluster controlled by a single nova-compute service. This
  means that the nova-compute service will run on a single Hyper-V Node in a
  Cluster and can manipulate WMI objects remotely on all the Cluster Nodes.

  Advantages:

  * Consistent disk resource tracking. The Cluster Shared Storage is only
    tracked by a single compute service.
  * Smaller overhead, as only one nova-compute service will necessary, as
    oposed to one nova-compute service / node.

  Disadvantages:

  * neutron-hyperv-agent are still mandatory on every Node. Even though its
    performance has been enhanced over the past release cycles, it won't be
    able to handle port binding efficiently, VLAN tagging and creating security
    group rules for each new port (up to thousands of ports in some scenarios).
  * ceilometer-agent-compute will have to run on each Node or implementing a
    Hyper-V Cluster Inspector is necessary, in order to poll the metrics of all
    the resources.
  * Free memory tracking issue. Consider this example: 16 x Nodes Cluster, each
    having 1 GB free memory => ResourceTracker will report 16 GB free memory.
    Deploying a 2 GB instance in the Cluster fails, as there is no viable host
    for it.
  * Free vCPU tracking issue. Same as above.
  * nova-compute service might perform poorly, as it will spawn threads for
    console logging for a considerably larger number of instances, which will
    cause the serial console access to be less responsive.
  * When performing actions on an instance, extra queries will be necessary in
    the Hyper-V Cluster Driver to determine on which Node the instance resides,
    in order to properly manipulate it.
  * The Hyper-V Cluster will act as a scheduler in choosing a node for a new
    instance, resulting in poor allocation choices.
  * The underlying cluster infrastructure will be opaque and the user won't be
    be able to know on which physical node the instance resides usinf Nova API.
  * Users cannot choose to live-migrate in the same cluster. As there is only
    one compute node reported in nova, all the 'foo' instances will be deployed
    on the host 'bar' and running the command:

        nova live-migration foo bar

    will result in a UnableToMigrateToSelf exception. This will negate one of
    the Hyper-V Cluster's advantages: faster live migrations within the same
    Cluster.

* Option B. nova-compute service on each Hyper-V Cluster Node.

  Advantages:

  * Correct memory and vCPU tracking.
  * nova-scheduler will properly schedule the instances in the Cluster.
  * No decrease in nova-compute service's performance.
  * Live migrations within the same cluster are faster.

  Disadvantages:

  * Free disk resource tracking. Since all the nova-compute services will
    report on the same Cluster Shared Storage, each ResourceTracker will report
    different amount of storage used. For example, having a 500 GB shared
    storage and 2 instances with 200 GB used storage each on a single node in
    the cluster, that node will report having 100 GB free storage space, while
    other nodes, with no instances, will report as having 500 GB free. Trying
    to deploy another 200 GB instance would fail. (WIP)

This blueprint will address Option B, as its value far outweighs Option A.

Almost all the existing Hyper-V code in nova is reusable for the purpose of
creating the Hyper-V Cluster Driver, though a few changes are necessary for
Option B:

* Instances will have to added to be clustered when they are spawned.
* Need to check before live migration if the new host is in the same Cluster.
  If it is in the same Cluster, cluster live migration will have to be
  performed, otherwise, the instance will have to unclustered before doing a
  classic live migration.
* Cold migrations are still possible in Hyper-V Clusters, the same conditions
  as live migration apply.
* The instance must be unclustered before it is destroyed.
* When new instance is added to the Cluster via live migration or cold
  migration from a non-clustered Hyper-V Server or from another Cluster,
  the instance will have to be clustered.
* Develop method to query free / available disk space for a Cluster Shared
  Storage, which will be reported to the Resource Tracker.
* Develop method to ensure that only one Hyper-V compute node will fetch a
  certain glance image.

Alternatives
------------

None, in order take advantage of the benefits offered by the Hyper-V Cluster,
the instances have to be clustered.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

nova-compute service will have to run with an Active Directory user which has
Hyper-V Management priviledges on all the Hyper-V nodes.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

* Because of the cluster shared storage, the images will have to cached only
  once per cluster, instead of once per node, resulting in less storage used
  for caching and less time spent doing it.

* Because of the cluster shared storage, live migration and cold migration
  duration is greatly reduced.

* Host evacuation takes place automatically when a clustered compute node is
  put into maintenance mode or is taken down. The instances are live-migrated,
  assuring high availability.

Other deployer impact
---------------------

* Hyper-V Cluster requirements: [4]
* Creating Hyper-V Cluster: [5]
* Hyper-V nodes will have to be joined in an Active Directory.
* Hyper-V nodes will have to be joined in a Failover Cluster and the setup
  has to be validated.[6][7]
* Only nodes with the same version can be joined in the same cluster. For
  example, clusters can contain only Windows / Hyper-V Server 2012,
  Windows / Hyper-V Server 2012 R2 or Windows / Hyper-V Server 2008 R2.
* All Hyper-V nodes in the cluster must have access to the same shared cluster
  storage.
* The path to the shared storage will have to be set in the compute
  nodes' nova.conf file as such:
  instances_path=\\SHARED_STORAGE\OpenStack\Instances
* The compute_driver in compute nodes' nova.conf file will have to be set as
  such:
  compute_driver=nova.virt.hyperv.cluster.driver.HyperVClusterDriver
* The WMI namespace for the Hyper-V Cluster is '/root/MSCluster'. When using
  that namespace, the driver will fail to start due to stack overflow exception
  while instantiating the namespace. This is happens because of a missing magic
  method in the WMI module (__nonzero__). This happens in python wmi module,
  for versions 1.4.9 or older.
* Hyper-V nodes in the same Cluster should be added to the same host aggregate.
  This will ensure that the scheduler will opt for a host in the same aggregate
  for cold migration.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Claudiu Belu <cbelu@cloudbasesolutions.com>

Work Items
----------

As described in the Proposed change section.

Dependencies
============

None

Testing
=======

* Unit tests.
* Tempest tests will be able to validate this feature and they will run as part
  of the Hyper-V CI.

Documentation Impact
====================

Documentation about HyperVClusterDriver will be added.

References
==========

[1] Windows Hyper-V / Server 2012 Cluster features:
  https://technet.microsoft.com/en-us/library/dn265972.aspx#BKMK_2012

[2] Windows Hyper-V / Server 2012 R2 Cluster features:
  https://technet.microsoft.com/en-us/library/dn265972.aspx#BKMK_2012R2

[3] Hyper-V Cluster live migration:
  https://technet.microsoft.com/en-us/library/dd759249.aspx#BKMK_live

[4] Hyper-V Cluster requirements:
  https://technet.microsoft.com/en-us/library/jj612869.aspx

[5] Creating Hyper-V Cluster:
  http://blogs.technet.com/b/keithmayer/archive/2012/12/12/step-by-step-building-a-free-hyper-v-server-2012-cluster-part-1-of-2.aspx

[6] Hyper-V Cluster validation:
  https://technet.microsoft.com/en-us/library/jj134244.aspx

[7] Windows Hyper-V / Server 2012 R2 Cluster valudation:
  https://technet.microsoft.com/en-us/library/hh847274%28v=wps.630%29.aspx

History
=======
