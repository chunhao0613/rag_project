# Incident Response（事件應變）

## 3W

### What

Incident Response 是從告警觸發到服務恢復、再到根因改善的完整流程。

### Why

- 沒流程會導致恢復慢、責任混亂、重複踩坑。
- SRE 核心不是「不出事」，而是「快速止血 + 可持續改善」。

### Where/How

- Where：on-call 實戰、故障演練、事後復盤。
- How：偵測 -> 分級 -> 止血 -> 根因 -> 復盤 -> 行動追蹤。

---

## 事件流程模板

1. 偵測：收到 critical alert（例如 5xx > 5% 連續 10 分鐘）。
2. 分級：判斷 P1/P2，啟動通報渠道。
3. 止血：回滾、限流、降級、切流量。
4. 根因：log + metrics + deploy diff 三線對照。
5. 復盤：無責檢討，輸出行動項與 owner。
6. 追蹤：設定截止日，確認行動落地。

### 關鍵名詞補充

- `P1`：最高優先級事故。
  - 用途：通常代表核心服務不可用或大範圍影響。
  - 何時要用：需要立即動員與對外通報時。
- `P2`：次高優先級事故。
  - 用途：有影響但可部分繞過或有降級手段。
  - 何時要用：需要處理但未達全面中斷時。
- `baseline`：正常狀態的基準值。
  - 用途：拿來判斷延遲、錯誤率、流量是否異常。
  - 何時要用：所有告警與復原判斷都要先知道正常值。
- `runbook`：標準處置手冊。
  - 用途：把常見事故的第一步處理寫成可執行步驟。
  - 何時要用：on-call 要快速止血時。
- 從零寫法：先定事故等級，再定 baseline，最後把常見處置寫進 runbook。

---

## 手把手演練腳本

## 案例：新版本導致延遲飆升

### Step 1 檢查指標

```bash
kubectl -n rag-prod get pods
kubectl -n rag-prod top pods
```

### 這段指令怎麼用

- `kubectl get pods`：看 Pod 目前狀態。
  - 用途：確認是不是有 Pod 沒起來或重啟中。
  - 何時要用：收到告警後的第一步。
- `kubectl top pods`：看即時資源使用量。
  - 用途：判斷是不是 CPU / memory 飆高導致問題。
  - 何時要用：你要先分辨是壓力問題還是應用錯誤時。
- 從零寫法：先用最小指令判斷服務是否活著，再決定要不要深入看 logs 或 rollout。

### Step 2 看 rollout 與變更

```bash
kubectl -n rag-prod rollout history deployment/rag-app
kubectl -n rag-prod rollout status deployment/rag-app --timeout=120s
```

### 這段回滾前檢查怎麼用

- `rollout history`：查部署版本歷史。
  - 用途：找出最近穩定 revision。
  - 何時要用：你懷疑新版本引發事故時。
- `rollout status`：等待部署狀態。
  - 用途：確認當前部署是否成功完成。
  - 何時要用：你想知道 rollout 是卡住還是已完成時。
- 從零寫法：先確認最新變更，再決定是否立即回滾，避免誤傷正常版本。

### Step 3 快速止血（回滾）

```bash
helm history rag-app -n rag-prod
helm rollback rag-app 12 -n rag-prod --wait --timeout 180s
```

### 這段回滾怎麼用

- `helm history`：看 release 歷史。
  - 用途：找出可回退的 revision。
  - 何時要用：需要確認哪個版本是最後穩定版本時。
- `helm rollback`：回到指定 revision。
  - 用途：快速恢復服務。
  - 何時要用：新版本確認有問題、而且你已經準備好止血時。
- `--wait` 與 `--timeout`：等回滾完成，避免不確定狀態。
- 從零寫法：先確認回滾目標，再執行回滾，最後一定要驗證復原結果。

### Step 4 驗證恢復

- p95 延遲恢復到基線。
- 5xx 比率回到閾值以下。
- 關鍵 API smoke test 全過。

---

## Postmortem 模板

- 事故摘要：時間、影響範圍、客戶影響。
- 時間線：偵測、通報、止血、恢復。
- 根因：技術根因 + 流程根因。
- 做得好：保留。
- 可改進：行動項（owner + due date）。

---

## 面試回答角度

- 你做 incident 後學到什麼：
  - 我會把修復轉成制度，例如新增 smoke gate、補監控、強化 rollback runbook，避免同類事故再發。

---

## 參考文件

- [Google SRE Book（英文）](https://sre.google/books/)
- [Google SRE Workbook（英文）](https://sre.google/workbook/)
- [PagerDuty Incident Response（英文）](https://response.pagerduty.com/)
