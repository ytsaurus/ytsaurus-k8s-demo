== How to bootstrap demo cluster

1. create namespace 

kubectl apply -f namespace.yaml

2. generate password and create admin credentials

kubectl create secret generic ytadminsec --from-literal=login=admin --from-literal=password=123456789 --from-literal=token=123456789  -n <namespace> 

3. create YT cluster

kubectl apply -f ytsaurus.yaml -n <namespace> 

4. create HTTP route for YT UI

kubectl apply -f ui-route.yaml -n <namespace>


5. modify env in jupyter deployment. create jupyter statefulset, headless-service, service and http route

kubectl apply -f jupyter-statefulset.yaml -n <namespace> 
kubectl apply -f jupyter-headless.yaml -n <namespace> 
kubectl apply -f jupyter-service.yaml -n <namespace> 
kubectl apply -f jupyter-route.yaml -n <namespace> 

6. fix env and run a job to upload demo data

kubectl apply -f demo-data-job.yaml -n <namespace> 

7. to clean up, just delete the namespace

kubectl delete namespace <namespace>

