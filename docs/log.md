# Docker → YAML → Helm 實作日誌筆記（0 基礎版）

> 這份文件是「實作日誌筆記」，不是指令備忘錄。它記錄每一階段的 **參考檔案、存在意義、做了什麼、關鍵名詞、程式片段、怎麼改、怎麼驗證**。  
> 目標是讓你可以從 0 開始，照著做出一條完整的自動化鏈，而且知道每一步為什麼要這樣寫。

---

## 0. 先看全域地圖

### 0-1. 交付鏈路

1. Dockerfile：把應用打包成可重現的 image。
2. docker-compose：把本機啟動、健康檢查、資料掛載標準化。
3. tests / Makefile：建立品質閘道。
4. Kubernetes YAML：把部署目標狀態宣告化。
5. Minikube：在本機真的跑 Kubernetes。
6. YAML rollback drill：先證明能回復，再談上線。
7. Helm：把 YAML 模板化、參數化、版本化。
8. GitLab CI / Jenkins：把治理與交付串起來。
9. Prometheus / ELK / Alertmanager：把健康、日誌、告警串起來。

### 0-2. 這份筆記怎麼用

每一階段都固定看這六件事：

- 參考檔案
- 這階段存在意義
- 這階段做了什麼
- 關鍵概念與專有名詞
- 程式片段與解說
- 怎麼改、怎麼驗證

### 0-3. 開始前先確認工具

```bash
docker --version
kubectl version --client
minikube version
helm version
```

你要先確認：

- Docker 能 build image。
- kubectl 能和 K8s 對話。
- minikube 能起本機叢集。
- helm 能安裝與渲染 chart。

---

## 03（4~6h）：容器化基線

### 參考檔案

- [Dockerfile](../Dockerfile)
- [.dockerignore](../.dockerignore)
- [startup.sh](../startup.sh)

### 這階段存在意義

把「在我電腦可跑」變成「在任何地方都可重現」。後面的 Compose、K8s、Helm、CI/CD 都是以這個 image 為基礎。

### 這階段做了什麼

- 選 `python:3.11-slim` 作為基底 image。
- 安裝 `curl` 供健康檢查，安裝 `make` 供後續品質命令。
- 先複製 `requirements.txt` 再安裝依賴，讓 layer cache 更有效。
- 加上 `HEALTHCHECK`，讓 Docker 知道容器是否可用。

### 關鍵名詞

- **Image**：不可變交付物。
- **Layer cache**：未變的建置層可重用。
- **Build context**：送進 docker build 的檔案集合。
- **HEALTHCHECK**：容器層健康訊號。

### 程式片段與解說

```dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl make \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/_stcore/health || exit 1

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port", "8000", "--server.address", "0.0.0.0"]
```

逐段解說：

- `FROM`：選 runtime 與系統層。`slim` 比完整版小，但工具少，所以後面常要自己補。
- `WORKDIR`：之後所有相對路徑都以 `/app` 為準。
- `RUN apt-get ...`：安裝系統工具。`--no-install-recommends` 是減肥手法。
- `COPY requirements.txt` + `RUN pip install ...`：先複製依賴檔，可以讓 image cache 更穩定。
- `COPY . ./`：把程式碼放進 image；哪些檔案不進 image，取決於 `.dockerignore`。
- `HEALTHCHECK`：Docker 週期性檢查服務。`curl -fsS` 失敗會回傳非 0。
- `CMD [...]`：容器預設啟動命令，這裡直接啟動 Streamlit。

### 怎麼改

- 如果你改服務 port，`HEALTHCHECK` 和 `CMD --server.port` 要一起改。
- 如果你要加 debug 工具，就在 `apt-get install` 裡補，但 image 會變大。
- 如果你要換啟動方式，可改 `CMD`，但要保證 app 仍聽在同一個 port。

### 怎麼驗證

```bash
docker build -t rag-app:local .
docker run --rm -p 8000:8000 rag-app:local
curl -I http://localhost:8000
```

你要看見：build 成功、容器啟動、HTTP 可連。

---

## 04（6~8h）：本機編排與健康檢查

### 參考檔案

- [docker-compose.yml](../docker-compose.yml)

### 這階段存在意義

Compose 讓你在本機把啟動、健康檢查、資料掛載變成單一指令流程。它不是 Kubernetes 的替代品，而是本機驗證工具。

### 這階段做了什麼

- 定義 `rag-app` 服務。
- 對外映射 `8000:8000`。
- 設定 healthcheck。
- 掛載 `./data:/app/data`。

### 關鍵名詞

- **Compose service**：一個可被編排的容器單位。
- **Port mapping**：主機 port 對到容器 port。
- **Bind mount**：把主機資料夾直接掛進容器。

### 程式片段與解說

```yaml
services:
  rag-app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: rag_app
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - ./data:/app/data
    environment:
      - PYTHONUNBUFFERED=1
      - TZ=Asia/Taipei
```

逐段解說：

- `build.context`：build 根目錄。
- `build.dockerfile`：指定使用哪個 Dockerfile。
- `container_name`：固定容器名，排障比較方便。
- `ports`：把主機 8000 對到容器 8000。
- `healthcheck`：檢查 HTTP 回應是否正常。
- `volumes`：把資料留在主機，容器重建後還在。
- `PYTHONUNBUFFERED=1`：log 立即輸出。
- `TZ=Asia/Taipei`：時區一致，方便查 log。

### 怎麼改

- 改 port 時要連同 healthcheck 路徑一起看。
- 想加第二個服務，就在 `services` 下再加一個 block。
- 如果你不想用 bind mount，可改 named volume，但排障較不直觀。

### 怎麼驗證

```bash
docker compose up -d --build
docker compose ps
docker logs rag_app --tail 50
docker compose down && docker compose up -d
```

你要看見：`healthy`、可重啟、log 沒有連續報錯。

---

## 05（8~10h）：最小測試與品質入口

### 參考檔案

- [Makefile](../Makefile)
- [pyproject.toml](../pyproject.toml)
- [requirements.txt](../requirements.txt)
- [tests/conftest.py](../tests/conftest.py)
- [tests/test_document_processor.py](../tests/test_document_processor.py)
- [tests/test_vector_store.py](../tests/test_vector_store.py)
- [tests/test_llm_service.py](../tests/test_llm_service.py)

### 這階段存在意義

CI/CD 的第一道門不是部署，而是品質閘道。你要先把壞變更擋住，後面的 build、deploy 才不會一直被打斷。

### 這階段做了什麼

- 建立 `tests/` 骨架。
- 加上 `make lint`、`make test`、`make check`。
- 用 Ruff 先擋高風險問題。
- 用 `conftest.py` 解決 import 路徑問題。

### 關鍵名詞

- **Lint**：靜態檢查。
- **Unit test**：單元測試。
- **Quality gate**：不通過就不能往下走。
- **pytest**：Python 測試框架。
- **ruff**：Python 靜態檢查工具。

