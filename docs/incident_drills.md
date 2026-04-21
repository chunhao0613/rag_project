# 24（46~48h）故障演練與復盤手冊

本手冊提供 3 個可重現的 incident 劇本，目的不是製造故障，而是驗證告警、排障、回滾與復盤流程是否可執行。

## 演練前置

- 環境：minikube 或可用的測試叢集。
- 服務：rag-app 已完成 Helm 部署。
- 觀測：Prometheus、Alertmanager、ELK 可查。
- 風險控管：演練只在測試環境執行。

建議先記錄基線：

```bash
kubectl -n rag-helm get deploy,po,svc
helm history rag-app -n rag-helm
kubectl -n rag-helm get events --sort-by=.lastTimestamp | tail -n 20
```

---

## Incident 1：壞版映像導致服務無法啟動

### 情境目標

驗證部署失敗時，團隊能在 5 分鐘內完成偵測與回滾。

### 觸發方式

```bash
helm upgrade rag-app helm/rag-app \
  -n rag-helm \
  -f helm/rag-app/values-prod.yaml \
  --set image.repository=rag_project-rag-app \
  --set image.tag=does-not-exist \
  --wait --timeout 120s
```

### 預期現象

- Pod 進入 ImagePullBackOff 或 ErrImagePull。
- 服務不可用或無法 Ready。
- 告警觸發 RagAppDown。

### 排障步驟

```bash
kubectl -n rag-helm get pods
kubectl -n rag-helm describe pod <pod-name>
kubectl -n rag-helm get events --sort-by=.lastTimestamp | tail -n 30
helm history rag-app -n rag-helm
```

### 修復與回滾

```bash
helm rollback rag-app <stable-revision> -n rag-helm --wait --timeout 180s
kubectl -n rag-helm rollout status deployment/rag-app --timeout=180s
```

### 驗收證據

- 回滾前後 revision。
- rollout status 成功訊息。
- 告警從 firing 回到 resolved。

---

## Incident 2：模型 API Key 錯誤導致高錯誤率

### 情境目標

驗證應用層錯誤（非容器崩潰）是否能透過 metrics 與 logs 快速定位。

### 觸發方式

以錯誤金鑰更新 Secret（測試環境）：

```bash
kubectl -n rag-helm create secret generic rag-app-secrets \
  --from-literal=GOOGLE_API_KEY=invalid-key \
  -o yaml --dry-run=client | kubectl apply -f -

kubectl -n rag-helm rollout restart deployment/rag-app
kubectl -n rag-helm rollout status deployment/rag-app --timeout=180s
```

### 預期現象

- 應用仍存活，但查詢成功率下降。
- rag_request_errors_total 上升。
- ELK 中出現 provider=google 與 error_type 欄位。

### 排障步驟

```bash
kubectl -n rag-helm logs deploy/rag-app --tail=200
curl -s http://<metrics-endpoint>/metrics | grep rag_request_errors_total
```

Kibana 建議查詢：

- provider : "google" and error_type : *
- event : "query_error"

### 修復與回滾

```bash
# 還原正確 key 後
kubectl -n rag-helm rollout restart deployment/rag-app
kubectl -n rag-helm rollout status deployment/rag-app --timeout=180s
```

### 驗收證據

- 錯誤率曲線回落。
- 同時段的 error log 顯著下降。

---

## Incident 3：高延遲事件（P95 > 3s）

### 情境目標

驗證延遲告警與容量調整流程，並檢查是否需要降載或擴容。

### 觸發方式

降低資源限制並施加壓力（測試環境）：

```bash
helm upgrade rag-app helm/rag-app \
  -n rag-helm \
  -f helm/rag-app/values-prod.yaml \
  --set resources.requests.cpu=100m \
  --set resources.limits.cpu=200m \
  --wait --timeout 180s
```

再執行一段高頻查詢流量（可用簡單迴圈或壓測工具）。

### 預期現象

- RagAppHighLatency 觸發。
- Histogram 的高分位延遲上升。

### 排障步驟

```bash
kubectl -n rag-helm top pod
kubectl -n rag-helm describe pod <pod-name>
```

### 修復與回滾

- 恢復原始資源配置，必要時提高副本數。
- 若為版本問題，回滾至上一個穩定 revision。

### 驗收證據

- P95 恢復到閾值以下。
- 告警 resolved。

---

## 復盤模板（Postmortem Template）

> 每次演練都要填。重點是根因、修正方案、預防方案，避免同類事件重複發生。

### A. 事件摘要

- Incident ID：
- 事件名稱：
- 日期時間（UTC+8）：
- 影響範圍：
- 偵測來源（Alert/使用者回報/排程檢查）：
- 嚴重度（SEV）：

### B. 時間線

| 時間 | 事件 |
|---|---|
| T0 | 告警觸發 |
| T+X | 初步判斷 |
| T+Y | 緩解完成 |
| T+Z | 完全恢復 |

### C. 根因分析

- 直接原因：
- 系統性原因：
- 為什麼沒有在前一關被擋下：

可使用 5 Whys：

1. 為什麼發生？
2. 為什麼沒有提早發現？
3. 為什麼保護機制沒擋住？
4. 為什麼流程允許這個風險進入？
5. 根本制度缺口是什麼？

### D. 修正方案

- 立即修復（24 小時內）：
- 短期改善（7 天內）：
- 長期改善（30 天內）：

### E. 行動項目追蹤

| 項目 | Owner | 截止日 | 狀態 |
|---|---|---|---|
| 例：新增 CI gate | xxx | 2026-05-01 | TODO |

### F. 面試敘事版本

- 事件一句話：
- 你做的判斷：
- 你做的技術動作：
- 最後學到的 trade-off：
