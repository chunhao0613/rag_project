# Kubernetes

## 3W

### What

Kubernetes 是容器編排平台，負責宣告式部署、服務暴露、資源治理、自癒。

### Why

- 單純 `docker run` 難以管理多副本、滾動更新、故障自癒。
- 需要標準化部署物件（Deployment/Service/ConfigMap/Secret/PVC）。

### Where/How

- Where：測試叢集、正式叢集。
- How：用 YAML 宣告「期望狀態」，由控制器自動收斂。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| Namespace | 邏輯隔離 | 避免資源命名衝突 |
| Pod | 最小執行單位 | 一個或多個容器共享網路與儲存 |
| Deployment | 管理副本與更新 | 透過 ReplicaSet 控制 Pod |
| Service | 穩定入口 | 透過 selector 綁定 Pod |
| ConfigMap/Secret | 配置注入 | envFrom 給容器 |
| PVC | 持久資料 | volumeMount 到容器 |
| Probe | 健康檢查 | readiness/liveness |

### 協作關係

1. Deployment 建 Pod。
2. Pod 是 K8s 真正排程與運行的基本單位，裡面可以放一個主要容器，也可以放 sidecar。
3. Service 透過 selector 導流到 Pod。
4. ConfigMap/Secret 注入設定。
5. Probe 控制流量接入與重啟。
6. PVC 保存跨 Pod 生命週期資料。

---

## 手把手實作

## Deployment + Service 範例

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-app
  namespace: rag-mvp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rag-app
  template:
    metadata:
      labels:
        app: rag-app
    spec:
      containers:
        - name: rag-app
          image: rag_project-rag-app:latest
          ports:
            - containerPort: 8000
          readinessProbe:
            httpGet:
              path: /_stcore/health
              port: 8000
          livenessProbe:
            httpGet:
              path: /_stcore/health
              port: 8000
```

### 這段 Deployment 怎麼寫

- `apiVersion` / `kind`：先定義你要建立的 K8s 資源類型。
- `metadata.name`：資源名稱，之後 `kubectl` 會靠它查詢與更新。
- `namespace`：把資源放進特定環境隔離。
- `Pod`：Kubernetes 實際排程的最小單位。
  - 用途：真正跑容器的地方。
  - 何時要用：只要你在 K8s 上跑服務，就一定先經過 Pod。
  - 從零寫法：先想清楚一個 Pod 裡要放哪些容器，通常主容器加必要的 sidecar。
- `replicas`：副本數；開發通常 1，正式環境視需求提升。
- `selector.matchLabels`：Deployment 如何找到自己的 Pod。
- `template.metadata.labels`：Pod 需與 selector 對上。
- `containers`：容器定義。
  - `image`：要跑的 image。
  - `ports.containerPort`：容器內監聽 port。
  - `readinessProbe`：告訴 Service 什麼時候可以接流量。
  - `livenessProbe`：告訴 K8s 什麼時候該重啟容器。
- 從零寫法：先寫最小 Pod，再加 Deployment 管理副本，最後補 probe。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-app-svc
  namespace: rag-mvp
spec:
  selector:
    app: rag-app
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

### 這段 Service 怎麼寫

- `kind: Service`：建立穩定入口。
- `selector.app: rag-app`：把流量導到 label 符合的 Pod。
- `ports`：設定對外與容器內的轉發。
  - `port`：Service 自己暴露的埠。
  - `targetPort`：後端 Pod 真正聽的埠。
- `type: ClusterIP`：只在叢集內可見。
  - 何時要用：內部服務間互通時最常見。
- 從零寫法：先決定入口要不要對外，再決定是否需要 Ingress/LoadBalancer。

### Probe 的差異

- `readinessProbe`：判斷 Pod 能不能接流量。
  - 用途：避免還沒準備好的 Pod 被 Service 導流。
  - 何時要用：服務需要初始化、載入模型、連資料庫時。
- `livenessProbe`：判斷 Pod 是否已經掛死。
  - 用途：讓 K8s 自動重啟失去回應的容器。
  - 何時要用：服務可能進入死鎖、卡住、不再回應時。
- 從零寫法：先把 readiness 設保守一點，確定真的可服務後再開流量；liveness 則要避免太早判死，否則冷啟時會被重啟循環。

## 指令與參數

```bash
kubectl apply -f k8s/base/deployment.yaml
```

- `apply`：套用宣告狀態（可重複執行）。
- 何時用：第一次部署、更新 YAML、或做版本修正時。

```bash
kubectl get pods -n rag-mvp
```

- `-n`：指定 namespace。
- 何時用：你要確認 Pod 是否正在建立、重啟或失敗時。

```bash
kubectl describe pod <pod> -n rag-mvp
```

- 顯示 probe 狀態、事件、容器重啟資訊。
- 何時用：Pod 起不來、探針失敗、或要看排程事件時。

```bash
kubectl rollout status deployment/rag-app -n rag-mvp --timeout=180s
```

- 監看 rollout 是否完成。
- `--timeout` 避免無限等待。
- 何時用：你要確認部署是否完成，特別是 CI/CD 裡的 smoke gate。

---

## 常見錯誤與排查

1. Service 沒流量：selector label 不一致。
2. Pod 一直重啟：liveness 探針太早或路徑錯。
3. Pod Pending：PVC 綁定失敗或資源不足。

---

## 面試回答角度

- 為什麼要 probe：
  - readiness 保證只把流量送到可服務 Pod，liveness 保證掛死容器可自癒。

---

## 參考文件

- [Kubernetes 官方文件（中文）](https://kubernetes.io/zh-cn/docs/)
- [Kubernetes 官方文件：Workloads（英文）](https://kubernetes.io/docs/concepts/workloads/)
- [Kubernetes 官方文件：Services, Load Balancing, and Networking（英文）](https://kubernetes.io/docs/concepts/services-networking/)
