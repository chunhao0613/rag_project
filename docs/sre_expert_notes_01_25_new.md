# 01~25 專家級細節筆記（Docker.md 同級細節版）

這份是以你的 Docker 筆記為基準做的版本：

- 每階段都有 3W（What / Why / Where / How）
- 每階段都有「核心名詞定位與功能意義」表格
- 每階段都有「可執行步驟」
- 每階段都有「程式片段 / 指令片段」與「逐段解釋」
- 每階段都有「概念延伸」
- 每階段都有「驗證方式」
- 每階段都有「常見錯誤與面試回答角度」

---

## 00. 先讀：這份筆記怎麼用

1. 先看每階段的 3W，確認你在做什麼與為什麼。
2. 再看名詞定位表，確認每個元件在架構中的角色。
3. 跟著可執行步驟做，再用驗證方式確認結果。
4. 最後讀「常見錯誤 + 面試角度」，把實作轉成可說明能力。

---

## 01（0~2h）定義系統邊界與面試敘事

### 3W

- What：定義整條交付鏈路的責任邊界。
- Why：避免工具職責重疊，故障時可快速歸因。
- Where：README、架構圖、面試開場。
- How：用一條固定敘事線把四層責任串起來。

### 核心名詞定位與功能意義

| 關鍵名詞 | 在架構中的定位 | 核心作用 / 在你專案中的體現 | 解釋 |
|---|---|---|---|
| Responsibility Boundary | 全域設計層 | README 的責任分工段落 | 先定義誰負責什麼，再定義工具怎麼做 |
| Governance Plane | 准入治理層 | GitLab CI gate | 不合格變更不得進交付層 |
| Delivery Plane | 交付執行層 | Jenkins pipeline | 把合格工件送到目標環境 |
| Runtime Plane | 平台運行層 | Kubernetes + Helm | 用標準化模板運行服務 |
| Observability Plane | 監控回饋層 | Prometheus + ELK + Alertmanager | 讓異常可見、可追、可告警 |

### 可執行步驟

1. 先寫一行主線敘事。
2. 寫出四層責任（治理、執行、運行、觀測）。
3. 把這四層放進 README。
4. 練 60 秒開場口述。

### 參考片段

```markdown
GitLab: 准入治理
Jenkins: 交付執行
Kubernetes + Helm: 標準化運行
Prometheus + ELK + Alertmanager: 觀測與告警閉環
```

### 逐段解釋

- 先講責任，再講工具，面試官會覺得你是系統思維。
- 這段不是技術炫技，是「架構決策能力」的展示。

### 概念延伸

- RACI：誰負責（Responsible）、誰最終負責（Accountable）。
- Blast Radius：若某層壞掉，影響範圍到哪。

### 驗證方式

- 能 60 秒講完四層責任，且回答不自相矛盾。

### 常見錯誤與面試回答角度

- 常見錯誤：把 GitLab 和 Jenkins 都講成部署工具。
- 面試回答：我把決策層與執行層拆開，減少流程黑箱與責任混淆。

---

## 02（2~4h）定義 MVP 驗收與回滾規則

### 3W

- What：定義可量化驗收標準與回滾條件。
- Why：避免「看起來可以」就上線。
- Where：README 驗收標準、CI/CD policy。
- How：每條標準都對應具體驗證證據。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Acceptance Criteria | 交付規範層 | 定義成功條件 | 成功必須可被檢查，不靠直覺 |
| Rollback Policy | 風險控制層 | 定義止血條件 | 何時回滾要預先定義 |
| MTTR | 恢復指標層 | 衡量恢復速度 | SRE 重點是恢復，不是零錯誤 |
| Audit Trail | 審計證據層 | 留下可追溯紀錄 | 面試時能展示真實證據鏈 |

### 可執行步驟

1. 寫 6 條驗收標準。
2. 寫 3 個失敗情境（gate fail、deploy fail、smoke fail）。
3. 定義每個失敗情境對應處置。

### 參考片段

```text
若 lint 或 test fail -> 禁止 build/push/deploy
若 deploy fail -> rollback to previous stable revision
若 smoke test fail -> rollback + 保留故障證據
```

### 逐段解釋

- 這段的重點是「先定規則再做實作」。
- 規則是讓 pipeline 能做決策，不是寫給人看而已。

### 概念延伸

- Error Budget：可接受失敗的上限。
- Change Failure Rate：變更造成失敗的比例。

### 驗證方式

- 人工製造 fail，確認流程真的被阻擋。

### 常見錯誤與面試回答角度

- 常見錯誤：有標準但沒有自動化強制執行。
- 面試回答：我把標準轉成 pipeline 的硬 gate，確保政策可執行。

---

## 03（4~6h）容器化基線

### 3W

