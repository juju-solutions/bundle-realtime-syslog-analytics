#!/usr/bin/env python3

import re
import os
import unittest
import textwrap

import yaml
import amulet


class TestBundle(unittest.TestCase):
    bundle_file = os.path.join(os.path.dirname(__file__), '..', 'bundle-local.yaml')

    @classmethod
    def setUpClass(cls):
        cls.d = amulet.Deployment(series='trusty')
        with open(cls.bundle_file) as f:
            bun = f.read()
        bundle = yaml.safe_load(bun)
        cls.d.load(bundle)
        cls.d.setup(timeout=1800)
        cls.d.sentry.wait_for_messages({
            'slave': 'Ready',
            'plugin': 'Ready',
            'zeppelin': 'Ready',
            'flume-syslog': 'Ready',
        }, timeout=1800)
        cls.hdfs = cls.d.sentry['namenode'][0]
        cls.yarn = cls.d.sentry['resourcemanager'][0]
        cls.slave = cls.d.sentry['slave'][0]
        cls.spark = cls.d.sentry['spark'][0]
        cls.zeppelin = cls.d.sentry['zeppelin'][0]

    def test_components(self):
        """
        Confirm that all of the required components are up and running.
        """
        hdfs, retcode = self.hdfs.run("pgrep -a java")
        yarn, retcode = self.yarn.run("pgrep -a java")
        slave, retcode = self.slave.run("pgrep -a java")
        secondary, retcode = self.secondary.run("pgrep -a java")
        spark, retcode = self.spark.run("pgrep -a java")

        # .NameNode needs the . to differentiate it from SecondaryNameNode
        assert '.NameNode' in hdfs, "NameNode not started"
        assert '.NameNode' not in yarn, "NameNode should not be running on resourcemanager"
        assert '.NameNode' not in slave, "NameNode should not be running on slave"
        assert '.NameNode' not in spark, "NameNode should not be running on spark"

        assert 'ResourceManager' in yarn, "ResourceManager not started"
        assert 'ResourceManager' not in hdfs, "ResourceManager should not be running on namenode"
        assert 'ResourceManager' not in slave, "ResourceManager should not be running on slave"
        assert 'ResourceManager' not in spark, "ResourceManager should not be running on spark"

        assert 'JobHistoryServer' in yarn, "JobHistoryServer not started"
        assert 'JobHistoryServer' not in hdfs, "JobHistoryServer should not be running on namenode"
        assert 'JobHistoryServer' not in slave, "JobHistoryServer should not be running on slave"
        assert 'JobHistoryServer' not in spark, "JobHistoryServer should not be running on spark"

        assert 'NodeManager' in slave, "NodeManager not started"
        assert 'NodeManager' not in yarn, "NodeManager should not be running on resourcemanager"
        assert 'NodeManager' not in hdfs, "NodeManager should not be running on namenode"
        assert 'NodeManager' not in spark, "NodeManager should not be running on spark"

        assert 'DataNode' in slave, "DataServer not started"
        assert 'DataNode' not in yarn, "DataNode should not be running on resourcemanager"
        assert 'DataNode' not in hdfs, "DataNode should not be running on namenode"
        assert 'DataNode' not in spark, "DataNode should not be running on spark"

        assert 'spark' in spark, 'Spark should be running on spark'
        assert 'zeppelin' in spark, 'Zeppelin should be running on spark'

    def test_hdfs_dir(self):
        """
        Validate admin few hadoop activities on HDFS cluster.
            1) This test validates mkdir on hdfs cluster
            2) This test validates change hdfs dir owner on the cluster
            3) This test validates setting hdfs directory access permission on the cluster

        NB: These are order-dependent, so must be done as part of a single test case.
        """
        output, retcode = self.spark.run("su hdfs -c 'hdfs dfs -mkdir -p /user/ubuntu'")
        assert retcode == 0, "Created a user directory on hdfs FAILED:\n{}".format(output)
        output, retcode = self.spark.run("su hdfs -c 'hdfs dfs -chown ubuntu:ubuntu /user/ubuntu'")
        assert retcode == 0, "Assigning an owner to hdfs directory FAILED:\n{}".format(output)
        output, retcode = self.spark.run("su hdfs -c 'hdfs dfs -chmod -R 755 /user/ubuntu'")
        assert retcode == 0, "seting directory permission on hdfs FAILED:\n{}".format(output)
        output, retcode = self.spark.run("su hdfs -c 'hdfs dfs -rmdir /user/ubuntu'")

    def test_yarn_mapreduce_exe(self):
        """
        Validate yarn mapreduce operations:
            1) validate mapreduce execution - writing to hdfs
            2) validate successful mapreduce operation after the execution
            3) validate mapreduce execution - reading and writing to hdfs
            4) validate successful mapreduce operation after the execution
            5) validate successful deletion of mapreduce operation result from hdfs

        NB: These are order-dependent, so must be done as part of a single test case.
        """
        jar_file = '/usr/lib/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar'
        test_steps = [
            ('teragen',      "su ubuntu -c 'hadoop jar {} teragen  10000 /user/ubuntu/teragenout'".format(jar_file)),
            ('mapreduce #1', "su hdfs -c 'hdfs dfs -ls /user/ubuntu/teragenout/_SUCCESS'"),
            ('terasort',     "su ubuntu -c 'hadoop jar {} terasort /user/ubuntu/teragenout /user/ubuntu/terasortout'".
                format(jar_file)),
            ('mapreduce #2', "su hdfs -c 'hdfs dfs -ls /user/ubuntu/terasortout/_SUCCESS'"),
            ('cleanup',      "su hdfs -c 'hdfs dfs -rm -r /user/ubuntu/teragenout'"),
        ]
        for name, step in test_steps:
            output, retcode = self.spark.run(step)
            assert retcode == 0, "{} FAILED:\n{}".format(name, output)

    def test_spark(self):
        output, retcode = self.spark.run("su ubuntu -c 'bash -lc /home/ubuntu/sparkpi.sh 2>&1'")
        assert 'Pi is roughly' in output, 'SparkPI test failed: %s' % output

    def test_ingest(self):
        self.spark.ssh('ls /home/ubuntu')  # ensure at least one pure ssh session for the logs
        for i in amulet.helpers.timeout_gen(60 * 5):  # wait for the log messages to be ingested
            output, retcode = self.spark.run("su hdfs -c 'hdfs dfs -ls /user/flume/flume-syslog/*/*'")
            if retcode == 0 and 'FlumeData' in output:
                break

        ssh_count = textwrap.dedent("""
            from pyspark import SparkContext
            sc = SparkContext(appName="ssh-count")
            count = sc.textFile("/user/flume/flume-syslog/*/*").filter(lambda line: "sshd" in line).count()
            print "SSH Logins: %s" % count
        """)
        output, retcode = self.spark.run("cat << EOP > /home/ubuntu/ssh-count.py\n{}\nEOP".format(ssh_count))
        assert retcode == 0
        output, retcode = self.spark.run("su ubuntu -c 'spark-submit --master yarn-client /home/ubuntu/ssh-count.py'")
        assert re.search(r'SSH Logins: [1-9][0-9]*', output), 'ssh-count.py failed: %s' % output

    def test_zeppelin(self):
        pass  # requires javascript; how to test?


if __name__ == '__main__':
    unittest.main()
