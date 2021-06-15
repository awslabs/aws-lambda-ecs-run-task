#!/usr/bin/env bash

set -e

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

echo "#--------------------------------------------------------#"
echo "#          Building SAM Packages for ${BASE}              "
echo "#--------------------------------------------------------#"

region=$(aws configure get region) || region="us-east-1"
BUCKET=$(aws s3 ls |awk '{print $3}' |grep -E "^sam-[0-9]{12}-${region}" )

KMS=$(aws s3api get-bucket-encryption \
  --bucket "${BUCKET}" \
  --region "${region}" \
  --query 'ServerSideEncryptionConfiguration.Rules[*].ApplyServerSideEncryptionByDefault.KMSMasterKeyID' \
  --output text
  )

echo "Deploying Serverless Application Function"

sam build -t cloudformation/function.yaml --use-container --region "${region}"

sam package \
  --template-file .aws-sam/build/template.yaml \
  --s3-bucket "${BUCKET}" \
  --s3-prefix "SAM" \
  --kms-key-id "${KMS}" \
  --region "${region}" \
  --output-template-file cloudformation/generated-sam-template.yaml

sam deploy \
  --stack-name LambdaEcsRunTask \
  --template-file cloudformation/generated-sam-template.yaml \
  --capabilities CAPABILITY_NAMED_IAM