- What：建立 Dockerfile 與 .dockerignore。
- Why：統一執行環境與交付工件。
- Where：本機、CI、部署前工件層。
- How：分層 build、健康檢查、固定啟動命令。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Dockerfile | Build 指令層 | 把環境建置流程版本化 | 是交付一致性的起點 |
| Image | 交付工件層 | 不可變發佈單位 | 減少「環境不同」風險 |
| Layer Cache | 效能層 | 加速重複 build | 先 copy requirements 是關鍵技巧 |
| HEALTHCHECK | 健康層 | 提供容器健康訊號 | 可與編排層健康策略串接 |

### 可執行步驟

1. 選基底映像。
2. 安裝必要系統套件。
3. 先安裝 Python 依賴。
4. 複製應用程式。
5. 設 HEALTHCHECK。
6. 設 CMD。

### 程式片段

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

### 逐段解釋

- FROM：固定 runtime 基底。
- WORKDIR：固定工作目錄，降低路徑錯誤。
- RUN apt-get：補齊必要工具（healthcheck 用 curl）。
- COPY requirements + RUN pip：利用 cache 加速。
- COPY .：複製應用程式本體。
- HEALTHCHECK：容器自我健康訊號。
- CMD：容器啟動後預設執行命令。

### 概念延伸

- Multi-stage build：可再進一步瘦身。
- Supply chain security：可加 image signing。

### 驗證方式

```bash
docker build -t rag-app:local .
docker run --rm -p 8000:8000 rag-app:local
curl -fsS http://localhost:8000/_stcore/health
```

### 常見錯誤與面試回答角度

- 常見錯誤：把密鑰放進 image。
- 面試回答：我把 image 當不可變工件，敏感資訊改由部署時注入。

---

## 04（6~8h）本機編排與健康檢查

### 3W

- What：建立 docker-compose 讓本機一鍵啟動。
- Why：快速重現運行環境與依賴。
- Where：開發與排障前線。
- How：service/port/volume/healthcheck。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Compose Service | 本機編排層 | 容器服務定義 | 管理多服務依賴 |
| Port Mapping | 連通層 | 主機訪問容器 | 對外測試入口 |
| Volume | 資料層 | 持久化本機資料 | 重建容器不丟資料 |
| healthcheck | 健康層 | 本機存活檢查 | 快速觀察服務狀態 |

### 可執行步驟

1. 定義 rag-app 服務。
2. 設 ports。
3. 設 healthcheck。
4. 設 volume 與 env。

### 程式片段

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
```

### 逐段解釋

- build：本機直接 build 同一份 Dockerfile。
- ports：讓主機可直接驗證服務。
- healthcheck：compose 層健康訊號。
- volumes：讓資料跨容器生命週期保留。

### 概念延伸

- Compose 是 developer runtime，不是 production orchestrator。

### 驗證方式

```bash
docker compose up -d --build
docker compose ps
docker logs rag_app --tail 50
```

### 常見錯誤與面試回答角度

- 常見錯誤：把 depends_on 當成健康依賴保證。
- 面試回答：depends_on 只保證啟動順序，真正健康要靠 probe/healthcheck。

---

## 05（8~10h）最小測試與品質入口

### 3W

- What：建立 lint/test/check 最小品質門。
- Why：先擋壞變更再談自動部署。
- Where：本機 + CI。
- How：pytest + ruff + Makefile。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Ruff | 靜態分析層 | 快速抓語法/高風險錯誤 | 成本低、速度快 |
| Pytest | 測試層 | 核心行為回歸驗證 | 交付前防回歸 |
| Makefile | 命令入口層 | 一鍵執行品質流程 | 降低人為操作差異 |

### 可執行步驟

1. 建測試骨架。
2. 設 ruff 規則。
3. 建 make lint/test/check。
4. 先覆蓋核心路徑。

### 程式片段

```makefile
lint:
	ruff check core services tests app.py

test:
	pytest

check: lint test
```

### 逐段解釋

- lint：最先執行，先擋明顯錯誤。
- test：確認核心功能不回歸。
- check：把兩者串成單一入口。

### 概念延伸

- Shift-left quality：在最早階段擋錯。

### 驗證方式

```bash
make check
```

### 常見錯誤與面試回答角度

- 常見錯誤：初期就追高覆蓋率，忽略核心路徑。
- 面試回答：我先守住高風險路徑，逐步擴充測試深度。

---

## 06（10~12h）Kubernetes 配置基礎

### 3W

- What：建立 Namespace、ConfigMap、Secret 模板。
- Why：配置與程式碼分離，提升治理能力。
- Where：k8s/base。
- How：kustomization 組裝資源。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Namespace | 邊界隔離層 | 隔離資源命名與權限 | 降低互相污染 |
| ConfigMap | 公開設定層 | 模型與port設定 | 無需重建 image 即可改參數 |
| Secret | 機密層 | API key 類敏感值 | 安全注入 |
| Kustomization | 組裝層 | 一次套用一組 YAML | 基礎部署入口 |

### 可執行步驟

1. 建 namespace。
2. 建 configmap。
3. 建 secret.template。
4. 建 kustomization。

### 程式片段

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-app-config
  namespace: rag-mvp
data:
  STREAMLIT_SERVER_PORT: "8000"
  STREAMLIT_SERVER_ADDRESS: "0.0.0.0"
```

