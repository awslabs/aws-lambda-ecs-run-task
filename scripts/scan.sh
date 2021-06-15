#!/usr/bin/env bash

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

OUTPUT_FILE="logs/scan-output.txt"
echo -n "" > "${OUTPUT_FILE}"

echo "#-----------------------------------------------#" | tee -a "${OUTPUT_FILE}"
echo "#   Scanning Python code for Vulnerabilities     " | tee -a "${OUTPUT_FILE}"
echo "#-----------------------------------------------#" | tee -a "${OUTPUT_FILE}"
echo "Output File: "${OUTPUT_FILE}""
bandit --recursive ../src | tee -a "${OUTPUT_FILE}"

echo "#-----------------------------------------------#" | tee -a "${OUTPUT_FILE}"
echo "#   Scanning Python depend for Vulnerabilities   " | tee -a "${OUTPUT_FILE}"
echo "#-----------------------------------------------#" | tee -a "${OUTPUT_FILE}"
safety check | tee -a "${OUTPUT_FILE}"