### 程式片段與解說

```makefile
lint:
	ruff check core services tests app.py

test:
	pytest

check: lint test
```

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E9", "F63", "F7", "F82"]
```

```python
# tests/conftest.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

逐段解說：

- `make lint`：跑 Ruff，先抓語法與致命錯誤。
- `make test`：跑 pytest。
- `make check`：把 lint 和 test 串成一條命令。
- `pytest.ini_options`：統一 pytest 的尋找規則。
- `ruff select`：先開高風險規則，避免一開始被格式規則拖慢。
- `conftest.py`：把專案 root 放進 `sys.path`，測試時才能直接 import `core`、`services`。

### 怎麼改

- 想加新功能，就對應補新的 test。
- 想更嚴格，可把 Ruff 規則擴大到格式與風格。
- 專案路徑改了，`conftest.py` 的 root 也要改。

### 怎麼驗證

```bash
docker compose run --rm --build rag-app make check
```

你要看到：Ruff 通過、pytest 通過、核心路徑可重現。

---

## 06（10~12h）：Kubernetes 配置基礎

### 參考檔案

- [k8s/base/namespace.yaml](../k8s/base/namespace.yaml)
- [k8s/base/configmap.yaml](../k8s/base/configmap.yaml)
- [k8s/base/secret.template.yaml](../k8s/base/secret.template.yaml)
- [k8s/base/kustomization.yaml](../k8s/base/kustomization.yaml)

### 這階段存在意義

把配置與程式碼分離，建立可治理、可切環境的部署基礎。

### 這階段做了什麼

- 建立 `rag-mvp` Namespace。
- 用 ConfigMap 管非敏感設定。
- 用 Secret template 管敏感資訊。
- 用 Kustomization 組裝 manifest。

### 關鍵名詞

- **Namespace**：資源隔離。
- **ConfigMap**：非敏感設定。
- **Secret**：敏感設定。
- **Kustomization**：YAML 組裝入口。

### 程式片段與解說

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rag-mvp
  labels:
    app.kubernetes.io/name: rag-project
    app.kubernetes.io/part-of: sre-mvp
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-app-config
  namespace: rag-mvp
data:
  STREAMLIT_SERVER_PORT: "8000"
  STREAMLIT_SERVER_ADDRESS: "0.0.0.0"
  GOOGLE_CHAT_MODEL: "gemini-2.0-flash-lite"
  GOOGLE_EMBEDDING_MODEL: "models/gemini-embedding-001"
```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-app-secrets
  namespace: rag-mvp
type: Opaque
stringData:
  GOOGLE_API_KEY: "<replace-google-api-key>"
```

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: rag-mvp
resources:
  - namespace.yaml
  - configmap.yaml
  - pvc.yaml
  - deployment.yaml
  - service.yaml
# secret.yaml 先補好再加入 resources
```

逐段解說：

- `Namespace`：先切隔離邊界，後面治理才清楚。
- `ConfigMap`：放公開配置，例如 port、模型名稱。
- `Secret`：放 API key，但這裡只放 template。
- `Kustomization`：把多份 YAML 組成一套可套用的 manifest。

### 怎麼改

- 新增設定鍵，就改 ConfigMap，應用程式讀取也要一起改。
- 真正部署前，`secret.template.yaml` 要複製成 `secret.yaml` 並填真值。
- 如果你想切環境，優先改配置，不要直接改程式碼。

### 怎麼驗證

```bash
kubectl apply --dry-run=client --validate=false -f k8s/base/namespace.yaml -o name
kubectl apply --dry-run=client --validate=false -f k8s/base/configmap.yaml -o name
kubectl apply --dry-run=client --validate=false -f k8s/base/secret.template.yaml -o name
```

---

## 07（12~14h）：Deployment 與 Service

### 參考檔案

- [k8s/base/deployment.yaml](../k8s/base/deployment.yaml)
- [k8s/base/service.yaml](../k8s/base/service.yaml)

### 這階段存在意義

把容器變成 Kubernetes 服務。Deployment 管副本與更新，Service 提供穩定入口。

### 這階段做了什麼

- 建 Deployment。
- 建 ClusterIP Service。
- 透過 `envFrom` 注入 ConfigMap / Secret。

### 關鍵名詞

- **Deployment**：工作負載控制器。
- **ReplicaSet**：維持副本數的底層控制器。
- **Service**：穩定存取入口。
- **Selector**：選出對應 Pod。

### 程式片段與解說

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
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8000
          envFrom:
            - configMapRef:
                name: rag-app-config
            - secretRef:
                name: rag-app-secrets
```

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
    - name: http
      port: 80
      targetPort: 8000
  type: ClusterIP
```

逐段解說：

- `replicas: 1`：MVP 先求穩定。
- `selector.matchLabels`：Deployment 要知道自己管哪些 Pod。
- `imagePullPolicy: IfNotPresent`：本機有 image 時優先用本機。
- `containerPort: 8000`：對齊 Streamlit 監聽 port。
- `envFrom`：一次掛入 ConfigMap 與 Secret。
- `Service.selector`：把流量導到標籤符合的 Pod。
- `port` / `targetPort`：Service 對外口與容器內口分開寫。

### 怎麼改

- 要擴容就改 `replicas`，但要先確認 PVC 策略是否允許多副本。
- 要換 image tag，就改 `image`。
- 要加配置，就改 ConfigMap 與應用程式讀取邏輯。

### 怎麼驗證

```bash
kubectl get pods -n rag-mvp
kubectl get svc -n rag-mvp
kubectl describe deployment rag-app -n rag-mvp
```

---

## 08（14~16h）：探針與資源治理

### 參考檔案

- [k8s/base/deployment.yaml](../k8s/base/deployment.yaml)

### 這階段存在意義

讓平台知道：什麼時候可以接流量，什麼時候要重啟，還有什麼資源上限不能突破。

### 這階段做了什麼

- 加 `readinessProbe`。
- 加 `livenessProbe`。
- 加 `resources.requests` 與 `resources.limits`。

### 關鍵名詞

- **Readiness probe**：是否可接流量。
- **Liveness probe**：是否需要重啟。
- **Requests**：排程保底。
- **Limits**：資源上限。

### 程式片段與解說

```yaml
readinessProbe:
  httpGet:
    path: /_stcore/health
    port: http
  initialDelaySeconds: 15
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /_stcore/health
    port: http
  initialDelaySeconds: 45
  periodSeconds: 20
  timeoutSeconds: 5
  failureThreshold: 3

resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: "1"
    memory: 1Gi