### 逐段解釋

- data 區塊是鍵值設定，不放機密。
- namespace 固定能避免跨環境誤操作。

### 概念延伸

- GitOps：配置應可被版本管理與審核。

### 驗證方式

```bash
kubectl apply --dry-run=client --validate=false -f k8s/base/configmap.yaml -o name
```

### 常見錯誤與面試回答角度

- 常見錯誤：Secret 真值入版控。
- 面試回答：我用 template 入庫，真值由環境注入，保持可審計與安全。

---

## 07（12~14h）Deployment 與 Service

### 3W

- What：建立工作負載與服務入口。
- Why：把容器轉成平台管理的服務。
- Where：k8s base runtime。
- How：Deployment 管副本，Service 管流量導向。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Deployment | 控制器層 | 管理 rollout 與副本 | 保持期望狀態 |
| Pod | 執行層 | 真實容器載體 | 運行 app 的基本單位 |
| Service | 網路抽象層 | 穩定存取入口 | Pod 重建也不影響入口 |
| Selector | 綁定層 | Service->Pod 對應 | 錯了就無流量 |

### 可執行步驟

1. 定 label。
2. deployment selector 對 label。
3. service selector 對 deployment label。
4. envFrom 注入 config/secret。

### 程式片段

```yaml
spec:
  selector:
    matchLabels:
      app: rag-app
  template:
    metadata:
      labels:
        app: rag-app
```

### 逐段解釋

- selector 與 label 必須一致，這是 service 是否有流量的關鍵。

### 概念延伸

- Service discovery：k8s 用 service 名稱做服務發現。

### 驗證方式

```bash
kubectl get deploy,po,svc -n rag-mvp
kubectl describe svc rag-app-svc -n rag-mvp
```

### 常見錯誤與面試回答角度

- 常見錯誤：label 命名不一致。
- 面試回答：我先檢查 selector/label 閉環，這是連線問題第一優先檢查點。

---

## 08（14~16h）探針與資源治理

### 3W

- What：加 readiness/liveness 及資源限制。
- Why：避免壞 Pod 接流量，避免資源失控。
- Where：deployment container spec。
- How：合理探針節奏 + requests/limits。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Readiness | 流量閘門層 | 控制是否加入 service endpoints | 啟動中或依賴失敗先不接流量 |
| Liveness | 自癒判斷層 | 判斷是否需重啟容器 | 防止掛死不自知 |
| Requests | 排程保底層 | scheduler 參考值 | 確保最小運行資源 |
| Limits | 保護上限層 | 防止單容器吃爆節點 | 降低噪鄰效應 |

### 可執行步驟

1. 設 readiness path。
2. liveness 延後啟動，避免冷啟誤判。
3. 設 requests/limits。
4. 觀察 events。

### 程式片段

```yaml
readinessProbe:
  httpGet:
    path: /_stcore/health
    port: http
livenessProbe:
  httpGet:
    path: /_stcore/health
    port: http
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: "1"
    memory: 1Gi
```

### 逐段解釋

- readiness 與 liveness 可以同 path，但節奏通常不同。
- requests 是排程參考，limits 是硬上限。

### 概念延伸

- OOMKilled 診斷：常由 limits 太低或記憶體洩漏引起。

### 驗證方式

```bash
kubectl describe pod -n rag-mvp <pod>
kubectl get events -n rag-mvp --sort-by=.lastTimestamp
```

### 常見錯誤與面試回答角度

- 常見錯誤：liveness 太急，導致冷啟重啟循環。
- 面試回答：我會先調 readiness 保障流量，再調 liveness 保障自癒。

---

## 09（16~18h）持久化策略

### 3W

- What：建立 PVC 與資料掛載。
- Why：避免 Pod 重建造成資料遺失。
- Where：k8s storage。
- How：資料分級 + 明確 mountPath。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| PVC | 申請層 | 宣告儲存需求 | 與底層儲存解耦 |
| AccessMode | 掛載模型層 | RWO/RWX | 影響可擴展方式 |
| MountPath | 應用接入層 | /app/data | 程式讀寫入口 |

### 可執行步驟

