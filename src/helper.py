# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import time
import re
import os
import json
from functools import wraps
from random import randint
import boto3

logging.basicConfig()
logger = logging.getLogger()
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(logging.INFO)


def send_failure_email(error_message, add_message=None):
    """This will send and email to an SNS topic about a Lambda Function Failure

    Args:
        error_message (str): Error message the was produced by the Lambda Function
        add_message (str) [optional]: Any additional data that would be added to the Email

    Returns:
        N/A
    """
    logger.info("Sending error message to SNS Topic")
    message = f'''\
                Hello,

                Your Function failed with the following message.

                Error Message: {error_message}

                Additional Data: {add_message} 

                To help further debug your issue...
                AWS_LAMBDA_LOG_GROUP_NAME: {os.environ['AWS_LAMBDA_LOG_GROUP_NAME']}
                AWS_LAMBDA_LOG_STREAM_NAME: {os.environ['AWS_LAMBDA_LOG_STREAM_NAME']}

                Sincerely,
                Your friendly neighborhood cloud architect :)

                '''

    client = boto3.client('sns')
    try:
        response = client.publish(
            TopicArn=os.environ['FAILURE_SNS_TOPIC_ARN'],
            Message=message,
            Subject=f"Execution of Lambda Function:{os.environ['AWS_LAMBDA_FUNCTION_NAME']} failed."
        )
        logger.info(response)

    except Exception as err:
        logger.error(err, exc_info=True)


def retry(max_attempts: int = 5, delay: int = 3, error_code=None, error_message=None):
    """Used as a decorator to retry any definition based on error code or error message, typically used due
       to lower then normal API limits.

    Args:
        max_attempts (int): Max number of retries
        delay (int): Duration to wait before another retry
        error_code (list) [optional]: Error code to search for in error
        error_message (str) [optional]: Error message to search for to retry

    Returns:
        :obj:`json`: Returns json object (dict) of the user parameters
    """

    if not error_code:
        error_code = ['TooManyRequestsException']

    def retry_decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            last_exception = "default exception"
            m_attempts = max_attempts  # create new memory allocation
            while m_attempts > 1:
                try:
                    logger.debug("**** [retry] args:%s", args)
                    logger.debug("**** [retry] kwargs:%s", kwargs)
                    return function(*args, **kwargs)

                except Exception as err:
                    if hasattr(err, 'response'):
                        logger.debug("**** [retry] ErrorCode:%s", err.response['Error']['Code'])

                    logger.warning(err)
                    if error_message and re.search(error_message, str(err)):
                        logger.warning(
                            "Definition failed:%s with (%s) message, trying again "
                            "in %s seconds...", function.__name__, error_message, delay
                        )
                        time.sleep(delay)
                        m_attempts -= 1
                        last_exception = err

                    elif hasattr(err, 'response'):
                        if err.response['Error']['Code'] in error_code:
                            logger.warning(
                                "Definition failed:%s with (%s) "
                                "error code, trying again in %s seconds...",
                                function.__name__, err.response['Error']['Code'], delay
                            )
                            time.sleep(delay)
                            m_attempts -= 1
                            last_exception = err

                    else:
                        logger.warning("Error wasn't found in retry raising error:%s", err)
                        raise err

            logger.error("Was not successfully able to complete the request after %s attempts", max_attempts)
            raise last_exception

        return wrapper

    return retry_decorator