```

逐段解說：

- `readinessProbe`：失敗時 Pod 不接流量。
- `livenessProbe`：失敗時 kubelet 重啟容器。
- `initialDelaySeconds`：避免啟動初期誤判。
- `periodSeconds`：多久檢查一次。
- `timeoutSeconds`：單次檢查最多等多久。
- `failureThreshold`：連續失敗幾次才算失敗。
- `requests`：scheduler 至少要預留多少資源。
- `limits`：容器可以吃到的上限。

### 怎麼改

- 啟動慢就拉高 `initialDelaySeconds`。
- 偶爾抖動就拉高 `failureThreshold`。
- 真的吃不到資源就調整 `requests` / `limits`，但要看節點容量。

### 怎麼驗證

```bash
kubectl describe pod -n rag-mvp <pod-name>
kubectl get events -n rag-mvp
```

---

## 09（16~18h）：持久化策略

### 參考檔案

- [k8s/base/pvc.yaml](../k8s/base/pvc.yaml)
- [k8s/base/deployment.yaml](../k8s/base/deployment.yaml)

### 這階段存在意義

RAG 應用會產生向量資料、快取與上傳檔案。真正需要保留的資料要從 Pod 生命週期抽離出來，否則 Pod 一重建就不見了。

### 這階段做了什麼

- 建立 PVC。
- 把 `/app/data` 掛進 Pod。

### 關鍵名詞

- **PV/PVC**：儲存資源與申請契約。
- **ReadWriteOnce**：單節點讀寫。
- **StorageClass**：儲存供應策略。

### 程式片段與解說

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rag-data-pvc
  namespace: rag-mvp
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

```yaml
volumeMounts:
  - name: rag-data
    mountPath: /app/data
volumes:
  - name: rag-data
    persistentVolumeClaim:
      claimName: rag-data-pvc
```

逐段解說：

- `PersistentVolumeClaim`：應用向叢集申請儲存資源。
- `ReadWriteOnce`：一次只給一個節點掛載讀寫。
- `storage: 10Gi`：申請最少 10Gi。
- `mountPath`：容器內看到的資料路徑。
- `claimName`：Pod 要連接哪個 PVC。

### 怎麼改

- 如果資料要更多，就調大 `storage`。
- 如果你要多副本共用，要先確認 storage class 支援 RWX，不然會卡住。
- 如果你想把 cache 跟持久化資料分開，最好拆不同目錄或不同 volume。

### 怎麼驗證

```bash
kubectl get pvc -n rag-mvp
kubectl describe pvc rag-data-pvc -n rag-mvp
```

---

## 10（18~20h）：YAML 版回滾演練

### 參考檔案

- [k8s/base/deployment.yaml](../k8s/base/deployment.yaml)
- [k8s/base/service.yaml](../k8s/base/service.yaml)
- [k8s/README.md](../k8s/README.md)

### 這階段存在意義

SRE 不只是會上版本，還要會回版本。這一階段用故障注入證明：如果部署壞了，我可以快速回到穩定版，而且過程可追溯。

### 這階段做了什麼

- 在 minikube 上套用 base manifests。
- 載入本機 image。
- 故意切壞 image tag。
- 用 `rollout undo` 回到穩定版。

### 關鍵名詞

- **Minikube**：本機 Kubernetes 叢集。
- **Rollout**：Deployment 版本推進。
- **Undo**：回復上一個版本。
- **Change-cause**：變更原因。

### 指令片段與解說

```bash
minikube start --driver=docker
minikube image load rag_project-rag-app:latest

kubectl -n rag-mvp set image deployment/rag-app rag-app=rag_project-rag-app:does-not-exist
kubectl -n rag-mvp rollout status deployment/rag-app --timeout=90s

kubectl -n rag-mvp rollout undo deployment/rag-app
kubectl -n rag-mvp rollout status deployment/rag-app --timeout=180s
kubectl -n rag-mvp rollout history deployment/rag-app
```

逐段解說：

- `minikube start --driver=docker`：把本機變成可跑 K8s 的環境。
- `minikube image load ...`：把本機 image 載到 minikube 節點，避免拉 registry。
- `kubectl set image`：把 deployment 改成壞版本，這是故障注入。
- `kubectl rollout status`：等 rollout 結果，確認它真的失敗。
- `kubectl rollout undo`：回滾到上一個 revision。
- `kubectl rollout history`：確認 revision 歷史完整。

### 怎麼改

- 你可以換成其他壞 tag 來測不同故障情境。
- 你可以調 timeout 看恢復速度。
- 你也可以改成故意讓 probe 失敗，練習另一種回滾路徑。

### 怎麼驗證

```bash
kubectl -n rag-mvp get deploy,po,svc,pvc
kubectl -n rag-mvp get deploy rag-app -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl -n rag-mvp rollout history deployment/rag-app
```

---

## 11（20~22h）：Helm 初始化

### 參考檔案

- [helm/rag-app/Chart.yaml](../helm/rag-app/Chart.yaml)
- [helm/rag-app/values.yaml](../helm/rag-app/values.yaml)
- [helm/rag-app/templates/deployment.yaml](../helm/rag-app/templates/deployment.yaml)
- [helm/rag-app/templates/service.yaml](../helm/rag-app/templates/service.yaml)

### 這階段存在意義

Helm 是把 YAML 變成可模板化、可參數化、可版本化的管理單位。它不取代 YAML，而是幫你產生與管理 YAML。

### 這階段做了什麼

- `helm create` 初始化 chart。
- `helm lint` 驗證 chart 結構。
- `helm template` 渲染輸出 YAML。

### 關鍵名詞

- **Chart**：Helm 套件單位。
- **Values**：模板參數。
- **Template**：帶變數的 YAML。
- **Release**：安裝到叢集的實例。

### 程式片段與解說

```yaml
apiVersion: v2
name: rag-app
type: application
version: 0.1.0
appVersion: "1.0.0"
```

```yaml
image:
  repository: rag_project-rag-app
  pullPolicy: IfNotPresent
  tag: latest
