# 50 小時 SRE 面試 MVP 時間進程表

這份文件是主 README 的延伸索引，專注於 50 小時的實作與學習節奏。主頁 README 只保留專案概述、責任邊界與驗收標準，細部時程則放在這裡，方便後續獨立維護。

## 排程原則

- 每 2 小時為一個區塊，共 25 個區塊。
- 每個區塊都包含三件事：原理理解、實作產出、驗證證據。
- 先完成可部署能力，再做可觀測、可回滾與面試彩排。

## 0~4h：已完成的前置階段

### 0~2h：定義系統邊界與面試敘事
- 產出：一頁架構責任圖。
- 重點：GitLab 負責准入治理，Jenkins 負責交付執行，Kubernetes 與 Helm 負責標準化交付，Prometheus 與 ELK 負責觀測閉環。
- 驗證：能清楚口述每一層的責任邊界。

### 2~4h：定義 MVP 驗收與回滾規則
- 產出：6 條 MVP 驗收標準。
- 重點：先定義成功條件，再開始實作。
- 驗證：能說明何時阻擋部署、何時觸發 rollback。

## 4~50h：後續執行表

| 區塊 | 時間 | 任務 | 產出 | 完成標準 |
|---|---|---|---|---|
| 03 | 4~6h | 容器化基線 | Dockerfile、.dockerignore | 可 build 與 run |
| 04 | 6~8h | 本機編排與健康檢查 | docker-compose.yml、health check 路徑 | 可重啟恢復，能解釋 readiness / liveness |
| 05 | 8~10h | 最小測試與品質入口 | tests/ 骨架、lint/test 指令 | 本機可一鍵執行基本檢查 |
| 06 | 10~12h | Kubernetes 配置基礎 | Namespace、ConfigMap、Secret 模板 | 可套用且配置分離 |
| 07 | 12~14h | Deployment 與 Service | Deployment、Service | Pod Ready、Service 可連通 |
| 08 | 14~16h | 探針與資源治理 | livenessProbe、readinessProbe、requests、limits | 故障可自癒且受資源限制 |
| 09 | 16~18h | 持久化策略 | PVC 與資料掛載策略 | Pod 重建後資料仍可用 |
| 10 | 18~20h | YAML 版回滾演練 | 升級與降版紀錄 | 5 分鐘內回復穩定版 |
| 11 | 20~22h | Helm 初始化 | Helm chart 骨架 | helm lint 通過 |
| 12 | 22~24h | 核心模板化 | Deployment、Service、ConfigMap、Secret 模板 | helm template 正確 |
| 13 | 24~26h | 多環境 values | values-dev、values-staging、values-prod | 不改模板即可切環境 |
| 14 | 26~28h | Helm 升級與回滾 | release 歷史與 rollback 紀錄 | revision 可查、回滾可操作 |
| 15 | 28~30h | GitLab CI 治理閘道 | validate、quality、security 三段式 gate | 任一 gate fail 不得部署 |
| 16 | 30~32h | GitLab 安全強化 | 依賴掃描與基礎 policy | 高風險問題會被阻擋 |
| 17 | 32~34h | GitLab 觸發 Jenkins | Webhook / trigger 流程 | gate 全綠才觸發 Jenkins |
| 18 | 34~36h | Jenkins 前半管線 | checkout、build、test、scan | 前半段穩定且有 log 證據 |
| 19 | 36~38h | Jenkins 後半管線 | push、deploy、smoke test | 部署成功且健康檢查通過 |
| 20 | 38~40h | Jenkins 自動回滾 | deploy fail rollback 邏輯 | 失敗時可自動回滾並留存紀錄 |
| 21 | 40~42h | Prometheus 指標接入 | metrics 抓取配置與核心儀表 | 核心指標可在儀表板看到 |
| 22 | 42~44h | ELK 日誌接入 | log pipeline 與 Kibana 查詢模板 | 可依 request_id/provider/error_type 查詢 |
| 23 | 44~46h | Alertmanager 告警 | 3 條告警規則 | 可手動觸發與恢復 |
| 24 | 46~48h | 故障演練與復盤 | docs/incident_drills.md（3 個 incident 劇本與復盤模板） | 每個事件都有根因與修正方案 |
| 25 | 48~50h | 面試彩排 | docs/interview_rehearsal.md（15 分鐘 demo 腳本、10 題追問答案） | 可連續演示完整流程並回答 trade-off |

## 每區塊固定節奏

1. 前 20 分鐘：先講原理，理解為什麼要做。
2. 中間 70 分鐘：完成當格最小可用交付。
3. 後 30 分鐘：做驗證、記錄證據、整理面試說法。

## 建議使用方式

- 如果你要一天完成 10 小時，就切成 5 個區塊。
- 如果你要一天完成 6 小時，就切成 3 個區塊，兩天多半會跨段。
- 任何時候都先守住驗收標準，再擴充進階功能。
