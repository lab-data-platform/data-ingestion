#!/usr/bin/env bash
# Prepara o moto com o que, na conta real, vem do data-lakehouse: o bucket do bronze.
set -euo pipefail
export AWS_ENDPOINT_URL=http://localhost:5100 AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-2
unset AWS_PROFILE
aws s3api create-bucket --bucket lab-data-dev-bronze-123456789012 \
  --create-bucket-configuration LocationConstraint=us-east-2 >/dev/null
echo "moto pronto: bucket do bronze criado."
