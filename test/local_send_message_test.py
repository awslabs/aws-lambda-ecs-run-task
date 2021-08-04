# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import json
import time
import yaml
import boto3

logging.basicConfig()
logger = logging.getLogger()
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(logging.INFO)

NUMBER_OF_MESSAGES = 1


def run_spinup_test(cluster, family):
    _max_concurrency = 0
    concurrency = 1     # priming the data

    # Watch the tasks run
    ecs = boto3.client('ecs')
    _response = ['priming_data']
    while concurrency != 0:
        concurrency = 0
        paginator = ecs.get_paginator("list_tasks")
        for page in paginator.paginate(
            cluster=cluster,
            family=family
        ):
            concurrency = concurrency + len(page['taskArns'])

        logger.debug(_response)
        print("*******************************************")
        print(f"*       {concurrency} Containers Left")
        print("*******************************************")
        if concurrency > _max_concurrency:
            _max_concurrency = concurrency

        time.sleep(5)

    return _max_concurrency


if __name__ == "__main__":
    COUNT = 0
    sqs = boto3.client('sqs')
    sts = boto3.client('sts')

    # Needed for SQS
    account_id = sts.get_caller_identity()["Account"]

    configFilePath = "test/local_send_message_test.yaml"
    with open(configFilePath, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    # Build message body
    message_body = dict()
    queue_url = f"https://sqs.{config['region']}.amazonaws.com/{account_id}/{config['queue_name']}"

    # Create messages
    while COUNT < NUMBER_OF_MESSAGES:
        environment = [
            {"name": "plate_barcode", "value": "12345"},
            {"name": "s3_image_id", "value": f"{str(COUNT).zfill(5)}.tiff"},
            {"name": "s3_bucket", "value": f"testapp22-{account_id}-us-east-1"},
            {"name": "sleep_time", "value": "10"}
        ]
        command = ['sh', '-c', 'sleep 120 && df -h']
        message_body['ECS'] = {
            # REQUIRED
            "cluster": config['cluster'],
            "taskDefinition": config['task_definition'],
            "service": config['service'],
            "launchType": "FARGATE",
            # OPTIONAL
            "platformVersion": 'LATEST',
            "propagateTags": 'TASK_DEFINITION',
            "overrides": {
                "containerOverrides": [
                    {
                        "name": config['container_name'],
                        "command": command,
                        "environment":  environment
                    }
                ],
                "cpu": "1024",
                "memory": "2048"
            },
            # If you'd like to use something other than the default Cluster Subnet and Security Group
            #  uncomment this section out.
            # "networkConfiguration": {
            #    'awsvpcConfiguration': {
            #        'subnets': config['subnets'],
            #        'securityGroups': config['security_group'],
            #        'assignPublicIp': "ENABLED"
            #    }
            # },
            "referenceId": "add_reference_id_here",
        }

        logger.info('Count:%s', COUNT)
        logger.info('Sending message:%s to QueueUrl:%s', str(message_body), queue_url)
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        COUNT += 1
        time.sleep(5)

    time.sleep(10)
    max_concurrency = run_spinup_test(cluster=config['cluster'], family=config['family'])
    print("*******************************************")
    print(f"*    Total # of Messages: {NUMBER_OF_MESSAGES}")
    print(f"*    Max Concurrency: {max_concurrency}")
    print("*******************************************")
