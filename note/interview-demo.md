# Interview Demo（15 分鐘實戰敘事）

## 3W

### What

這份文件是把 01-25 階段成果壓縮成 15 分鐘可展示的技術敘事。

### Why

- 面試官要看的是「系統思維 + 落地能力 + 故障應對」。
- 你要在有限時間展示完整交付鏈路與決策品質。

### Where/How

- Where：技術面試、內部分享、架構評審。
- How：背景 -> 架構 -> Pipeline -> 觀測 -> Incident -> 反思。

---

## 15 分鐘時間切片

1. 0-2 分：問題背景與目標（穩定性、可回滾、可觀測）。
2. 2-5 分：本機到容器（Docker/Compose）與品質門（pytest/ruff）。
3. 5-9 分：K8s/Helm 發布與回滾機制。
4. 9-12 分：Prometheus + ELK + Alertmanager 觀測閉環。
5. 12-15 分：事故演練與 postmortem 行動項。

---

## Demo 操作腳本（可實際執行）

### 本機啟動

```bash
docker compose up -d --build
docker compose ps
```

### 這段 Demo 指令怎麼說

- `docker compose up -d --build`：先把整套服務起來。
	- 用途：展示本機可重現環境。
	- 何時要用：你要先證明應用在自己的環境能啟動時。
- `docker compose ps`：確認容器狀態。
	- 用途：快速展示哪些服務已經 healthy。
	- 何時要用：面試 Demo 中作為可用性證據。

### 品質門

```bash
make check
```

### 這段品質門怎麼說

- 用途：展示你有把 lint 與 test 包成單一入口。
- 吃的參數：沒有額外參數時就是跑預設檢查集合。
- 何時要用：你想證明新需求不會輕易破壞現有功能時。
- 從零寫法：先說明你如何讓本機與 CI 用同一條命令驗證品質。

### 部署（示意）

```bash
helm upgrade --install rag-app helm/rag-app -n rag-demo -f helm/rag-app/values-dev.yaml --wait --timeout 180s
kubectl -n rag-demo rollout status deployment/rag-app --timeout=180s
```

### 這段部署驗證怎麼說

- `helm upgrade --install`：展示你用 Helm 管理版本與環境差異。
	- 用途：正式部署或升級。
	- 何時要用：你要展示可重複部署能力時。
- `-f values-dev.yaml`：展示環境參數化。
	- 用途：用不同 values 切換環境。
	- 何時要用：你想證明 dev / prod 不需改模板本體時。
- `kubectl rollout status`：展示部署完成後的驗證。
	- 用途：不是只有 apply，而是確認服務真的 ready。
	- 何時要用：面試官很常看你有沒有補最後一哩路。

### 故障與回滾（示意）

```bash
helm history rag-app -n rag-demo
helm rollback rag-app 1 -n rag-demo --wait --timeout 180s
```

### 這段故障回復怎麼說

- `helm history`：先找可回退版本。
- `helm rollback`：示範快速止血。
- 何時要用：你要展示事故處理能力，而不是只會部署不會回復時。
- 從零寫法：每次部署都要保留回到上一版的路徑，這樣 demo 才有完整閉環。

---

## 高頻面試題（精簡回答骨架）

1. 你如何確保部署安全？
- 先治理後交付：GitLab gate 擋風險，Jenkins 部署後必做 smoke，失敗即回滾。

2. 你如何做可觀測性設計？
- 指標看趨勢（Prometheus）、日誌看上下文（ELK）、告警看決策（Alertmanager）。

3. 你怎麼處理事故？
- 先止血再根因，最後用 postmortem 轉制度，追蹤行動項閉環。

### smoke test 是什麼

- `smoke test`：部署後最小可用性驗證。
	- 用途：確認服務至少能回應核心入口，而不是只看部署流程綠燈。
	- 何時要用：每次正式部署後都應該跑。
- 成功判斷準則：
	- 核心 health endpoint 回 200。
	- 主要業務入口能正常回應。
	- 關鍵指標沒有明顯惡化。
- 從零寫法：先挑最小的、最能代表服務活著的檢查，不要把 smoke test 做成完整回歸測試。

---

## 演示注意事項

- 所有命令先在本機跑過，避免現場語法錯誤。
- 用一個固定案例貫穿（例如「延遲飆升」）。
- 每段都明確說「做法 + 為什麼 + 風險控制」。

---

## 參考文件

- [Google Technical Writing（英文）](https://developers.google.com/tech-writing)
- [System Design Primer（英文）](https://github.com/donnemartin/system-design-primer)
- [STAR 面試回答法（英文）](https://en.wikipedia.org/wiki/Situation,_task,_action,_result)
