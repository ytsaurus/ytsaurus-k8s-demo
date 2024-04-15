#! /bin/bash

kubectl create configmap -n arivkin control-api-config --from-file=api.yaml=./api.yaml