1. 建 PVC。
2. deployment 掛載。
3. 重建 Pod 驗資料。

### 程式片段

```yaml
volumes:
  - name: rag-data
    persistentVolumeClaim:
      claimName: rag-data-pvc
volumeMounts:
  - name: rag-data
    mountPath: /app/data
```

### 逐段解釋

- claimName 對應不到時，Pod 會 pending。
- mountPath 變更要同步檢查程式讀寫路徑。

### 概念延伸

- Stateful vs Stateless：RAG 常是混合型，要做資料分層。

### 驗證方式

```bash
kubectl get pvc -n rag-mvp
kubectl describe pvc rag-data-pvc -n rag-mvp
```

### 常見錯誤與面試回答角度

- 常見錯誤：把可重建 cache 也做持久化，增加成本。
- 面試回答：我會把資料分成可重建與不可重建兩類，做差異化策略。

---

## 10（18~20h）YAML 版回滾演練

### 3W

- What：演練壞版部署與回滾。
- Why：驗證「可恢復」而非只驗證「可部署」。
- Where：測試叢集。
- How：故障注入 -> 觀察 -> 回滾 -> 驗證。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Failure Injection | 測試設計層 | 主動製造故障 | 驗證流程不是紙上談兵 |
| Rollout Status | 運行檢查層 | 觀察部署結果 | 第一時間判斷是否失敗 |
| Rollback | 恢復層 | 回到穩定版本 | 降低故障暴露時間 |

### 可執行步驟

1. 將 image 設為不存在 tag。
2. 觀察 rollout timeout/fail。
3. rollback。
4. 驗證恢復。

### 指令片段

```bash
kubectl -n rag-mvp set image deployment/rag-app rag-app=rag_project-rag-app:does-not-exist
kubectl -n rag-mvp rollout status deployment/rag-app --timeout=90s
kubectl -n rag-mvp rollout undo deployment/rag-app
```

### 逐段解釋

- set image 是最直接故障注入方法。
- rollback 後要再看 rollout status，確定真的回穩。

### 概念延伸

- GameDay：定期故障演練制度化。

### 驗證方式

```bash
kubectl -n rag-mvp rollout history deployment/rag-app
```

### 常見錯誤與面試回答角度

- 常見錯誤：沒有紀錄演練過程與時間線。
- 面試回答：我會保留每次演練證據，作為 MTTR 與流程改進基線。

---

## 11（20~22h）Helm 初始化

### 3W

- What：建立 Helm chart 管理模板化資源。
- Why：降低手動維護 YAML 成本。
- Where：helm/rag-app。
- How：chart metadata + values + templates。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Chart.yaml | 套件描述層 | name/version/appVersion | chart 識別與版本管理 |
| values.yaml | 參數層 | image/resources/config | 可變配置集中化 |
| helm lint | 靜態檢查層 | 檢查 chart 結構 | 提前發現模板問題 |

### 可執行步驟

1. create chart。
2. 清理樣板。
3. 對齊現有部署結構。

### 程式片段

```yaml
apiVersion: v2
name: rag-app
type: application
version: 0.1.0
appVersion: "1.0.0"
```

### 逐段解釋

- version 是 chart 版本。
- appVersion 是應用版本，兩者不同。

### 概念延伸

- SemVer：讓升級風險可預測。

### 驗證方式

```bash
helm lint helm/rag-app
```

### 常見錯誤與面試回答角度

- 常見錯誤：chart 版本不更新，導致追溯困難。
- 面試回答：我分離 chart version 與 appVersion，保持模板與應用兩條版本線。

---

## 12（22~24h）核心模板化

### 3W

- What：把核心 k8s 資源模板化。
- Why：避免重複 YAML 與命名不一致。
- Where：helm templates。
- How：helpers 共享命名，values 注入參數。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| helpers.tpl | 共用規則層 | fullname/labels/pvcName | 降低命名分歧 |
| include | 模板引用層 | 套用 helper | 提升模板可維護性 |
| range values | 參數迭代層 | config map entries | 批次注入設定鍵值 |

### 可執行步驟

1. 寫 helper。
2. deployment/service 用 helper 命名。
3. configmap/secret 用 values 驅動。
4. render 檢查輸出。

### 程式片段

```yaml
name: {{ include "rag-app.fullname" . }}
```

### 逐段解釋

- 這行確保所有資源命名一致，減少人工拼接錯誤。

### 概念延伸

- DRY 原則在 IaC 同樣重要。

### 驗證方式

```bash
helm template rag-app helm/rag-app > /tmp/rag-rendered.yaml
```

### 常見錯誤與面試回答角度

- 常見錯誤：模板與 values 命名對不上。
- 面試回答：我用 helper 統一命名，減少模板與資源漂移。

---

