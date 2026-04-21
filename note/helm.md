# Helm

## 3W

### What

Helm 是 Kubernetes 的套件管理器，把 YAML 模板化與版本化。

### Why

- 原生 YAML 在多環境維護時容易重複與漂移。
- 需要 release history 與 rollback 機制。

### Where/How

- Where：K8s 應用發布層。
- How：Chart + Values + Templates -> render -> install/upgrade/rollback。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| Chart | Helm 套件單位 | 包含 templates 與 values |
| Values | 參數來源 | 驅動模板差異 |
| Release | 一次安裝實例 | 有 revision history |
| Revision | 版本編號 | 回滾目標 |
| _helpers.tpl | 共用模板函式 | 統一命名與標籤 |
| Template | YAML 動態模板 | 由 `{{ }}` 與 `.Values` 組成 |
| include | 匯入 helper 函式 | 重用命名與片段 |
| range | 迴圈模板語法 | 批次產生多個項目 |
| if | 條件模板語法 | 依 values 切換區塊 |

### 協作關係

- Template 用 Values 渲染成 YAML。
- 每次 upgrade 產生新 revision。
- rollback 回到指定 revision。

### Helm 模板語法怎麼看

- `{{ ... }}`：Helm template 的輸出區塊。
  - 用途：把 values 或函式結果寫進最後 YAML。
  - 何時要用：只要內容需要動態生成就會用到。
- `.Values`：目前 release 的參數來源。
  - 用途：讀取 values 檔中的設定。
  - 何時要用：環境差異、image tag、資源限制這些會變動的值。
- `include`：呼叫 helper 產生文字。
  - 用途：重用名稱、labels、annotations。
  - 何時要用：多個模板要共用同一段邏輯時。
- `if` / `range`：條件與迴圈。
  - 用途：依 values 產生不同資源片段，或批次輸出多個項目。
  - 何時要用：例如多個 env、volume、config key 需要批量生成時。
- 從零寫法：先把固定 YAML 寫出來，再把會變的值換成 `.Values`，最後再抽 helper 和條件區塊。

---

## 手把手實作

## 模板片段

```yaml
metadata:
  name: {{ include "rag-app.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
        - name: rag-app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```

### 這段 Helm 模板怎麼寫

- `{{ include "rag-app.fullname" . }}`：呼叫 helper 產生名稱。
  - 用途：統一命名規則，避免不同模板各寫各的。
  - 何時要用：只要你有多個資源共享同一命名規範，就應該抽 helper。
- `.Values.replicaCount`：從 values 讀副本數。
  - 用途：讓不同環境只改參數，不改模板。
  - 何時要用：dev/prod 要不同配置時最常見。
- `.Values.image.repository` / `.Values.image.tag`：組合 image 名稱。
  - 用途：把 image 路徑與版本分開管理。
  - 何時要用：你要在 CI/CD 中動態切換 image tag 時。
- 從零寫法：先定義共用 helper，再把會變動的值全部搬進 values。

## 多環境 values 片段

```yaml
# values-dev.yaml
replicaCount: 1

# values-prod.yaml
replicaCount: 2
```

### 這份 values 檔怎麼寫

- 用途：把環境差異集中管理。
- 吃的參數：YAML key/value，例如 `replicaCount: 1`。
- 何時要用：同一套 chart 要套用到 dev、staging、prod 時。
- 從零寫法：先列出會變的值，再逐步把 template 裡的常數換成 `.Values`。

### helper 檔在做什麼

- `_helpers.tpl`：放共用函式，不直接產生獨立資源。
  - 用途：統一 fullname、labels、selector 名稱。
  - 何時要用：當你不想在每個模板檔重複寫相同命名規則時。
- 從零寫法：先把命名規則寫成 helper，再讓 deployment/service/configmap 共用。

## 指令與參數

```bash
helm lint helm/rag-app
```

- 檢查 chart 結構與模板語法。
- 何時用：修改 chart 後先做靜態檢查。

```bash
helm template rag-app helm/rag-app -f helm/rag-app/values-dev.yaml
```

- 本地渲染，不上叢集。
- `-f` 指定覆蓋 values 檔。
- 何時用：你想先看渲染結果，不想直接套到叢集時。

```bash
helm upgrade --install rag-app helm/rag-app -n rag-helm -f helm/rag-app/values-prod.yaml --wait --timeout 180s
```

- `upgrade --install`：存在就升級，不存在就安裝。
- `--wait`：等資源 ready。
- `--timeout`：等待上限。
- 何時用：正式部署或 CI/CD 需要一次完成安裝/升級時。

```bash
helm history rag-app -n rag-helm
helm rollback rag-app 1 -n rag-helm --wait --timeout 180s
```

- history 查 revision。
- rollback 回指定 revision。
- 何時用：新版本異常時，快速回到上一個穩定版本。

---

## 常見錯誤與排查

1. template 可渲染但 apply 失敗：values 類型錯。
2. rollback 成功但服務未恢復：未做 rollout status 驗證。
3. 命名漂移：未統一使用 helper。

---

## 面試回答角度

- 為什麼用 Helm：
  - 我用 Helm 把結構與參數分離，提升多環境一致性，並保留 revision 可回滾能力。

---

## 參考文件

- [Helm 官方文件（英文）](https://helm.sh/docs/)
- [Helm 官方文件：Charts（英文）](https://helm.sh/docs/topics/charts/)
- [Helm 官方文件：Templates（英文）](https://helm.sh/docs/chart_template_guide/)
