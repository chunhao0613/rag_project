# 25（48~50h）面試彩排包

本文件包含 15 分鐘 demo 腳本與 10 題高頻追問答案，目標是把工程實作轉成可口述、可演示、可回答 trade-off 的面試輸出。

## 15 分鐘 Demo 腳本

## 0:00 - 1:30 開場與系統邊界

你要說明：

- GitLab：治理閘道（validate、quality、security）。
- Jenkins：交付執行（build、scan、deploy、rollback）。
- Kubernetes + Helm：標準化部署與版本管理。
- Prometheus + ELK + Alertmanager：觀測與告警閉環。

一句話版本：

「我把這個 RAG 專案做成可部署、可觀測、可回滾的 SRE MVP。」

## 1:30 - 4:00 展示可部署

建議展示：

```bash
docker compose up -d --build
docker compose ps
```

重點話術：

- 本機可重現。
- 有 health check。
- 基礎品質閘道可跑。

## 4:00 - 6:30 展示 Kubernetes + Helm

建議展示：

```bash
helm lint helm/rag-app
helm history rag-app -n rag-helm
kubectl -n rag-helm get deploy,po,svc
```

重點話術：

- 用 values 切 dev/staging/prod。
- 升級與回滾可追蹤 revision。

## 6:30 - 9:30 展示 CI/CD 閘道與自動回滾

建議展示：

- GitLab pipeline 的 validate/quality/security。
- Jenkins 的 deploy 失敗後 rollback 證據（history + log）。

重點話術：

- 先治理再交付。
- fail-fast 與 MTTR 思維。

## 9:30 - 12:30 展示觀測閉環

建議展示：

- Prometheus 指標：錯誤率、延遲。
- ELK 查詢：request_id / provider / error_type。
- Alertmanager：告警觸發與恢復。

重點話術：

- 指標告訴你「有沒有問題」。
- 日誌告訴你「問題在哪裡」。
- 告警告訴你「什麼時候要處理」。

## 12:30 - 15:00 收尾與 trade-off

建議收尾句：

- 目前 MVP 側重穩定性與可回復性。
- 成本與複雜度控制在面試可展示範圍。
- 下一步可補 incident 自動化演練與容量策略。

---

## 10 題高頻追問與答案

### 1) 為什麼用 GitLab + Jenkins，而不是單一平台？

答案：

我把兩者拆成治理與執行。GitLab 做 gate，比較像 policy entry；Jenkins 做交付管線，方便整合既有部署工具。這樣責任邊界清楚，且可替換性高。

### 2) Docker healthcheck 與 readiness/liveness 差異？

答案：

Docker healthcheck 是容器層訊號；readiness/liveness 是編排層決策。readiness 決定接不接流量，liveness 決定要不要重啟。

### 3) 你如何定義部署成功？

答案：

不只 rollout success，還要 smoke test 通過，且核心監控指標不惡化。這樣才算真正可用。

### 4) 為什麼先做測試閘道再做 CI/CD？

答案：

沒有可執行 gate，CI/CD 只是在自動化傳遞風險。先擋低品質變更，才能降低後續部署失敗率。

### 5) 回滾策略怎麼設計？

答案：

保留上一個穩定 revision，deploy 失敗或 smoke test 失敗就自動 rollback，並留存證據檔供追溯。

### 6) 你怎麼避免告警噪音？

答案：

只保留有行動價值的 3 條核心告警，並設定合理 for 時間與重發間隔，減少瞬時抖動造成的噪音。

### 7) 為什麼用 Helm，不直接維護 YAML？

答案：

YAML 適合宣告狀態，但多環境維護成本高。Helm 把結構與參數分離，降低重複與漂移風險。

### 8) 如果 production 發生高錯誤率，你第一步做什麼？

答案：

先看告警與 SLO 指標判斷影響範圍，再用 request_id 到 ELK 定位錯誤路徑，同步確認近期變更，必要時先回滾止血。

### 9) 你在這個 MVP 做了哪些取捨？

答案：

我優先做可部署、可觀測、可回滾，不先做高複雜的多叢集與進階網路治理。這是以面試時限換取可驗證成果的取捨。

### 10) 下一步你會做什麼？

答案：

補完整 incident 演練自動化、容量壓測基線、以及更明確的 SLO/Error budget 機制，讓營運決策更量化。

---

## 彩排檢核清單

- 能在 15 分鐘內演示完整流程。
- 能說清楚每層責任邊界。
- 能回答至少 10 題追問且不自相矛盾。
- 能清楚區分已完成與未完成項目。
