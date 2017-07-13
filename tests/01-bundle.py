#!/usr/bin/env python3

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from operator import itemgetter
from urllib.parse import urljoin
from time import sleep

import amulet
import json
import os
import re
import requests
import textwrap
import unittest
import yaml


class TestBundle(unittest.TestCase):
    bundle_file = os.path.join(os.path.dirname(__file__), '..', 'bundle.yaml')

    @classmethod
    def setUpClass(cls):
        cls.d = amulet.Deployment(series='xenial')
        with open(cls.bundle_file) as f:
            bun = f.read()
        bundle = yaml.safe_load(bun)

        # NB: strip machine ('to') placement. We don't seem to be guaranteed
        # the same machine numbering after the initial bundletester deployment,
        # so we might fail when redeploying --to a specific machine to run
        # these bundle tests. This is ok because all charms in this bundle are
        # using 'reset: false', so we'll already have our deployment just the
        # way we want it by the time this test runs. This was originally
        # raised as:
        #  https://github.com/juju/amulet/issues/148
        for service, service_config in bundle['services'].items():
            if 'to' in service_config:
                del service_config['to']

        cls.d.load(bundle)
        cls.d.expose('zeppelin')
        cls.d.setup(timeout=3600)
        # we need units reporting ready before we attempt our smoke tests
        cls.d.sentry.wait_for_messages({'client': re.compile('ready'),
                                        'flume-hdfs': re.compile('Ready'),
                                        'flume-syslog': re.compile('Ready'),
                                        'namenode': re.compile('ready'),
                                        'resourcemanager': re.compile('ready'),
                                        'slave': re.compile('ready'),
                                        'zeppelin': re.compile('ready'),
                                        }, timeout=3600)
        cls.hdfs = cls.d.sentry['namenode'][0]
        cls.yarn = cls.d.sentry['resourcemanager'][0]
        cls.slave = cls.d.sentry['slave'][0]
        cls.zeppelin = cls.d.sentry['zeppelin'][0]
        # Roll flume output every 10 seconds so we don't have to wait
        # for the default 5 minute roll.
        cls.d.configure('flume-hdfs', {'roll_interval': 10})

    def test_components(self):
        """
        Confirm that all of the required components are up and running.
        """
        hdfs, retcode = self.hdfs.run("pgrep -a java")
        yarn, retcode = self.yarn.run("pgrep -a java")
        slave, retcode = self.slave.run("pgrep -a java")
        zeppelin, retcode = self.zeppelin.run("pgrep -a java")

        assert 'NameNode' in hdfs, "NameNode not started"
        assert 'NameNode' not in slave, "NameNode should not be running on slave"

        assert 'ResourceManager' in yarn, "ResourceManager not started"
        assert 'ResourceManager' not in slave, "ResourceManager should not be running on slave"

        assert 'JobHistoryServer' in yarn, "JobHistoryServer not started"
        assert 'JobHistoryServer' not in slave, "JobHistoryServer should not be running on slave"

        assert 'NodeManager' in slave, "NodeManager not started"
        assert 'NodeManager' not in yarn, "NodeManager should not be running on resourcemanager"
        assert 'NodeManager' not in hdfs, "NodeManager should not be running on namenode"

        assert 'DataNode' in slave, "DataNode not started"
        assert 'DataNode' not in yarn, "DataNode should not be running on resourcemanager"
        assert 'DataNode' not in hdfs, "DataNode should not be running on namenode"

        assert 'ZeppelinServer' in zeppelin, 'ZeppelinServer should be running on zeppelin'

    def test_hdfs(self):
        """
        Validates mkdir, ls, chmod, and rm HDFS operations.
        """
        uuid = self.hdfs.run_action('smoke-test')
        result = self.d.action_fetch(uuid, timeout=600, full_output=True)
        # action status=completed on success
        if (result['status'] != "completed"):
            self.fail('HDFS smoke-test did not complete: %s' % result)

    def test_yarn(self):
        """
        Validates YARN using the Bigtop 'yarn' smoke test.
        """
        uuid = self.yarn.run_action('smoke-test')
        # 'yarn' smoke takes a while (bigtop tests download lots of stuff)
        result = self.d.action_fetch(uuid, timeout=1800, full_output=True)
        # action status=completed on success
        if (result['status'] != "completed"):
            self.fail('YARN smoke-test did not complete: %s' % result)

    def test_ingest(self):
        self.zeppelin.ssh('logger FLUME INGESTION TEST')  # create a log entry
        for i in amulet.helpers.timeout_gen(60):  # wait 60s for the entry to be ingested
            output, retcode = self.zeppelin.run("su hdfs -c '"
                                                "hdfs dfs -ls /user/flume/flume-syslog/*/*.txt'")
            if retcode == 0 and 'FlumeData' in output:
                break

        ingest_count = textwrap.dedent("""
            from pyspark import SparkContext
            sc = SparkContext(appName="ingest-count")
            count = sc.textFile("/user/flume/flume-syslog/*/*.txt").filter(lambda line: "INGESTION" in line).count()
            print("INGESTION Count: {}".format(count))
        """)
        output, retcode = self.zeppelin.run("cat << EOP > /home/ubuntu/ingest-count.py\n{}\nEOP".format(ingest_count))
        assert retcode == 0
        output, retcode = self.zeppelin.run("su ubuntu -c '"
                                            "PYSPARK_PYTHON=/usr/bin/python3 "
                                            "SPARK_HOME=/usr/lib/spark "
                                            "spark-submit --master yarn-client "
                                            "/home/ubuntu/ingest-count.py'")
        assert re.search(r'INGESTION Count: [1-9][0-9]*', output), 'ingest-count.py failed: %s' % output

    @unittest.skip(
        'Skipping zeppelin tests; current notebook has known failures.')
    def test_zeppelin(self):
        notebook_id = 'flume-tutorial'
        zep_addr = self.zeppelin.info['public-address']
        base_url = 'http://{}:9090/api/notebook/'.format(zep_addr)
        interp_url = urljoin(base_url, 'interpreter/bind/%s' % notebook_id)
        job_url = urljoin(base_url, 'job/%s' % notebook_id)
        para_url = urljoin(base_url, '%s/paragraph/' % notebook_id)

        # bind interpreters
        interpreters = requests.get(interp_url, timeout=60).json()
        interp_ids = list(map(itemgetter('id'), interpreters['body']))
        requests.put(interp_url, data=json.dumps(interp_ids), timeout=60)

        # run notebook
        requests.post(job_url, timeout=60)
        for i in amulet.helpers.timeout_gen(60 * 5):
            sleep(10)  # sleep first to give the job some time to run
            try:
                response = requests.get(job_url, timeout=60)
            except requests.exceptions.Timeout:
                # sometimes a long-running paragraph will cause the notebook
                # job endpoint to timeout, but it may eventually recover
                continue
            if response.status_code == 500:
                # sometimes a long-running paragraph will cause the notebook
                # job endpoint to return 500, but it may eventually recover
                continue
            statuses = list(map(itemgetter('status'), response.json()['body']))
            in_progress = {'PENDING', 'RUNNING'} & set(statuses)
            if not in_progress:
                break

        # check for errors
        errors = []
        for result in response.json()['body']:
            if result['status'] == 'ERROR':
                para_id = result['id']
                resp = requests.get(urljoin(para_url, para_id), timeout=60)
                para = resp.json()['body']
                errors.append(para['errorMessage'].splitlines()[0])
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
