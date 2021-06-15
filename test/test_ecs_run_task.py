# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
import json
from src.helper import validate_ecs_run_task_info

# -------------------
# FAILING TEMPLATES
# -------------------
# Minimum Requirements
f = open("test/sqs_messages/test_minimum_requirements.json", "r")
test_minimum_requirements = json.loads(f.read())

# Network Override
f = open("test/sqs_messages/test_network_override.json", "r")
test_network_override = json.loads(f.read())

# No Container Name
f = open("test/sqs_messages/test_no_container_name.json", "r")
test_no_container_name = json.loads(f.read())

# No Network
f = open("test/sqs_messages/test_no_network.json", "r")
test_no_network = json.loads(f.read())

# No Security Group
f = open("test/sqs_messages/test_no_security_group.json", "r")
test_no_security_group = json.loads(f.read())

f.close()


class TestStringMethods(unittest.TestCase):

    # Pass
    def test_minimum_requirements(self):
        self.assertTrue(validate_ecs_run_task_info(ecs_info=test_minimum_requirements))

    def test_network_override(self):
        self.assertTrue(validate_ecs_run_task_info(ecs_info=test_network_override))

    def test_no_container_name(self):
        self.assertTrue(validate_ecs_run_task_info(ecs_info=test_no_container_name))

    def test_no_network(self):
        self.assertTrue(validate_ecs_run_task_info(ecs_info=test_no_network))

    def test_no_security_group(self):
        self.assertTrue(validate_ecs_run_task_info(ecs_info=test_no_security_group))


if __name__ == '__main__':
    unittest.main()