def validate_ecs_run_task_info(ecs_info: dict):
    """Used to validate that SQS Message contains all necessary information to run the ECS Task

    Args:
        ecs_info (int): ECS Information

    Returns:
        :obj:`json`: Returns json object (dict) of the ECS information
    """
    logger.info("Validating SQS Message contains all the needed information to execution ECS Task")
    required_net_keys = {
        "subnets": ecs_info.get('networkConfiguration', {}).get('awsvpcConfiguration', {}).get('subnets'),
        "securityGroups": ecs_info.get('networkConfiguration', {}).get('awsvpcConfiguration', {}).get('securityGroups')
    }
    required_definition_keys = {
        "container_name": ecs_info.get('overrides', {}).get('containerOverrides', [{}])[0].get('name')
    }

    ecs = boto3.client('ecs')
    logger.info(f"ecs_info:{ecs_info}")

    if None in required_net_keys.values():
        logger.warning("***** REQUIRED NETWORK KEYS NOT PASSED TO RUN TASK *****")
        logger.warning(required_net_keys)

        if ecs_info.get('service') and ecs_info.get('cluster'):
            response = ecs.describe_services(
                cluster=ecs_info['cluster'],
                services=[ecs_info['service']]
            )

            logger.debug(response)
            if not required_net_keys['subnets'] and not required_net_keys['securityGroups']:
                logger.info(f"Updating Networking Configuration:{response['services'][0]['networkConfiguration']}")
                ecs_info['networkConfiguration'] = response['services'][0]['networkConfiguration']

            else:
                if not required_net_keys['subnets']:
                    subnets = response['services'][0]['networkConfiguration']['awsvpcConfiguration']['subnets']
                    logger.info(f"Updating Networking Subnet Configuration:{subnets}")
                    ecs_info['networkConfiguration'] = {"awsvpcConfiguration": {"subnets": subnets}}

                if not required_net_keys['securityGroups']:
                    security_groups = response['services'][0]['networkConfiguration']['awsvpcConfiguration']['securityGroups']
                    logger.info(f"Updating Networking securityGroups Configuration:{security_groups}")
                    ecs_info['networkConfiguration'] = {"awsvpcConfiguration": {"securityGroups": security_groups}}

        else:
            raise Exception(
                "ECS Service and/or Cluster Names did not get passed into ECS Information for "
                "validate_ecs_run_task_info"
            )

    if None in required_definition_keys.values():
        logger.warning("***** REQUIRED DEFINITION KEYS NOT PASSED TO RUN TASK *****")
        logger.warning(required_definition_keys)

        response = ecs.describe_task_definition(
            taskDefinition=ecs_info['taskDefinition']
        )
        logger.debug(response)

        if "overrides" not in ecs_info:
            ecs_info['overrides'] = {}

        if "containerOverrides" not in ecs_info['overrides']:
            ecs_info['overrides']['containerOverrides'] = [{}]

        container_name = response['taskDefinition']['containerDefinitions'][0]['name']
        ecs_info['overrides']['containerOverrides'][0]['name'] = container_name

    # Cleanup of ecs run task dictionary
    logger.info("Removing Service from ecs_info dict")
    del ecs_info['service']
    logger.info(f"ecs_parameters:{ecs_info}")

    return ecs_info


# Max 14 min retry window b/c of Lambdas timeout window
@retry(
    max_attempts=44,
    delay=randint(15, 20),
    error_code=["ThrottlingException", "ServerException", "RequestLimitExceeded"],  # InvalidParameterException
    error_message="You've reached the limit on the number of tasks you can run concurrently"
)
def ecs_run_task(**ecs_parameters):
    """Runs an ECS Task

    Args:
        ecs_parameters (dict): Data pass through from SQS to ECS run task

    Returns:
        N/A
    """
    logger.info("Attempting to start ECS Task")
    ecs = boto3.client('ecs')

    response = ecs.run_task(**ecs_parameters)
    logger.info(response)

    # If received a failure within the response raise error
    if len(response['failures']) > 0:
        raise Exception(response['failures'][0]['reason'])

    logger.info("Successfully started container using command:%s", ecs_parameters)


def send_message_to_queue(message_body):
    """Sends message to SQS Queue if a time out or limit has occurred to allow for more time for cool down if a
       large number of tasks are being executed in parallel.

    Args:
        message_body (str): ECS Cluster Name

    Returns:
        N/A
    """
    logger.info("Pushing message:%s back on the queue.", message_body)
    sqs = boto3.client('sqs')
    response = sqs.send_message(
        QueueUrl=os.environ['QUEUE_URL'],
        MessageBody=json.dumps(message_body)
    )
    logger.info(response)
