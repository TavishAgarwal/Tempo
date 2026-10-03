#!/usr/bin/env bash
# Deploy Tempo to Azure Container Apps (single container, UI + API).
# Prereqs: `brew install azure-cli` and `az login`.
set -euo pipefail
cd "$(dirname "$0")/.."

RG=${RG:-tempo-rg}
LOC=${LOC:-centralindia}
ACR=${ACR:-tempo$RANDOM$RANDOM}     # globally unique, lowercase alnum
ENVN=${ENVN:-tempo-env}
APP=${APP:-tempo}
MIN=${MIN:-0}                        # 0 = scale to zero (cheapest, ~30 s cold start); 1 = always warm

az extension add --name containerapp --upgrade -y
az provider register -n Microsoft.ContainerRegistry --wait
az provider register -n Microsoft.App --wait
az provider register -n Microsoft.OperationalInsights --wait
az group create -n "$RG" -l "$LOC" -o none
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true -o none
# Build locally for amd64 and push (ACR Tasks / `az acr build` is blocked on Azure for Students)
az acr login -n "$ACR"
docker buildx build --platform linux/amd64 -f Dockerfile.azure -t "$ACR.azurecr.io/tempo:latest" --push .
az containerapp env create -n "$ENVN" -g "$RG" -l "$LOC" -o none
# Single replica only: jobs and websocket streams live in process memory.
az containerapp create -n "$APP" -g "$RG" --environment "$ENVN" \
  --image "$ACR.azurecr.io/tempo:latest" \
  --registry-server "$ACR.azurecr.io" \
  --registry-username "$(az acr credential show -n "$ACR" --query username -o tsv)" \
  --registry-password "$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)" \
  --target-port 8000 --ingress external \
  --cpu 1.0 --memory 2.0Gi --min-replicas "$MIN" --max-replicas 1 -o none
echo "URL: https://$(az containerapp show -n "$APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)"
