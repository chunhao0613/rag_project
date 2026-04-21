# RAG 系統 SRE 交付與維運實踐 (SRE Interview MVP)
## 專案概述

本專案將一個基於大語言模型（LLM）的 Retrieval-Augmented Generation (RAG) 應用，轉化為具備高可用性、可自動化交付且高度可觀測的企業級服務。

專案的核心目標不在於單純實現 RAG 功能。透過標準化的 CI/CD 流程、Kubernetes 容器編排以及完整的監控告警機制，確保系統能夠穩定、安全且高效地迭代與運行。

## 核心責任邊界 (Responsibility Boundaries)

本專案嚴格遵守治理與執行分離的設計原則：
> **GitLab** 負責准入治理，**Jenkins** 負責建置與部署執行，**Kubernetes 與 Helm** 負責標準化交付，**Prometheus 與 ELK** 負責觀測與告警閉環。

## 系統架構 (System Architecture)
<img width="2463" height="2318" alt="未命名绘图 drawio (4)" src="https://github.com/user-attachments/assets/ab89feac-d491-46dc-aa79-17ccdba88bc5" />


## 時間進程表

完整的 50 小時每 2 小時區塊執行表請見 [docs/sre_mvp_timeline.md](docs/sre_mvp_timeline.md)。

## 05 階段：最小測試與品質入口（本機）

已提供 `tests/` 骨架與 `Makefile` 指令：

- `make lint`：檢查核心程式碼與測試（`core/`、`services/`、`tests/`、`app.py`）
- `make test`：執行測試
- `make check`：一鍵執行 lint + test

目前優先覆蓋的核心路徑：

- 文件處理：`core/document_processor.py`
- 向量化：`services/vector_store.py`
- 模型選擇（LLM provider routing）：`services/llm_service.py`

## MVP 驗收標準 (Acceptance Criteria)

本專案的成功定義基於以下 6 項硬性指標：

1. **品質閘道阻擋 (GitLab CI)**
   任何 lint、測試、或基礎安全檢查未通過的程式碼變更，絕對禁止進入後續的 Image Build 與交付流程。
3. **全自動化交付 (Jenkins)**
   Pipeline 必須包含 `build`、`test`、`scan`、`push`、`deploy`、`smoke test` 六個關鍵階段，且每一階段皆須保留可審計的執行紀錄。
5. **標準化與可配置部署 (Kubernetes & Helm)**
   系統必須運行於 Kubernetes 叢集，並透過 Helm Chart 進行模板化管理，支援動態載入 `values-dev.yaml`、`values-staging.yaml` 與 `values-prod.yaml` 以實現環境配置分離。
7. **低 MTTR 回滾機制 (Rollback)**
   當部署失敗或 Smoke Test 未通過時，系統必須能在 5 分鐘內自動或手動安全回滾至上一個穩定的 Revision。
9. **探針與健康檢查 (Probes & Health Check)**
   應用層必須實作 `liveness` 與 `readiness` probes，確保平台能準確識別應用崩潰（需自癒重啟）與依賴失效（需暫停流量）的差異。
11. **可觀測性與告警 (Observability & Alerting)**
      * **Metrics**: Prometheus 必須能收集 API 延遲、錯誤率與服務重啟次數。
      * **Logs**: ELK 必須能集中檢索結構化日誌，追蹤跨模組請求脈絡。
      * **Alerts**: Alertmanager 需設定針對高錯誤率與高延遲的具體處置告警。

**驗收判定方式**

* 若能成功從提交變更一路走到部署與觀測，且有明確日誌、指標與回滾證據，則視為通過。
* 若只能「跑起來」，但無法證明可部署、可觀測、可回滾，則不視為 SRE MVP。
* 若無法清楚說明每個元件的責任邊界與故障處理方式，則不視為可面試展示版本。

---
> *註：本專案依循敏捷開發原則，目前持續迭代完善各項基礎設施與 CI/CD 管線中。*
