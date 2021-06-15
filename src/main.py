# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from random import randrange
from helper import ecs_run_task, send_failure_email, send_message_to_queue, validate_ecs_run_task_info

logging.basicConfig()
logger = logging.getLogger()
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(logging.INFO)

retry_error_codes = ["ThrottlingException", "ServerException", "RequestLimitExceeded", "InvalidParameterException"]
sqs_retry_limit = int(os.environ['SQS_RETRY_LIMIT'])


def lambda_handler(event, context):
    print(json.dumps(event))
    sqs_retries = 0  # Priming data

    # If event is from a CloudWatch Rule
    if event.get('detail'):
        subnets = []
        logger.info('****** Found Event *******')
        overrides = event['detail']['overrides']['containerOverrides'][0]
        container_info = event['detail']['containers'][0]
        attachment_details = event['detail']['attachments'][0]['details']

        logger.info("Gathering data from event")
        for att_detail in attachment_details:
            for value in att_detail.values():
                if "subnet-" in value:
                    subnets.append(value)

        logger.info("Building body dictionary")
        body = {
            'ECS': {
                "cluster": event['detail']['clusterArn'].split('/')[1],
                "subnets": subnets,
                "cpu": event['detail']['cpu'],
                "memory": event['detail']['memory'],
                "command": overrides['command'],
                "environment": overrides['environment'],
                "container_name": container_info['name'],
                "reference_id": f"{container_info['taskArn'].split('/')[1]}-{randrange(10)}",
                "task_def": event['detail']['taskDefinitionArn'].split('/')[1].split(':')[0],
                "startedBy": "CloudWatch Rules State Change to STOPPED",
                "security_groups": [os.environ['ECS_SECURITY_GROUP']]
            }
        }

        logger.info(f"body:{body}")

    # If event is from SQS
    elif event.get('Records'):
        record = event['Records'][0]
        body = json.loads(record['body'].replace("\'", "\""))
        body['ECS']['startedBy'] = record['eventSourceARN']

    try:
        # Add SQS retry to message body if not already there
        if not body.get('SQS_Retries'):
            logger.info("Setting up SQS Retry count")
            body['SQS_Retries'] = 0

        sqs_retries = body['SQS_Retries']

        ecs_info = validate_ecs_run_task_info(
            ecs_info=body['ECS']
        )

        ecs_run_task(**ecs_info)

    except KeyError as keyerr:
        logger.debug("***** KeyError ******")
        send_failure_email(error_message=keyerr, add_message=event)
        logger.error(keyerr, exc_info=True)

    except Exception as err:
        logger.debug("***** Exception ******")
        if hasattr(err, 'response'):
            if err.response['Error']['Code'] in retry_error_codes and \
                    sqs_retries < sqs_retry_limit:
                body['SQS_Retries'] += 1
                send_message_to_queue(message_body=body)
                return

        elif str(err) == "You've reached the limit on the number of tasks you can run concurrently" and \
                sqs_retries < sqs_retry_limit:
            body['SQS_Retries'] += 1
            send_message_to_queue(message_body=body)
            return

        send_failure_email(error_message=err, add_message=event)
        logger.error(err, exc_info=True)
