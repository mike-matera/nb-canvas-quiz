# Testing the Checker Server 

This directory has configuration to launch z2jh on Minikube. 

1. Start `minikube`:
    ```
    minikube start
    ```

1. Zip up a test bank:
    ```
    zip testbank.zip ../examples/testbanks/example.ipynb
    ```

1. Create a Kubernetes secret with the test bank:
    ```
    kubectl create secret generic testbank --from-file=testbank.zip
    ```

1. Install z2jh with `z2jh-values.yaml`
    ```
    helm repo add jupyterhub https://hub.jupyter.org/helm-chart/
    helm repo update
    helm install jhub jupyterhub/jupyterhub --values z2jh-values.yaml
    ```

1. Start a tunnel so you can access Jupyter Hub
    ```
    minikube tunnel  
    ```
