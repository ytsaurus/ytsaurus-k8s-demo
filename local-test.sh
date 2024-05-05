kubectl delete namespace testing || true
kubectl create namespace testing
kubectl delete crd chyts.cluster.ytsaurus.tech ytsaurus.cluster.ytsaurus.tech spyts.cluster.ytsaurus.tech remoteexecnodes.cluster.ytsaurus.tech remoteytsaurus.cluster.ytsaurus.tech || true

export HELM_EXPERIMENTAL_OCI=1
export YC_DEMO_REGISTRY_ID=crptkkbc0947ickrtnp7
export HELM_CHART_VERSION=0.0.278-dev-f80709464c1f4031df1346b7f81a2179dec7a547-ui-fix

if [ -z "${YC_TOKEN}" ]; then
  YC_TOKEN=$(yc iam create-token)
fi
echo $YC_TOKEN | helm registry login cr.yandex -u iam --password-stdin
echo $YC_TOKEN | docker login --username iam --password-stdin cr.yandex

kubectl create -n testing secret generic regcred --from-file=.dockerconfigjson=$HOME/.docker/config.json --type=kubernetes.io/dockerconfigjson
kubectl patch -n testing serviceaccount default -p '{"imagePullSecrets": [{"name": "regcred"}]}'

helm install -n testing ytsaurus oci://registry-1.docker.io/ytsaurus/ytop-chart --version 0.8.0
#helm install -n testing ytsaurus oci://cr.yandex/$YC_DEMO_REGISTRY_ID/ytsaurus/helm/ytop-chart --version $HELM_CHART_VERSION --set serviceAccountName=default

echo '
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: all-permissions
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
' | kubectl apply --filename=-

echo '
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: service-account-all-permissions
subjects:
- kind: ServiceAccount
  name: default
  namespace: testing
roleRef:
  kind: ClusterRole
  name: all-permissions
  apiGroup: rbac.authorization.k8s.io
' | kubectl apply --filename=-
echo "IAM_TOKEN=$(kubectl create token default -n testing --duration 6000s)" > /tmp/os-demo-env.txt
echo "NAMESPACE_NAME=testing" >> /tmp/os-demo-env.txt
export CONTOUR=testing
export K8S_HOST=$(kubectl config view --raw -o json | jq -r '.clusters[0].cluster.server')
kubectl -n testing wait --for condition=established --timeout=120s crd/chyts.cluster.ytsaurus.tech crd/ytsaurus.cluster.ytsaurus.tech crd/spyts.cluster.ytsaurus.tech crd/remoteexecnodes.cluster.ytsaurus.tech crd/remoteytsaurus.cluster.ytsaurus.tech
kubectl -n testing wait --for=jsonpath='{.spec.ports[0].port}'=443 --timeout=100s service/ytsaurus-ytop-chart-webhook-service

cat /home/$USER/.minikube/ca.crt > /tmp/os-demo-certificate_authority
export PYTHONPATH=$PYTHONPATH:$(pwd)

sleep 100
kubectl get pods -n testing
kubectl get services --all-namespaces

pytest -rA  --log-cli-level=INFO --log-level=INFO tests/*
