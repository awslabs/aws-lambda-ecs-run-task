#!/usr/bin/env bash

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

set -eo pipefail

echo "#---------------------------------------------------#"
echo "#                  Running Tests                     "
echo "#---------------------------------------------------#"

for test in $(find . -name tox.ini); do
  #pyenv local 3.6.9 3.7.4 3.8.1 # Can do multiple versions like this but need to make sure they are installed
#  pyenv local 3.7.4
  tox -c "${test}"
done