## 13（24~26h）多環境 values

### 3W

- What：拆 dev/staging/prod values。
- Why：同一模板跨環境可控。
- Where：helm values files。
- How：用 override 控制副本、資源、儲存。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| values override | 參數覆蓋層 | -f values-prod.yaml | 不改模板切環境 |
| env parity | 環境一致性層 | staging 近似 prod | 降低上線意外 |
| config drift | 漂移風險層 | 線上手改配置 | 版本與現場分裂 |

### 可執行步驟

1. base values 定共通值。
2. env values 覆蓋差異值。
3. 渲染輸出比對。

### 程式片段

```yaml
# values-prod.yaml
replicaCount: 2
resources:
  requests:
    cpu: 500m
```

### 逐段解釋

- 生產環境通常副本與資源上限較高，保障穩定性。

### 概念延伸

- Promotion model：dev -> staging -> prod 漸進式驗證。

### 驗證方式

```bash
helm template rag-app helm/rag-app -f helm/rag-app/values-dev.yaml > /tmp/dev.yaml
helm template rag-app helm/rag-app -f helm/rag-app/values-prod.yaml > /tmp/prod.yaml
```

### 常見錯誤與面試回答角度

- 常見錯誤：直接複製三份模板，維護爆炸。
- 面試回答：我用單模板多 values 控制環境差異，降低維護成本。

---

## 14（26~28h）Helm 升級與回滾

### 3W

- What：練習 release 升級與回滾。
- Why：交付要可追溯、可恢復。
- Where：helm release lifecycle。
- How：upgrade/install + history + rollback。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| helm history | 追溯層 | revision time/status | 查每次變更紀錄 |
| helm rollback | 恢復層 | 回某個 revision | 版本回復明確化 |
| --wait --timeout | 控制層 | 等待就緒再返回 | 避免誤判部署成功 |

### 可執行步驟

1. install dev。
2. upgrade staging/prod。
3. rollback 到穩定 revision。

### 指令片段

```bash
helm upgrade --install rag-app helm/rag-app -n rag-helm -f helm/rag-app/values-dev.yaml --wait --timeout 180s
helm history rag-app -n rag-helm
helm rollback rag-app 1 -n rag-helm --wait --timeout 180s
```

### 逐段解釋

- history 是回滾前確認目標的依據。
- rollback 後要再看 rollout status。

### 概念延伸

- Progressive delivery：可逐步擴展至 canary/blue-green。

### 驗證方式

```bash
kubectl -n rag-helm rollout status deployment/rag-app --timeout=180s
```

### 常見錯誤與面試回答角度

- 常見錯誤：回滾完成後不驗證服務功能。
- 面試回答：回滾只是手段，服務恢復才是目標。

---

## 15（28~30h）GitLab CI 治理閘道

### 3W

- What：建立 validate/quality/security gate。
- Why：在最上游阻擋低品質與高風險變更。
- Where：GitLab pipeline。
- How：階段化檢查 + 失敗即阻擋。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| validate | 語法層 | compile + lint | 快速篩掉基礎錯誤 |
| quality | 測試層 | unit tests | 功能不回歸 |
| security | 安全層 | dependency/code scan | 風險前移 |
| needs | 依賴層 | stage 先後約束 | 失敗不下傳 |

### 可執行步驟

1. 建 stages。
2. 配 validate。
3. 配 quality。
4. 配 security。
5. 加 needs。

### 程式片段

```yaml
stages:
  - validate
  - quality
  - security
  - trigger
```

### 逐段解釋

- 先定 stage，再定每段 script，流程更清楚。

### 概念延伸

- Policy as Code：把治理規範寫成可執行流程。

### 驗證方式

- 故意引入 lint error，觀察 pipeline 是否停止於 validate。

### 常見錯誤與面試回答角度

- 常見錯誤：讓 trigger 不受前段結果約束。
- 面試回答：治理層的價值是能阻擋，不是只發通知。

---

## 16（30~32h）GitLab 安全強化

### 3W

- What：引入依賴與程式碼安全掃描。
- Why：供應鏈風險與危險寫法要提前攔截。
- Where：security stage。
- How：pip-audit + bandit，設定 fail policy。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| pip-audit | 依賴風險層 | CVE 掃描 | 找出已知漏洞版本 |
| bandit | 程式風險層 | 危險模式掃描 | 發現潛在安全問題 |
| fail policy | 決策層 | 高風險阻擋 | 讓掃描結果可執行 |

### 可執行步驟

1. 安裝工具。
2. 掃 requirements。
3. 掃 app/core/services。
4. 高風險 fail。

### 指令片段

```bash
pip-audit -r requirements.txt
bandit -q -r core services app.py
```

### 逐段解釋