```

逐段解說：

- `apiVersion: v2`：Helm 3+ chart 格式。
- `name`：chart 名稱，不是 release 名稱。
- `version`：chart 版本。
- `appVersion`：應用版本。
- `values.yaml`：所有可變參數的預設值。

### 怎麼改

- 改 chart 內容時，順手更新 `version`。
- 改 image 來源時，改 `repository/tag`。
- 如果你要多環境，就把差異放到獨立 values 檔。

### 怎麼驗證

```bash
helm lint helm/rag-app
helm template rag-app helm/rag-app | head -n 40
```

---

## 12（22~24h）：Helm 核心模板化

### 參考檔案

- [helm/rag-app/templates/deployment.yaml](../helm/rag-app/templates/deployment.yaml)
- [helm/rag-app/templates/service.yaml](../helm/rag-app/templates/service.yaml)
- [helm/rag-app/templates/configmap.yaml](../helm/rag-app/templates/configmap.yaml)
- [helm/rag-app/templates/secret.yaml](../helm/rag-app/templates/secret.yaml)
- [helm/rag-app/templates/pvc.yaml](../helm/rag-app/templates/pvc.yaml)
- [helm/rag-app/templates/_helpers.tpl](../helm/rag-app/templates/_helpers.tpl)

### 這階段存在意義

模板化的關鍵是：把固定結構和可變參數分開。固定結構放 templates，可變參數放 values。

### 這階段做了什麼

- 把 Deployment、Service、ConfigMap、Secret、PVC 模板化。
- 用 helper 統一命名。

### 關鍵名詞

- **Helper**：Helm 裡的共用模板函式。
- **Selector labels**：讓 Service 與 Deployment 對上。
- **Templating**：用變數生 YAML。

### 程式片段與解說

```yaml
{{- define "rag-app.configMapName" -}}
{{- printf "%s-config" (include "rag-app.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "rag-app.secretName" -}}
{{- printf "%s-secrets" (include "rag-app.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "rag-app.pvcName" -}}
{{- if .Values.persistence.existingClaim -}}
{{- .Values.persistence.existingClaim -}}
{{- else -}}
{{- printf "%s-data" (include "rag-app.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end }}
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "rag-app.configMapName" . }}
data:
  {{- range $k, $v := .Values.config }}
  {{ $k }}: {{ $v | quote }}
  {{- end }}
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "rag-app.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          envFrom:
            - configMapRef:
                name: {{ include "rag-app.configMapName" . }}
            {{- if .Values.secret.create }}
            - secretRef:
                name: {{ include "rag-app.secretName" . }}
            {{- end }}
```

逐段解說：

- `_helpers.tpl`：集中命名規則，避免不同資源名稱不一致。
- `range .Values.config`：把 values 裡的 config 轉成 ConfigMap 鍵值。
- `image.tag | default .Chart.AppVersion`：如果沒指定 tag，就用 appVersion。
- `envFrom`：把 ConfigMap 與 Secret 一次掛進容器。

### 怎麼改

- 如果你要改命名規則，只改 helper，不要每個 template 都改。
- 如果你要新增設定鍵，優先在 `values.yaml` 與 `configmap.yaml` 同步加。
- 如果你要關閉 Secret 建立，把 `.Values.secret.create` 設成 `false`。

### 怎麼驗證

```bash
helm lint helm/rag-app
helm template rag-app helm/rag-app > /tmp/rag-app.yaml
```

---

## 13（24~26h）：多環境 values

### 參考檔案

- [helm/rag-app/values-dev.yaml](../helm/rag-app/values-dev.yaml)
- [helm/rag-app/values-staging.yaml](../helm/rag-app/values-staging.yaml)
- [helm/rag-app/values-prod.yaml](../helm/rag-app/values-prod.yaml)

### 這階段存在意義

同一套模板，不同環境只改 values。這樣才能做到 dev / staging / prod 的差異化配置，而不是複製三份 YAML。

### 這階段做了什麼

- dev / staging / prod 各自有不同副本數、資源與 PVC size。
- 用 values 切模型與秘密預設值。

### 關鍵名詞

- **Values override**：用外部 values 覆蓋預設值。
- **Environment-specific config**：不同環境不同配置。

### 程式片段與解說

```yaml
# values-dev.yaml
replicaCount: 1
resources:
  requests:
    cpu: 200m
    memory: 384Mi
  limits:
    cpu: 500m
    memory: 768Mi
persistence:
  size: 5Gi
```

```yaml
# values-staging.yaml
replicaCount: 1
resources:
  requests:
    cpu: 300m
    memory: 512Mi
  limits:
    cpu: 800m
    memory: 1Gi
persistence:
  size: 10Gi
```

```yaml
# values-prod.yaml
replicaCount: 2
resources:
  requests:
    cpu: 500m
    memory: 768Mi
  limits:
    cpu: "1"
    memory: 1Gi
persistence:
  size: 20Gi
```

逐段解說：

- dev：先求快、求便宜。
- staging：接近正式環境，但規模較小。
- prod：更保守，副本和資源都較高。

### 怎麼改

- 你要新增環境，只要新增一份 values 檔。
- 不同環境差異應該放在 values，不要回去改模板。

### 怎麼驗證

```bash
helm template rag-app helm/rag-app -f helm/rag-app/values-dev.yaml > /tmp/dev.yaml
helm template rag-app helm/rag-app -f helm/rag-app/values-prod.yaml > /tmp/prod.yaml
grep -n "replicas:" /tmp/dev.yaml /tmp/prod.yaml
grep -n "storage:" /tmp/dev.yaml /tmp/prod.yaml
```

---

## 14（26~28h）：Helm 升級與回滾

### 參考檔案

- [helm/rag-app/Chart.yaml](../helm/rag-app/Chart.yaml)
- [helm/rag-app/values-dev.yaml](../helm/rag-app/values-dev.yaml)
- [helm/rag-app/values-prod.yaml](../helm/rag-app/values-prod.yaml)

### 這階段存在意義

Helm 的價值不是只會 install，而是可以 upgrade、看 history、必要時 rollback。

### 這階段做了什麼

- `helm upgrade --install` 安裝 release。
- 以 revision 歷史追蹤升級。
- 用 `helm rollback` 回到穩定版。

### 關鍵名詞

- **Release**：Helm 安裝到叢集後的實例。
- **Revision**：release 的版本號。
- **Rollback**：回退到某個 revision。

### 指令片段與解說

```bash
kubectl get ns rag-helm >/dev/null 2>&1 || kubectl create ns rag-helm
minikube image load rag_project-rag-app:latest

helm upgrade --install rag-app helm/rag-app -n rag-helm -f helm/rag-app/values-dev.yaml --wait --timeout 180s
helm history rag-app -n rag-helm

helm upgrade rag-app helm/rag-app -n rag-helm -f helm/rag-app/values-staging.yaml --wait --timeout 180s
helm upgrade rag-app helm/rag-app -n rag-helm -f helm/rag-app/values-prod.yaml --wait --timeout 180s

helm rollback rag-app 1 -n rag-helm --wait --timeout 180s
```

逐段解說：

- `upgrade --install`：第一次沒裝過就 install，裝過就 upgrade。
- `--wait`：等資源真的 ready 才結束。
- `helm history`：查 revision 歷史。
- `helm rollback`：回到穩定版。

### 怎麼改

- 換 release 名稱時，所有相關命令都要一起改。
- 換 namespace 時，要連同 `kubectl` 與 `helm` 的 namespace 一起改。
- 換 values 檔時，要確認該環境的資源與 PVC 設定合理。

### 怎麼驗證

```bash
helm history rag-app -n rag-helm
kubectl -n rag-helm rollout status deployment/rag-app --timeout=180s
```

---

## 15（28~30h）：GitLab CI 治理閘道

### 參考檔案

- [/.gitlab-ci.yml](../.gitlab-ci.yml)

### 這階段存在意義

GitLab 在這裡扮演治理層：先做語法檢查、再做品質檢查、再做安全掃描，最後才決定要不要觸發 Jenkins。

### 這階段做了什麼

- 建立 `validate`、`quality`、`security` 三段式 gate。
- 加上 `trigger_jenkins`。

### 關鍵名詞

- **Pipeline**：一組自動化流程。
- **Stage**：pipeline 的階段。
- **Gate**：通過門檻，不過就卡住。

### 程式片段與解說

```yaml
stages:
  - validate
  - quality
  - security
  - trigger

validate:
  script:
    - python -m compileall app.py core services
    - ruff check core services tests app.py

quality:
  script:
    - make test

security:
  script:
    - pip install pip-audit bandit
    - pip-audit -r requirements.txt
    - bandit -q -r core services app.py

trigger_jenkins:
  needs:
    - validate
    - quality
    - security
```

逐段解說：

- `validate`：先擋 syntax 與 lint 類問題。
- `quality`：確認核心行為仍正常。
- `security`：先做依賴漏洞與危險寫法掃描。
- `needs`：前面 gate 沒過，後面就不該動。

### 怎麼改

- 如果要更嚴格，可以把 lint 規則擴大。
- 如果要更快，可以調整 cache 與 image。
- 如果要限制只在特定分支跑，改 `rules`。

### 怎麼驗證

- 看 GitLab Pipeline 是否依序通過。
- 若任一 stage fail，後面不應繼續。

---

## 16（30~32h）：GitLab 安全強化

### 參考檔案

- [/.gitlab-ci.yml](../.gitlab-ci.yml)

### 這階段存在意義

安全不是上線後才補，而是要在最上游先擋。這裡用依賴掃描與靜態安全掃描，先看出風險。

### 這階段做了什麼

- 加入 `pip-audit` 掃依賴漏洞。
- 加入 `bandit` 掃 Python 原始碼風險。

### 關鍵名詞

- **Dependency scanning**：掃套件漏洞。
- **Static security scanning**：掃原始碼風險。

### 程式片段與解說

```yaml
security:
  script:
    - pip install pip-audit bandit
    - pip-audit -r requirements.txt
    - bandit -q -r core services app.py
```

逐段解說：

- `pip-audit`：檢查 requirements 裡是否有已知漏洞版本。
- `bandit`：檢查常見危險寫法，例如不安全檔案操作或危險 eval。

### 怎麼改

- 若有特定套件不想被掃，可以在掃描策略上調整，但要有理由。
- 若漏洞太多，可先做 allowlist / exception 管理。

### 怎麼驗證

- 只要掃到高風險問題，pipeline 就應該 fail。

---

## 17（32~34h）：GitLab 觸發 Jenkins

### 參考檔案

- [/.gitlab-ci.yml](../.gitlab-ci.yml)

### 這階段存在意義

GitLab 負責治理，Jenkins 負責執行。這一段是兩者的交接橋。

### 這階段做了什麼

- 在 `main` 等條件通過後，觸發 Jenkins job。

### 關鍵名詞

- **Trigger job**：由一個系統主動呼叫另一個系統啟動工作。
- **Webhook / API trigger**：透過 HTTP 請求啟動外部流程。
- **Build parameters**：把 branch、commit 等上下文帶進 Jenkins。
- **Fail-fast gate**：前置條件不滿足就提早結束，避免誤觸發。

### 程式片段與解說

```yaml
trigger_jenkins:
  stage: trigger
  image: curlimages/curl:8.9.1
  needs:
    - validate
    - quality
    - security
  script:
    - |
      if [ -z "$JENKINS_URL" ] || [ -z "$JENKINS_JOB" ] || [ -z "$JENKINS_TOKEN" ]; then
        echo "Skip Jenkins trigger: JENKINS_URL/JENKINS_JOB/JENKINS_TOKEN not set."
        exit 0
      fi
    - |
      curl -fsS -X POST "${JENKINS_URL%/}/job/${JENKINS_JOB}/buildWithParameters?token=${JENKINS_TOKEN}&branch=${CI_COMMIT_REF_NAME}&commit=${CI_COMMIT_SHA}"
```

逐段解說：

- `curlimages/curl`：用最小 image 做 HTTP 觸發。
- `JENKINS_URL/JENKINS_JOB/JENKINS_TOKEN`：沒有設定就跳過，避免 pipeline 卡死。
- `buildWithParameters`：把 branch / commit 帶給 Jenkins，方便追溯。

### 怎麼改

- 如果 Jenkins job 名稱變了，URL 也要改。
- 如果你要換 branch 條件，改 `rules`。
- 如果你要帶更多參數，可以擴充 query string。

### 怎麼驗證

- 先確認前面 3 個 gate 都過。
- 再確認 Jenkins 收到觸發請求。

---

## 18（34~36h）：Jenkins 前半管線

### 參考檔案

- [Jenkinsfile](../Jenkinsfile)

### 這階段存在意義

Jenkins 要做的是把程式碼固定到某個 commit，然後產出可部署工件、執行測試、執行掃描，留下證據。

### 這階段做了什麼

- 建立 `Checkout`、`Build`、`Test`、`Scan`。
- 產生 image tag 與證據檔。

### 關鍵名詞

- **Checkout**：抓出當前 commit。
- **Artifact**：產出的 image。
- **Scan**：安全檢查。

### 程式片段與解說

```groovy
stage('Checkout') {
  steps {
    checkout scm
    script {
      env.GIT_SHA_SHORT = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
      env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_SHA_SHORT}"
    }
  }
}

stage('Build') {
  steps {
    sh '''
      set -euo pipefail
      docker build -t "${LOCAL_IMAGE}" .
      docker image inspect "${LOCAL_IMAGE}" >/dev/null
    '''
  }
}

stage('Test') {
  steps {
    sh 'make check'
  }
}

stage('Scan') {
  steps {
    sh '''
      set -euo pipefail
      python -m pip install --upgrade pip
      python -m pip install pip-audit bandit
      pip-audit -r requirements.txt
      bandit -q -r core services app.py
    '''
  }
}
```

逐段解說：

- `checkout scm`：先把 repo 當前版本抓出來。
- `git rev-parse --short HEAD`：把 commit 變短，方便做 image tag。
- `docker build`：把源碼打成 image。
- `docker image inspect`：確認 image 真有成功建立。
- `make check`：沿用第 05 階段的品質閘道。
- `pip-audit` / `bandit`：把依賴與原始碼風險一起掃。

### 怎麼改

- 如果 image 命名規則變了，`IMAGE_TAG` / `LOCAL_IMAGE` 要一起改。
- 如果你要補新的掃描工具，就加在 `Scan` stage。
- 如果測試太慢，可以把 test 分層，但要保留最小必跑關卡。

### 怎麼驗證

- 檢查 Jenkins log 是否有 image tag、測試結果、掃描結果。
- 確認每次 build 都能對應到 commit。

---

## 19（36~38h）：Jenkins 後半管線

### 參考檔案

- [Jenkinsfile](../Jenkinsfile)

### 這階段存在意義

前半管線負責產生工件，後半管線負責把工件送進環境、驗證健康狀態。

### 這階段做了什麼

- 加上 `Push`、`Deploy`、`Smoke Test`。
- 若有 registry 就推 image。
- 用 Helm 進行部署。

### 關鍵名詞

- **Image push**：把本地 image 上傳到 registry 供叢集拉取。
- **Deploy**：把新版本套用到 Kubernetes 並等待就緒。
- **Smoke test**：最小可行健康驗證，確認服務可連與可回應。
- **Progressive release evidence**：每一步都留下可追溯紀錄。

### 程式片段與解說

```groovy
stage('Push') {
  when {
    expression { return (env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main' || env.CHANGE_TARGET == 'main') && env.DOCKER_REGISTRY?.trim() }
  }
  steps {
    sh '''
      set -euo pipefail
      if [ -z "${DOCKER_USERNAME:-}" ] || [ -z "${DOCKER_PASSWORD:-}" ]; then
        echo "Skip push: registry credentials not configured."
        exit 0
      fi
      echo "${DOCKER_PASSWORD}" | docker login "${DOCKER_REGISTRY}" -u "${DOCKER_USERNAME}" --password-stdin
      docker tag "${LOCAL_IMAGE}" "${DEPLOY_IMAGE}"
      docker push "${DEPLOY_IMAGE}"
    '''
  }
}

stage('Deploy') {
  steps {
    sh '''
      set -euo pipefail
      previous_revision="$(helm history "${HELM_RELEASE}" -n "${HELM_NAMESPACE}" 2>/dev/null | awk '$2=="deployed"{rev=$1} END{print rev}')"
      printf '%s\n' "${previous_revision:-}" > .jenkins_previous_revision
      helm upgrade --install "${HELM_RELEASE}" "${HELM_CHART}" \
        -n "${HELM_NAMESPACE}" --create-namespace \
        -f "${HELM_VALUES}" \
        --set image.repository="${DEPLOY_IMAGE_REPO}" \
        --set image.tag="${DEPLOY_IMAGE_TAG}"
    '''
  }
}

stage('Smoke Test') {
  steps {
    sh '''
      set -euo pipefail
      kubectl -n "${HELM_NAMESPACE}" rollout status deployment/"${HELM_RELEASE}" --timeout="${ROLLOUT_TIMEOUT}"
      kubectl -n "${HELM_NAMESPACE}" run smoke-${BUILD_NUMBER} --image=curlimages/curl:8.9.1 --restart=Never --rm -i -- curl -fsS "http://${HELM_RELEASE}${SMOKE_PATH}"
    '''
  }
}
```

逐段解說：

- `when`：只有有 registry 且在主分支時才推 image。
- `docker login`：如果有 registry，先登入。
- `helm history`：先記錄上一個 deployed revision，為 rollback 準備。
- `helm upgrade --install`：同一條命令處理首次安裝與升級。
- `kubectl rollout status`：確認 deployment 真的 roll out 完成。
- `curlimages/curl`：用臨時 Pod 做最小 smoke test。

### 怎麼改

- 如果 registry 更換，改 `DOCKER_REGISTRY` 與 login 流程。
- 如果部署 namespace 更換，改 `HELM_NAMESPACE`。
- 如果健康路徑不同，改 `SMOKE_PATH`。

### 怎麼驗證

- 看 Jenkins log 是否有 push / deploy / smoke test 成功。
- 看 rollout 是否成功。
- 看 smoke test 是否真的打到 health endpoint。

---

## 20（38~40h）：Jenkins 自動回滾

### 參考檔案

- [Jenkinsfile](../Jenkinsfile)

### 這階段存在意義

部署失敗時不能只報錯，要能自動退回穩定版，而且要保留證據鏈。

### 這階段做了什麼

- 在 `post { failure { ... } }` 實作 rollback。
- 保留 `.jenkins_previous_revision` 與 history。

### 關鍵名詞

- **Rollback target**：此次失敗後要回復的既有穩定版本。
- **Post-failure hook**：Pipeline 失敗後自動執行的處理區塊。
- **Operational evidence**：回滾歷史、revision 與狀態輸出等證據。
- **Recovery SLO mindset**：重點是縮短恢復時間，而不只紀錄失敗。

### 程式片段與解說

```groovy
post {
  failure {
    sh '''
      set +e
      previous_revision="$(cat .jenkins_previous_revision 2>/dev/null || true)"
      if [ -n "${previous_revision}" ]; then
        echo "Rollback target revision: ${previous_revision}"
        helm rollback "${HELM_RELEASE}" "${previous_revision}" -n "${HELM_NAMESPACE}" --wait --timeout="${ROLLOUT_TIMEOUT}"
        helm history "${HELM_RELEASE}" -n "${HELM_NAMESPACE}" | tee .jenkins_rollback_history
        kubectl -n "${HELM_NAMESPACE}" rollout status deployment/"${HELM_RELEASE}" --timeout="${ROLLOUT_TIMEOUT}"
      else
        echo "Skip rollback: no previous deployed revision recorded."
      fi
    '''
  }
  always {
    archiveArtifacts artifacts: '.jenkins_*', allowEmptyArchive: true
  }
}
```

逐段解說：

- `post.failure`：只有失敗時才做 rollback。
- `cat .jenkins_previous_revision`：讀出上一個穩定 revision。
- `helm rollback`：回到穩定版。
- `archiveArtifacts`：把證據保留下來。

### 怎麼改

- 如果你想改回滾等待時間，調 `ROLLOUT_TIMEOUT`。
- 如果你想回滾到更早版本，改 revision 來源。
- 如果你想加更多證據檔，也可以一起 archive。

### 怎麼驗證

- 故意讓 deploy 或 smoke test 失敗，確認會 rollback。
- 看 `.jenkins_rollback_history` 是否有輸出。

---

## 21（40~42h）：Prometheus 指標接入

### 參考檔案

- [app.py](../app.py)
- [observability/prometheus/prometheus.yml](../observability/prometheus/prometheus.yml)
- [observability/prometheus/rules/rag-alerts.yml](../observability/prometheus/rules/rag-alerts.yml)
- [observability/grafana/dashboards/rag-app.json](../observability/grafana/dashboards/rag-app.json)

### 這階段存在意義

沒有指標就沒有觀測基準。Prometheus 讓你把「感覺正常」變成「有數據證明正常」。

### 這階段做了什麼

- 在 app 裡加入 Counter / Histogram / Gauge。
- 起一個 metrics server。
- 準備 scrape config 與 dashboard。

### 關鍵名詞

- **Counter**：只會往上加的計數器。
- **Histogram**：看延遲分布與 P95 / P99。
- **Gauge**：可上下變動的即時值。
- **Scrape**：Prometheus 定期拉 metrics。

### 程式片段與解說

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

REQUEST_COUNTER = Counter(
    "rag_requests_total",
    "Total RAG user actions",
    ["action", "provider", "status"],
)
REQUEST_ERRORS = Counter(
    "rag_request_errors_total",
    "Total RAG user action failures",
    ["action", "provider", "error_type"],
)
REQUEST_LATENCY = Histogram(
    "rag_request_duration_seconds",
    "RAG user action latency in seconds",
    ["action"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 3, 5, 10, 20, 30),
)
INDEXED_CHUNKS = Gauge("rag_indexed_chunks", "Number of chunks currently indexed for the active document")
```

```python
def _ensure_metrics_server() -> None:
    if st.session_state.get("_metrics_server_started"):
        return
    metrics_port = int(os.getenv("METRICS_PORT", "8001"))
    start_http_server(metrics_port)
    st.session_state["_metrics_server_started"] = True
```

逐段解說：

- `Counter`：用來累計 action 成功/失敗次數。
- `Histogram`：記錄 embedding 與 query latency。
- `Gauge`：記錄目前索引中 chunk 數量與文件數量。
- `start_http_server`：把 metrics endpoint 掛在獨立 port。
- `METRICS_PORT`：可透過環境變數改 port。

### 怎麼改

- 如果你要更精準的延遲統計，可以改 Histogram buckets。
- 如果你要加新的觀測點，就新增 Counter 或 Gauge。
- 如果 metrics port 被占用，改 `METRICS_PORT`。

### 怎麼驗證

```bash
curl http://localhost:8001/metrics
```

你要看見：`rag_requests_total`、`rag_request_errors_total`、`rag_request_duration_seconds` 等指標輸出。

---

## 22（42~44h）：ELK 結構化日誌

### 參考檔案

- [app.py](../app.py)
- [observability/elk/logstash/rag-pipeline.conf](../observability/elk/logstash/rag-pipeline.conf)
- [observability/elk/kibana-queries.md](../observability/elk/kibana-queries.md)

### 這階段存在意義

指標回答「整體是不是健康」，log 回答「這次到底發生了什麼」。結構化 log 是 ELK 可以有效檢索的基礎。

### 這階段做了什麼

- 把 log 改成 JSON。
- 為每次事件帶上 `request_id`。
- 準備 Logstash pipeline 與 Kibana 查詢範本。

### 關鍵名詞

- **Structured log**：欄位固定的日誌。
- **request_id**：串起同一次操作的所有 log。
- **JSON lines**：最適合讓 log pipeline 處理的格式。

### 程式片段與解說

```python
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
LOGGER = logging.getLogger("rag_app")

def _log_event(event: str, **fields) -> None:
    payload = {
        "event": event,
        "component": "rag_app",
        "host": socket.gethostname(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    LOGGER.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
```

```conf
filter {
  json {
    source => "message"
    target => "rag"
  }
  mutate {
    rename => {
      "[rag][request_id]" => "request_id"
      "[rag][provider]" => "provider"
      "[rag][error_type]" => "error_type"
    }
  }
}
```

```md
## Kibana Query Templates

request_id : "abc123def456"
provider : "google" and error_type : *
event : "query_success" and elapsed_seconds > 3
```

逐段解說：

- `_log_event`：把每個事件寫成單行 JSON。
- `request_id`：讓同一次 embedding 或 query 的 log 可以串起來。
- Logstash `json` filter：把 message 轉成可查詢欄位。
- Kibana query 範本：讓你可以直接查 request_id、provider、error_type。

### 怎麼改

- 要新增欄位，只要在 `_log_event` 多帶 `fields`，Logstash 也要同步收。
- 如果你想改 index 名稱，改 Logstash output。
- 如果你想追更多行為，補更多 event 類型。

### 怎麼驗證

- 看 stdout 是否輸出單行 JSON。
- Logstash 是否能解析 `request_id` / `provider` / `error_type`。
- Kibana 是否能用 KQL 查到事件。

---

## 23（44~46h）：Alertmanager 告警

### 參考檔案

- [observability/prometheus/rules/rag-alerts.yml](../observability/prometheus/rules/rag-alerts.yml)
- [observability/alertmanager/alertmanager.yml](../observability/alertmanager/alertmanager.yml)

### 這階段存在意義

告警不是噪音，而是「什麼時候要叫人處理」。Prometheus 負責判斷，Alertmanager 負責路由、抑制與通知。

### 這階段做了什麼

- 定義 3 條核心 alert。
- 設定 Alertmanager route。

### 關鍵名詞

- **Alert rule**：何時該告警。
- **Alertmanager**：分組、抑制、路由。
- **Severity**：告警等級。

### 程式片段與解說

```yaml
groups:
  - name: rag-app-alerts
    rules:
      - alert: RagAppDown
        expr: up{job="rag-app"} == 0
        for: 2m
        labels:
          severity: critical
          service: rag-app

      - alert: RagAppHighErrorRate
        expr: |
          sum(rate(rag_request_errors_total[5m]))
          /
          clamp_min(sum(rate(rag_requests_total[5m])), 1)
          > 0.05
        for: 5m
        labels:
          severity: warning
          service: rag-app

      - alert: RagAppHighLatency
        expr: |
          histogram_quantile(
            0.95,
            sum(rate(rag_request_duration_seconds_bucket[5m])) by (le, action)
          ) > 3
        for: 10m
        labels:
          severity: warning
          service: rag-app
```

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: rag-default
  group_by:
    - alertname
    - service
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: rag-default
    webhook_configs:
      - url: http://alert-webhook:5001/alerts
        send_resolved: true
```

逐段解說：

- `RagAppDown`：最直接的存活告警。
- `RagAppHighErrorRate`：錯誤率超過 5% 就要注意。
- `RagAppHighLatency`：P95 latency 高於 3 秒，代表體感開始變差。
- `route`：決定告警怎麼分組、多久送一次、送到哪裡。

### 怎麼改

- 想更敏感就降低 threshold，但要注意噪音。
- 想換通知方式，就換 receiver。
- 想加 pager 或 slack，可以再加 webhook / email receiver。

### 怎麼驗證

- 確認 Prometheus 有讀到 rules。
- 確認 Alertmanager 有收到告警。
- 透過模擬 down / 高錯誤率 / 高延遲，確認會觸發。

---

## 24（46~48h）：故障演練與復盤

### 參考檔案

- [docs/incident_drills.md](./incident_drills.md)
- [Jenkinsfile](../Jenkinsfile)
- [observability/prometheus/rules/rag-alerts.yml](../observability/prometheus/rules/rag-alerts.yml)
- [observability/alertmanager/alertmanager.yml](../observability/alertmanager/alertmanager.yml)

### 這階段存在意義

這一段要把前面做過的部署、告警、回滾能力整合成實戰流程。SRE 重點不是系統永遠不壞，而是壞了能不能快速偵測、正確止血、留下可追溯證據、最後做出可行改善。

### 這階段做了什麼

- 設計 3 個 incident 劇本：壞版映像、API key 錯誤、高延遲。
- 每個劇本都定義觸發方式、預期現象、排障步驟、修復方式、驗收證據。
- 建立統一 postmortem 模板，確保每次演練都能收斂到根因與行動項目。

### 關鍵名詞

- **Incident drill**：可控故障演練，用來驗證應變流程。
- **MTTR**：Mean Time To Recovery，平均恢復時間。
- **Blast radius**：故障影響範圍。
- **Postmortem**：事件後復盤，聚焦系統改進而非責任指責。

### 程式片段與解說

```bash
# 壞版映像演練（Incident 1）
helm upgrade rag-app helm/rag-app \
  -n rag-helm \
  -f helm/rag-app/values-prod.yaml \
  --set image.repository=rag_project-rag-app \
  --set image.tag=does-not-exist \
  --wait --timeout 120s

kubectl -n rag-helm get pods
kubectl -n rag-helm describe pod <pod-name>
helm rollback rag-app <stable-revision> -n rag-helm --wait --timeout 180s
```

```bash
# API key 錯誤演練（Incident 2）
kubectl -n rag-helm create secret generic rag-app-secrets \
  --from-literal=GOOGLE_API_KEY=invalid-key \
  -o yaml --dry-run=client | kubectl apply -f -

kubectl -n rag-helm rollout restart deployment/rag-app
kubectl -n rag-helm logs deploy/rag-app --tail=200
```

```markdown
### 復盤模板核心欄位

- 事件摘要：時間、影響、偵測來源、SEV
- 時間線：T0 觸發、T+X 判斷、T+Y 緩解、T+Z 恢復
- 根因分析：直接原因、系統性原因、5 Whys
- 修正方案：24 小時內、7 天內、30 天內
- 行動項目：Owner、截止日、狀態
```

逐段解說：

- Incident 1 用來驗證「部署失敗 → 告警 → 回滾」整段鏈路。
- Incident 2 用來驗證「服務存活但功能失敗」的觀測能力。
- 復盤模板保證每次演練最後都能產生可執行改善，不只停在口頭結論。

### 怎麼改

- 你可以把 incident 劇本換成更貼近你系統的故障型態（例如 DB 連線中斷）。
- 你可以按團隊習慣調整 SEV 分級與時間線粒度。
- 你可以把 postmortem 的行動項目直接串到 issue tracker。

### 怎麼驗證

- 三個劇本都能被重現，且能在預期時間內恢復。
- 每個事件都有完整根因分析與修正方案。
- 復盤內容能對應到實際 pipeline 或配置改善。

---

## 25（48~50h）：面試彩排

### 參考檔案

- [docs/interview_rehearsal.md](./interview_rehearsal.md)
- [docs/sre_mvp_timeline.md](./sre_mvp_timeline.md)
- [docs/sre_mvp_timeline_detailed.md](./sre_mvp_timeline_detailed.md)

### 這階段存在意義

工程成果若無法在短時間被清楚表達，就很難在面試場景轉成評估優勢。這階段是把技術輸出轉換成「可展示、可回答、可追問」的敘事能力。

### 這階段做了什麼

- 產出 15 分鐘 demo 腳本（分段到分鐘）。
- 整理 10 題高頻追問與標準答案。
- 建立彩排檢核清單，確保敘事與實作一致。

### 關鍵名詞

- **Narrative**：技術敘事線，讓聽者快速理解重點。
- **Trade-off**：在成本、風險、複雜度間的取捨。
- **Evidence-based demo**：每段說明都能對應命令、畫面或 log 證據。
- **Scope control**：明確區分已完成與規劃中項目。

### 程式片段與解說

```markdown
15 分鐘 demo 節奏

0:00 - 1:30  系統邊界與責任分工
1:30 - 4:00  Compose 與可部署基線
4:00 - 6:30  Kubernetes + Helm（含 history）
6:30 - 9:30  GitLab gate + Jenkins rollback
9:30 - 12:30 Prometheus + ELK + Alertmanager
12:30 - 15:00 trade-off 與下一步
```

```bash
# 彩排時可直接展示的最小命令集合
docker compose ps
helm history rag-app -n rag-helm
kubectl -n rag-helm get deploy,po,svc
```

```markdown
高頻追問範例

Q: 為什麼 GitLab + Jenkins？
A: GitLab 做治理閘道，Jenkins 做交付執行，責任邊界清楚。

Q: 你如何定義部署成功？
A: rollout success + smoke test + 指標不惡化。
```

逐段解說：

- 腳本化後，演示不會因臨場緊張漏掉關鍵內容。
- 問答庫的目的是統一口徑，不是背稿。
- 最小命令集合可確保在有限時間內穩定完成展示。

### 怎麼改

- 你可以依目標職缺把問題重心調成平台、可靠度或成本導向。
- 你可以把 demo 時間切成 10 分鐘版與 20 分鐘版。
- 你可以加上「已完成 / 未完成」對照表，避免回答過度承諾。

### 怎麼驗證

- 可在 15 分鐘內完整演示不中斷。
- 能連續回答 10 題追問且敘事一致。
- 每個回答都能對應到 repo 中的實作證據。

---

## 附錄：這份筆記要怎麼拿來自訂

如果你要把這份筆記改成別的專案，優先改這些地方：

1. Image 名稱與 port：Dockerfile、Compose、K8s Deployment、Service、Prometheus scrape target 要一致。
2. 配置鍵：ConfigMap、Helm values、app 內讀取環境變數要一致。
3. 資料路徑：PVC mountPath、程式寫入路徑要一致。
4. Health endpoint：Docker healthcheck、readinessProbe、livenessProbe、smoke test 要一致。
5. metrics / log 欄位：app、Prometheus、ELK、Alert rule 要一致。

---

## 附錄：到這裡為止的完整順序

1. 先做 Dockerfile 與 `.dockerignore`。
2. 再做 docker-compose 與 healthcheck。
3. 再做 tests / Makefile / ruff / pytest。
4. 再做 K8s Namespace、ConfigMap、Secret template。
5. 再做 Deployment、Service。
6. 再做 readiness / liveness / requests / limits。
7. 再做 PVC。
8. 再做 minikube rollback drill。
9. 再做 Helm chart、template、values、多環境、rollback。
10. 再做 GitLab CI、Jenkins。
11. 最後把 metrics、logs、alerts 串起來。
12. 進行 3 個 incident 演練並完成 postmortem。
13. 完成 15 分鐘面試 demo 與 10 題追問彩排。