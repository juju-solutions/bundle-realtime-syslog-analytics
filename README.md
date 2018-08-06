<!--
  Licensed to the Apache Software Foundation (ASF) under one or more
  contributor license agreements.  See the NOTICE file distributed with
  this work for additional information regarding copyright ownership.
  The ASF licenses this file to You under the Apache License, Version 2.0
  (the "License"); you may not use this file except in compliance with
  the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
-->
# Overview

The Apache Hadoop software library is a framework that allows for the
distributed processing of large data sets across clusters of computers
using a simple programming model.

Hadoop is designed to scale from a few servers to thousands of machines,
each offering local computation and storage. Rather than rely on hardware
to deliver high-availability, Hadoop can detect and handle failures at the
application layer. This provides a highly-available service on top of a cluster
of machines, each of which may be prone to failure.

Apache Flume is a distributed, reliable, and highly available service for
collecting, aggregating, and moving large amounts of log data. It has a simple
and flexible architecture based on streaming data flows. Learn more at
[flume.apache.org][].

Apache Zeppelin is a web-based notebook that enables interactive data analytics.
It allows for beautiful data-driven, interactive, and collaborative documents
with SQL, Scala and more. Learn more at [zeppelin.apache.org][].

This bundle provides a complete deployment of Hadoop and Zeppelin components
from [Apache Bigtop][]. By leveraging these components along with Rsyslog and
Flume, this bundle provides a robust environment for analysing syslog events.

[flume.apache.org]: http://flume.apache.org/
[zeppelin.apache.org]: http://zeppelin.apache.org/
[Apache Bigtop]: http://bigtop.apache.org/

## Bundle Composition

The applications that comprise this bundle are spread across 6 units as
follows:

  * NameNode v2.7.3
  * ResourceManager v2.7.3
    * Colocated on the NameNode unit
  * Slave (DataNode and NodeManager) v2.7.3
    * 3 separate units
  * Client (Hadoop endpoint)
  * Plugin (Facilitates communication with the Hadoop cluster)
    * Colocated on the Client unit
  * Zeppelin v0.7.2
    * Colocated on the Client unit
  * Flume-HDFS v1.6.0
    * Colocated on the Client unit
  * Flume-Syslog v1.6.0

Syslog events generated on the Client unit are forwarded to the
`apache-flume-syslog` charm. These events are serialized and sent to the
`apache-flume-hdfs` charm to be stored in HDFS. A sample web notebook
is included to analyze these events using the Zeppelin spark interpreter.

Deploying this bundle results in a fully configured Apache Bigtop
cluster on any supported cloud, which can be scaled to meet workload
demands.


# Deploying

This bundle requires Juju 2.0 or greater. If Juju is not yet set up, please
follow the [getting-started][] instructions prior to deploying this bundle.

> **Note**: This bundle requires hardware resources that may exceed limits
of Free-tier or Trial accounts on some clouds. To deploy to these
environments, modify a local copy of [bundle.yaml][] to set
`services: 'X': num_units: 1` and `machines: 'X': constraints: mem=3G` as
needed to satisfy account limits.

Deploy this bundle from the Juju charm store with the `juju deploy` command:

    juju deploy realtime-syslog-analytics

Alternatively, deploy a locally modified `bundle.yaml` with:

    juju deploy /path/to/bundle.yaml

The charms in this bundle can also be built from their source layers in the
[Bigtop charm repository][].  See the [Bigtop charm README][] for instructions
on building and deploying these charms locally.

## Network-Restricted Environments
Charms can be deployed in environments with limited network access. To deploy
in this environment, configure a Juju model with appropriate proxy and/or
mirror options. See [Working offline][] for more information.

[getting-started]: https://docs.jujucharms.com/2.4/en/getting-started
[bundle.yaml]: https://github.com/juju-solutions/bundle-realtime-syslog-analytics/blob/master/bundle.yaml
[Bigtop charm repository]: https://github.com/apache/bigtop/tree/master/bigtop-packages/src/charm
[Bigtop charm README]: https://github.com/apache/bigtop/blob/master/bigtop-packages/src/charm/README.md
[Working offline]: https://docs.jujucharms.com/2.4/en/charms-offline


# Verifying

## Status
The applications that make up this bundle provide status messages to indicate
when they are ready:

    juju status

This is particularly useful when combined with `watch` to track the on-going
progress of the deployment:

    watch -n 2 juju status

The message for each unit will provide information about that unit's state.
Once they all indicate that they are ready, perform application smoke tests
to verify that the bundle is working as expected.

## Smoke Test
The charms for each core component (namenode, resourcemanager, slave, and
zeppelin) provide a `smoke-test` action that can be used to verify the
application is functioning as expected. Note that the 'slave' component runs
extensive tests provided by Apache Bigtop and may take up to 30 minutes to
complete. Run the smoke-test actions as follows:

    juju run-action namenode/0 smoke-test
    juju run-action resourcemanager/0 smoke-test
    juju run-action slave/0 smoke-test
    juju run-action zeppelin/0 smoke-test

Watch the progress of the smoke test actions with:

    watch -n 2 juju show-action-status

Eventually, all of the actions should settle to `status: completed`.  If
any report `status: failed`, that application is not working as expected. Get
more information about a specific smoke test with:

    juju show-action-output <action-id>

## Utilities
Applications in this bundle include command line and web utilities that
can be used to verify information about the cluster.

From the command line, show the HDFS dfsadmin report and view the current list
of YARN NodeManager units with the following:

    juju run --application namenode "su hdfs -c 'hdfs dfsadmin -report'"
    juju run --application resourcemanager "su yarn -c 'yarn node -list'"

To access the HDFS web console, find the `Public address` of the namenode
application and expose it:

    juju status namenode
    juju expose namenode

The web interface will be available at the following URL:

    http://NAMENODE_PUBLIC_IP:50070

To access the Resource Manager web consoles, find the `Public address` of the
resourcemanager application and expose it:

    juju status resourcemanager
    juju expose resourcemanager

The YARN and Job History web interfaces will be available at the following URLs:

    http://RESOURCEMANAGER_PUBLIC_IP:8088
    http://RESOURCEMANAGER_PUBLIC_IP:19888

To access the Zeppelin web console, find the `Public address` of the
zeppelin application and expose it:

    juju status zeppelin
    juju expose zeppelin

The Zeppelin web interface will be available at the following URL:

    http://ZEPPELIN_PUBLIC_IP:9080


# Scaling

By default, three Hadoop slave units are deployed with this bundle. Scaling
this application is as simple as adding more units. To add one unit:

    juju add-unit slave

Multiple units may be added at once.  For example, add four more slave units:

    juju add-unit -n4 slave


# Issues

File an issue for this bundle at:

https://github.com/juju-solutions/bundle-realtime-syslog-analytics/issues


# Contact Information

- <bigdata@lists.ubuntu.com>


# Resources

- [Apache Bigtop home page](http://bigtop.apache.org/)
- [Apache Bigtop issue tracking](http://bigtop.apache.org/issue-tracking.html)
- [Apache Bigtop mailing lists](http://bigtop.apache.org/mail-lists.html)
- [Juju Big Data](https://jujucharms.com/big-data)
- [Juju Bigtop charms](https://jujucharms.com/q/bigtop)
- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
