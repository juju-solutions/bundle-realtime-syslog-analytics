## Overview

This bundle is an 8 node cluster designed to scale out. Built around Apache
Hadoop components, it contains the following units:

  * 1 NameNode (HDFS)
    - 1 Rsyslog Forwarder (colocated on the NameNode)
  * 1 ResourceManager (YARN)
  * 3 Slaves (DataNode and NodeManager)
  * 1 Flume-HDFS
    - 1 Plugin (colocated on the Flume unit)
  * 1 Flume-Syslog
  * 1 Spark
    - 1 Plugin (colocated on the Spark unit)
    - 1 Zeppelin (colocated on the Spark unit)

Syslog events generated on the NameNode unit are forwarded to the
`apache-flume-syslog` charm. These events are serialized and sent to the
`apache-flume-hdfs` charm to be stored in HDFS. We have included a sample
application to analyze these events with Spark/Zeppelin.


## Usage

A working Juju installation is assumed to be present. If you have not yet set
up Juju, please follow the
[getting-started](https://jujucharms.com/docs/2.0/getting-started) instructions
prior to deploying this bundle. Once ready, deploy this bundle with the
`juju deploy` command:

    juju deploy realtime-syslog-analytics

Alternatively, you can deploy using `conjure-up`. This provides a text-based
walkthrough of bundle options that you may want to adjust at deploy time:

    sudo apt install conjure-up
    conjure-up bigdata-syslog-analytics

_**Note**: The above assumes Juju 2.0 or greater. If using an earlier version
of Juju, use [juju-quickstart](https://launchpad.net/juju-quickstart) with the
following syntax: `juju quickstart cs:bundle/realtime-syslog-analytics`._

Once deployment is complete, expose Zeppelin:

    juju expose zeppelin

You may now access the Zeppelin web interface at
`http://{zeppelin_ip_address}:9090`. The ip address can be found by running
`juju status --format=yaml zeppelin | grep public-address`.


## Verify the deployment

### Status
The applications that make up this bundle provide status messages to
indicate when they are ready:

    juju status

This is particularly useful when combined with `watch` to track the on-going
progress of the deployment:

    watch -n 0.5 juju status

The message for each unit will provide information about that unit's state.
Once they all indicate that they are ready, you can perform a smoke test
to verify that the bundle is working as expected.

### Smoke Test
The charms for each core component (namenode, resourcemanager, spark, zeppelin)
provide a `smoke-test` action that can be used to verify the application is
functioning as expected. You can run them all with the following:

    juju run-action namenode/0 smoke-test
    juju run-action resourcemanager/0 smoke-test
    juju run-action spark/0 smoke-test
    juju run-action zeppelin/0 smoke-test

_**Note**: The above assumes Juju 2.0 or greater. If using an earlier version
of Juju, the syntax is `juju action do <application>/0 smoke-test`._

You can watch the progress of the smoke test actions with:

    watch -n 0.5 juju show-action-status

_**Note**: The above assumes Juju 2.0 or greater. If using an earlier version
of Juju, the syntax is `juju action status`._

Eventually, all of the actions should settle to `status: completed`.  If
any report `status: failed`, that application is not working as expected. Get
more information about a specific smoke test with:

    juju show-action-output <action-id>

_**Note**: The above assumes Juju 2.0 or greater. If using an earlier version
of Juju, the syntax is `juju action fetch <action-id>`._


## Scale Out Usage

This bundle was designed to scale out. To increase the amount of hadoop
slaves, simple add more units. To add one unit:

    juju add-unit slave

You can also add multiple units, for example, to add four more slaves:

    juju add-unit -n4 slave


## Contact Information

- <bigdata@lists.ubuntu.com>


## Help

- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
- [Juju community](https://jujucharms.com/community)
