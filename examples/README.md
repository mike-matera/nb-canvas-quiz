# Testing the Checker Server 

This directory has configuration to launch z2jh on Minikube. The configuration
in `z2jh-values.yaml` uses the example test bank in this directory. 

1. Generate the Canvas export and corresponding test notebook. The test notebook
  is also embedded in the quiz export.
  ```
  uv run nbquiz export assessment.yaml
  ```

1. Start `minikube`:
    ```
    minikube start
    ```

1. Enable sharing of the `examples` directory with containers (this must stay 
  running):
    ```
    minikube mount $(pwd):/testbanks &
    ```

1. Install z2jh with `z2jh-values.yaml`
    ```
    helm repo add jupyterhub https://hub.jupyter.org/helm-chart/
    helm repo update
    helm install jhub jupyterhub/jupyterhub --values z2jh-values.yaml
    ```

1. Start a tunnel so you can access Jupyter Hub. This must stay running and 
  requires `sudo`:
    ```
    minikube tunnel
    ```