- pip-audit 看依賴 CVE。
- bandit 看原始碼風險模式。

### 概念延伸

- DevSecOps：安全內建到開發流程，而非後補。

### 驗證方式

- 測試引入高風險依賴，確認 pipeline fail。

### 常見錯誤與面試回答角度

- 常見錯誤：掃描只輸出報表，不做阻擋。
- 面試回答：安全掃描要能影響交付決策，才是治理能力。

---

## 17（32~34h）GitLab 觸發 Jenkins

### 3W

- What：gate 通過後觸發 Jenkins。
- Why：治理層與執行層解耦。
- Where：GitLab trigger stage。
- How：HTTP 觸發 + token + 參數傳遞。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| webhook/API trigger | 串接層 | buildWithParameters | 跨系統啟動流程 |
| token auth | 安全層 | Jenkins token | 受控觸發 |
| branch/commit params | 追溯層 | CI_COMMIT_REF_NAME/SHA | 確保執行上下文一致 |

### 可執行步驟

1. 檢查環境變數。
2. 組 trigger URL。
3. POST 觸發。
4. 傳 branch/commit。

### 程式片段

```yaml
curl -fsS -X POST "${JENKINS_URL%/}/job/${JENKINS_JOB}/buildWithParameters?token=${JENKINS_TOKEN}&branch=${CI_COMMIT_REF_NAME}&commit=${CI_COMMIT_SHA}"
```

### 逐段解釋

- %/ 是去掉尾端 /，避免 URL 雙斜線。
- 帶 branch/commit 能建立完整追溯鏈。

### 概念延伸

- Event-driven pipeline：事件驅動交付。

### 驗證方式

- gate fail 時不觸發。
- gate pass 時 Jenkins 收到 job。

### 常見錯誤與面試回答角度

- 常見錯誤：觸發失敗沒有降級策略。
- 面試回答：我做 skip-safe 檢查，避免治理層因外部依賴整段中斷。

---

## 18（34~36h）Jenkins 前半管線

### 3W

- What：checkout/build/test/scan。
- Why：先確保工件品質，再進部署。
- Where：Jenkins pipeline 前半段。
- How：固定來源、固定版本標籤、固定檢查。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| checkout scm | 來源層 | 鎖定 commit | 建立可追溯起點 |
| image tag strategy | 版本層 | BUILD-SHA | 避免 latest 混淆 |
| scan stage | 安全層 | 上線前風險檢查 | 降低生產風險 |

### 可執行步驟

1. checkout。
2. 產 GIT_SHA_SHORT。
3. docker build。
4. make check。
5. 掃描。

### 程式片段

```groovy
env.GIT_SHA_SHORT = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_SHA_SHORT}"
```

### 逐段解釋

- BUILD_NUMBER + SHA 能同時保留執行序與來源版本。

### 概念延伸

- Reproducible build：同來源可重建同結果。

### 驗證方式

- build log 能對應 commit。
- test/scan fail 時 pipeline 終止。

### 常見錯誤與面試回答角度

- 常見錯誤：無法從 image 追到 commit。
- 面試回答：我把 tag 規則固定，保證回滾與審計可追溯。

---

## 19（36~38h）Jenkins 後半管線

### 3W

- What：push/deploy/smoke test。
- Why：交付閉環要包含部署後功能驗證。
- Where：Jenkins 後半段。
- How：條件推送 + helm deploy + smoke。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| push policy | 發佈控制層 | main branch + creds | 降低誤發布 |
| deploy step | 上線層 | helm upgrade --install | 標準化部署 |
| smoke test | 驗證層 | curl health endpoint | 快速檢查可用性 |

### 可執行步驟

1. 條件滿足才 push。
2. 記錄 previous revision。
3. helm deploy。
4. rollout status。
5. smoke。

### 程式片段

```bash
kubectl -n "${HELM_NAMESPACE}" run smoke-${BUILD_NUMBER} --image=curlimages/curl:8.9.1 --restart=Never --rm -i -- curl -fsS "http://${HELM_RELEASE}${SMOKE_PATH}"
```

### 逐段解釋

- 用臨時 Pod 做 smoke，避免依賴外部工具環境。

### 概念延伸

- Post-deploy verification：部署後驗證是必需步驟。

### 驗證方式

- smoke test 成功。
- deployment rollout complete。

### 常見錯誤與面試回答角度

- 常見錯誤：把 rollout success 當完整成功。
- 面試回答：我要求 rollout + smoke + 指標確認三件事同時通過。

---

## 20（38~40h）Jenkins 自動回滾

### 3W

