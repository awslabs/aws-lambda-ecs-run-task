#!/usr/bin/env bash

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

OUTPUT_FILE="logs/lint-output.txt"
mkdir "logs"
echo "Output File: "${OUTPUT_FILE}""
echo -n "" > "${OUTPUT_FILE}"

echo "#---------------------------------------------------#" | tee -a "${OUTPUT_FILE}"
echo "#               Linting Python Files                 " | tee -a "${OUTPUT_FILE}"
echo "#---------------------------------------------------#" | tee -a "${OUTPUT_FILE}"
find "." -name "*.py" | \
  grep -Ev ".venv|.pytest_cach|.tox|botocore|boto3|.aws" | \
  xargs pylint --rcfile .pylintrc | tee -a "${OUTPUT_FILE}"


echo "#---------------------------------------------------#" | tee -a "${OUTPUT_FILE}"
echo "#               Linting Cfn Files                    " | tee -a "${OUTPUT_FILE}"
echo "#---------------------------------------------------#" | tee -a "${OUTPUT_FILE}"
# https://github.com/aws-cloudformation/cfn-python-lint/issues/1265
IGNORED_FILES=(
  './iac/CloudFormation/CodePipeline.yaml'
)

ALL_CFN_TEMPLATES=$(grep -r '^AWSTemplateFormatVersion' . | cut -d: -f1)

for TEMPLATE in ${ALL_CFN_TEMPLATES}; do
    if [[ "${TEMPLATE}" == "${IGNORED_FILES[0]}" ]] || [[ "${TEMPLATE}" == "${IGNORED_FILES[1]}" ]]; then
        echo "Template Ignored: $TEMPLATE" | tee -a "${OUTPUT_FILE}"
        continue
    fi
    echo "Linting CloudFormation Template - ${TEMPLATE}" | tee -a "${OUTPUT_FILE}"
    rm -f /tmp/cfn-lint-output.txt
    cfn-lint -t "${TEMPLATE}" | tee -a "${OUTPUT_FILE}"
done