# Testing the Checker Server 

This directory has configuration to launch z2jh on Minikube. The configuration in `z2jh-values.yaml` is
configured to use the example test banks on GitHub. 

1. Start `minikube`:
    ```
    minikube start
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

## Setup in Jupyter 

The Helm chart uses a default Jupyter image that doesn't have `nbquiz` installed. Before
you can run a test notebook use the shell to execute: 

```
pip install git+https://github.com/mike-matera/nbquiz.git
```

Once `nbquiz` is installed you can drag-and-drop an exam notebook into Jupyter and execute
it. 

## Use Local Testbanks 

You can update the system to use your own test banks that are loaded into 
Kubernetes using a Secret resource.

1. First update the `singleuser` configuration to mount a secret:
    ```yaml
    singleuser:
      extraContainers:
        - "name": "nbquiz-server"
          "image": "ghcr.io/mike-matera/nbquiz:main"
          "env":
            - "name": "NBQUIZ_TESTBANKS"
              "value": "/testbank/testbank.zip"
          volumeMounts:
          - name: testbank
            mountPath: "/testbank"
            readOnly: true
      storage:
        extraVolumes:
        - name: testbank
          secret:
            secretName: testbank
            optional: true
    ```

1. Zip up a test bank:
    ```
    zip testbank.zip /path/to/your/testbanks/*.ipynb
    ```

1. Create a Kubernetes secret with the test bank:
    ```
    kubectl create secret generic testbank --from-file=testbank.zip
    ```

1. Upgrade z2jh to use your test banks: 
    ```
    helm upgrade jhub jupyterhub/jupyterhub --values z2jh-values.yaml
    ```

## Setup in Jupyter 

The Helm chart uses a default Jupyter image that doesn't have `nbquiz` installed. Before
you can run a test notebook use the shell to execute: 

```
pip install git+https://github.com/mike-matera/nbquiz.git
```