- What：部署失敗時自動回滾。
- Why：縮短故障暴露時間、減少人工依賴。
- Where：post failure block。
- How：讀取 previous revision，rollback 後再驗證。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| post.failure | 觸發層 | 失敗時自動執行 | 自動止血起點 |
| rollback target | 恢復層 | previous revision | 回復精準化 |
| artifact archive | 證據層 | .jenkins_* files | 事後可審計 |

### 可執行步驟

1. deploy 前寫 previous revision。
2. failure 時 rollback。
3. rollback 後 rollout status。
4. archive 證據。

### 程式片段

```groovy
helm rollback "${HELM_RELEASE}" "${previous_revision}" -n "${HELM_NAMESPACE}" --wait --timeout="${ROLLOUT_TIMEOUT}"
```

### 逐段解釋

- previous_revision 空值時要有防呆，避免誤 rollback。

### 概念延伸

- Auto-remediation：自動修復策略需保守且可審計。

### 驗證方式

- 人工故障注入，確認 pipeline 自動回復。

### 常見錯誤與面試回答角度

- 常見錯誤：回滾後無證據留存。
- 面試回答：我把回滾歷史與狀態輸出存檔，確保可審計。

---

## 21（40~42h）Prometheus 指標接入

### 3W

- What：導入核心 SLI 指標。
- Why：可靠度要數據化，不能只靠體感。
- Where：app metrics endpoint、Prometheus scrape。
- How：Counter/Histogram/Gauge。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| SLI | 服務指標層 | latency/error/request | 量化服務健康 |
| Counter | 累積層 | requests/errors total | 看趨勢 |
| Histogram | 分布層 | duration bucket | 看高分位延遲 |
| Gauge | 即時層 | indexed docs/chunks | 看當前狀態 |

### 可執行步驟

1. 定義指標。
2. 在 ingest/query/error 埋點。
3. 啟動 metrics server。
4. Prometheus 加抓取 job。

### 程式片段

```python
REQUEST_LATENCY = Histogram(
    "rag_request_duration_seconds",
    "RAG user action latency in seconds",
    ["action"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 3, 5, 10, 20, 30),
)
```

### 逐段解釋

- buckets 直接影響 P95/P99 準確度與可觀察性。

### 概念延伸

- SLO 設計：例如 P95 < 3s。

### 驗證方式

```bash
curl http://localhost:8001/metrics | grep rag_request_duration_seconds
```

### 常見錯誤與面試回答角度

- 常見錯誤：埋很多指標但沒有決策用途。
- 面試回答：我先定核心 SLI，再擴充次要指標，避免儀表板噪音。

---

## 22（42~44h）ELK 日誌接入

### 3W

- What：建立結構化日誌與查詢模板。
- Why：故障定位需要可關聯可檢索。
- Where：app logging + logstash + kibana。
- How：統一欄位 schema（request_id/provider/error_type）。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| JSON log | 格式層 | 單行結構化輸出 | 易於 pipeline 解析 |
| request_id | 關聯層 | 串起同次請求事件 | 快速追蹤鏈路 |
| logstash filter | 轉換層 | message -> 欄位 | 可搜尋可聚合 |
| KQL template | 查詢層 | 常見排障查詢 | 降低定位時間 |

### 可執行步驟

1. app 改 JSON logging。
2. 事件加 request_id。
3. logstash 解析欄位。
4. kibana 建查詢模板。

### 程式片段

```python
LOGGER.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
```

### 逐段解釋

- 單行 JSON 是日誌管線最穩定格式。

### 概念延伸

- Observability triad：metrics/logs/traces。

### 驗證方式

- 用 request_id 查到同次事件的完整 log。

### 常見錯誤與面試回答角度

- 常見錯誤：欄位名稱不一致，查詢難以重用。
- 面試回答：我先定欄位 schema，再寫查詢模板，保證可維護。

---

## 23（44~46h）Alertmanager 告警

### 3W

- What：建立核心告警與通知路由。
- Why：異常要能主動通知與分級處理。
- Where：Prometheus rules + Alertmanager。
- How：定義閾值、for 時間、severity、receiver。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| alert expression | 偵測層 | PromQL 規則 | 定義何時告警 |
| for duration | 穩定層 | 例如 for: 5m | 避免瞬時抖動誤報 |
| route/group | 通知層 | group_by/group_wait | 降噪與批次通知 |
| receiver | 輸出層 | webhook/email/slack | 實際通知端 |

### 可執行步驟

1. 定義 down/error/latency 規則。
2. 設 route 與 group 策略。
3. 設 receiver。
4. 演練 firing/resolved。

### 程式片段

```yaml
- alert: RagAppHighErrorRate
  expr: |
    sum(rate(rag_request_errors_total[5m]))
    /
    clamp_min(sum(rate(rag_requests_total[5m])), 1)
    > 0.05
  for: 5m
```

### 逐段解釋

