# Realtime Syslog Analytics

This bundle is a 9 node cluster designed to scale out. Built around Apache
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

Deploy this bundle using juju-quickstart:

    juju quickstart u/bigdata-dev/realtime-syslog-analytics

See `juju quickstart --help` for deployment options, including machine
constraints and how to deploy a locally modified version of the
`realtime-syslog-analytics` bundle.yaml.

Once deployment is complete, expose the zeppelin service:

    juju expose zeppelin

You may now access the Zeppelin web interface at
`http://{spark_unit_ip_address}:9090`. The ip address can be found by running
`juju status spark | grep public-address`.


## Testing the deployment

The services provide extended status reporting to indicate when they are ready:

    juju status --format=tabular

This is particularly useful when combined with `watch` to track the on-going
progress of the deployment:

    watch -n 0.5 juju status --format=tabular

The message for each unit will provide information about that unit's state.
Once they all indicate that they are ready, you can use the provided `terasort`
action to test that the Apache Hadoop components are working as expected:

    juju action do plugin/0 terasort
    watch juju action status

Once the action is complete, you can retrieve the results:

    juju action fetch <action-id>

The `<action-id>` value will be in the `juju action status` output.


## Scale Out Usage

This bundle was designed to scale out. To increase the amount of Compute
Slaves, you can add units to the compute-slave service. To add one unit:

    juju add-unit slave

You can also add multiple units, for examle, to add four more compute slaves:

    juju add-unit -n4 slave


## Contact Information

- <bigdata@lists.ubuntu.com>


## Help

- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
- [Juju community](https://jujucharms.com/community)
