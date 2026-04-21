# Kubernetes Manifests（06~09）

## 目錄
- `base/namespace.yaml`
- `base/configmap.yaml`
- `base/secret.template.yaml`
- `base/pvc.yaml`
- `base/deployment.yaml`
- `base/service.yaml`
- `base/kustomization.yaml`

## 套用方式
1. 先建立 secret：
   - 複製 `base/secret.template.yaml` 成 `base/secret.yaml`
   - 填入真實金鑰
2. 將 `base/secret.yaml` 加入 `base/kustomization.yaml` 的 `resources`
3. 套用 manifests：
   - `kubectl apply -k k8s/base`

## 驗證
- `kubectl get ns rag-mvp`
- `kubectl get all -n rag-mvp`
- `kubectl get pvc -n rag-mvp`
- `kubectl describe pod -n rag-mvp <pod-name>`
