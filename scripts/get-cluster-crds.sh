#!/bin/bash

mkdir ./crds
mkdir ./crds/tmp

# for crd in $(kubectl get crds -o jsonpath='{.items[*].metadata.name}'); do \
#   kubectl get crd $crd -o yaml > ./crds/tmp/$crd.yaml; \
# done

# Map of patterns to target directories
# Move files with cnrm.cloud.google.com in the name to the kcc folder
echo "Moving files to their respective directories..."
for file in ./crds/tmp/*.yaml; do
  if [[ $file == *"cnrm.cloud.google.com"* ]]; then
    mkdir ./crds/kcc/
    mv $file ./crds/kcc/
  elif [[ $file == *"argoproj.io"* ]]; then
    mkdir ./crds/argocd/
    mv $file ./crds/argocd/
  elif [[ $file == *"gke.io"* ]]; then
    mkdir ./crds/gke/
    mv $file ./crds/gke/
  elif [[ $file == *"datadoghq.com"* ]]; then
    mkdir ./crds/datadog/
    mv $file ./crds/datadog/
  elif [[ $file == *"external-secrets.io"* ]]; then
    mkdir ./crds/external-secrets/
    mv $file ./crds/external-secrets/
  elif [[ $file == *"cert-manager.io"* ]]; then
    mkdir ./crds/cert-manager/
    mv $file ./crds/cert-manager/
  elif [[ $file == *"googleapis.com"* ]]; then
    mkdir ./crds/google-apis/
    mv $file ./crds/google-apis/
  elif [[ $file == *"cilium.io"* ]]; then
    mkdir ./crds/cilium/
    mv $file ./crds/cilium/
  elif [[ $file == *"cloud.google.com"* ]]; then
    mkdir ./crds/google/
    mv $file ./crds/google/
  fi
done

echo "CRDs extraction and organization complete."