- clamp_min 避免分母接近 0 造成誤判。
- for 讓告警更穩定，降低噪音。

### 概念延伸

- Alert fatigue：告警過多會降低值班效率。

### 驗證方式

- 人工製造錯誤率升高，確認告警觸發與恢復。

### 常見錯誤與面試回答角度

- 常見錯誤：全都設 critical，失去分級價值。
- 面試回答：我用 severity 分級處置，確保值班資源集中在高風險事件。

---

## 24（46~48h）故障演練與復盤

### 3W

- What：執行 3 個 incident 劇本並完成復盤。
- Why：把「可部署」提升為「可恢復 + 可改進」。
- Where：incident_drills 手冊與測試叢集。
- How：故障注入 -> 偵測 -> 止血 -> 恢復 -> 復盤。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Incident Drill | 演練層 | 壞版/錯 key/高延遲 | 驗證處置能力 |
| Timeline | 事件紀錄層 | T0/T+X/T+Y | 還原處置過程 |
| Root Cause | 根因層 | 直接原因 + 系統性原因 | 不是只找表面現象 |
| Action Item | 改善落地層 | owner + due date | 防止復盤流於形式 |

### 可執行步驟

1. Incident A：壞 image。
2. Incident B：錯 API key。
3. Incident C：高延遲。
4. 每案填復盤模板。

### 參考片段

```markdown
復盤最小欄位：
- 事件摘要
- 時間線
- 根因（5 Whys）
- 修正方案（24h/7d/30d）
- 行動追蹤（owner/due date）
```

### 逐段解釋

- 重點不在「演練成功」，而在「是否產生可執行改善」。

### 概念延伸

- Learning organization：每次事件都要增強系統，而非只恢復當下。

### 驗證方式

- 三個事件都有完整復盤文件。
- 每個復盤都有具體改善項目與責任人。

### 常見錯誤與面試回答角度

- 常見錯誤：只做技術回復，不做制度改善。
- 面試回答：我把復盤轉為可追蹤 action item，確保同錯不再發生。

---

## 25（48~50h）面試彩排

### 3W

- What：完成 15 分鐘 demo 與 10 題追問答庫。
- Why：把工程成果轉成可展示與可追問能力。
- Where：interview_rehearsal 文件與模擬面試。
- How：按時間分段、每段對應證據點。

### 核心名詞定位與功能意義

| 關鍵名詞 | 定位 | 作用 | 解釋 |
|---|---|---|---|
| Demo Script | 表達層 | 0~15 分鐘流程 | 降低臨場失誤 |
| Evidence Point | 證據層 | 指令輸出/儀表板/log | 確保不是空口說白話 |
| Trade-off | 決策層 | 成本/穩定/複雜度 | 展示工程判斷力 |
| Scope Control | 範圍層 | 已完成 vs 規劃中 | 防止過度承諾 |

### 可執行步驟

1. 按時間切 6 段演示。
2. 每段綁一個證據點。
3. 練 10 題追問。
4. 修正口徑不一致。

### 參考片段

```text
0:00-1:30 邊界
1:30-4:00 可部署
4:00-6:30 Helm
6:30-9:30 CI/CD + rollback
9:30-12:30 觀測
12:30-15:00 trade-off + 下一步
```

### 逐段解釋

- 先講邊界，能建立面試官對你架構能力的信任。
- 每段都要能點到真實證據（命令或圖表）。

### 概念延伸

- Storytelling for engineers：先問題、再方案、再證據、最後取捨。

### 驗證方式

- 15 分鐘可完整走完不中斷。
- 10 題追問回答一致且能對應證據。

### 常見錯誤與面試回答角度

- 常見錯誤：把 roadmap 講成現況。
- 面試回答：我會明確分「已落地」與「下一步」，並且只對已落地部分給可驗證證據。

---

## 全程通用：專家級驗證模板（可直接複製）

## A. 階段摘要

- 階段編號：
- 目標：
- 主要風險：
- 成功定義（量化）：

## B. 交付證據

- Commit SHA：
- Image Tag：
- Helm Revision：
- Pipeline Run：

## C. 執行證據

- 執行命令：
- 主要輸出：
- 成功現象：
- 失敗現象：

## D. 觀測證據

- Metrics：
- Logs（含 request_id）：
- Alerts（firing/resolved）：

## E. 風險控制

- 最可能故障點：
- 第一時間檢查三項：
- 回復策略：
- 目標恢復時間：

## F. 復盤與改善

- 根因：
- 立即修正（24h）：
- 短期改善（7d）：
- 長期改善（30d）：
- Owner / Due Date：

## G. 面試四句模板

1. 我這階段在解哪個風險。
2. 我採用什麼機制。
3. 我如何證明它有效。
4. 我做了什麼取捨，為什麼。
