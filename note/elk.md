# ELK（Elasticsearch + Logstash/Fluent Bit + Kibana）

## 3W

### What

ELK 是集中式日誌方案，用於搜尋、聚合、關聯分析。

### Why

- 分散在多容器的 log 難以追查。
- 需要跨服務關聯同一請求（trace_id/request_id）。

### Where/How

- Where：容器平台、K8s 工作負載。
- How：應用輸出結構化 JSON log，collector 收集送入 Elasticsearch，Kibana 查詢視覺化。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| structured logging | JSON 格式日誌 | 可機器解析 |
| index | ES 資料分片邏輯 | lifecycle policy |
| ingest pipeline | 資料清洗與轉換 | 欄位標準化 |
| Kibana query | 查詢介面 | incident 排障 |
| collector | 日誌收集器 | Fluent Bit / Logstash |
| KQL | Kibana Query Language | 搜尋條件語法 |
| trace_id | 跨服務關聯鍵 | 串接一次請求 |

### 協作關係

- App JSON log -> collector -> Elasticsearch index -> Kibana dashboard。

### 日誌鏈路怎麼理解

- `collector`：把節點上的 log 收集起來並送往後端。
    - 用途：集中管理多 Pod、多容器的日誌。
    - 何時要用：只要日誌不想散落在每台機器或每個 Pod 裡，就需要 collector。
- `trace_id`：一次請求的關聯識別。
    - 用途：把 ingress、app、下游服務的 log 串成一條線。
    - 何時要用：你要跨服務查詢同一個 request 時。
- `KQL`：Kibana 的搜尋語法。
    - 用途：用欄位條件快速篩選 log。
    - 何時要用：你已經知道大概是哪個服務、哪個錯誤碼、哪個時間段出問題時。
- 從零寫法：先把 log 欄位設好，再決定 collector 與查詢語法，不要反過來寫。

---

## 手把手實作

## Python 結構化 log

```python
import json
import logging

logger = logging.getLogger("rag")
logger.setLevel(logging.INFO)

def log_event(level: str, message: str, trace_id: str) -> None:
    payload = {
        "level": level,
        "message": message,
        "trace_id": trace_id,
        "service": "rag-app"
    }
    logger.info(json.dumps(payload, ensure_ascii=False))
```

### 這段結構化 log 怎麼寫

- `logging.getLogger("rag")`：取得專案專屬 logger。
    - 用途：讓不同模組共用一致的輸出設定。
    - 何時要用：你不想直接用 root logger 時。
- `setLevel(logging.INFO)`：設定 log 等級。
    - 用途：決定哪些訊息會被輸出。
    - 何時要用：開發與正式環境可以有不同等級策略。
- `payload`：把要查詢的欄位先整理成 dict。
    - 用途：讓 log 可被機器解析與搜尋。
    - 何時要用：你需要 trace_id、service、level 這些欄位做關聯分析時。
- `json.dumps(..., ensure_ascii=False)`：輸出 JSON 字串。
    - 用途：保留中文與結構化格式。
    - 何時要用：你希望 ELK 能穩定解析欄位，而不是只看到純文字。
- 從零寫法：先定義你未來會查詢的欄位，再決定 log schema，不要先寫一堆文字再回頭猜欄位。

## 查詢示例（Kibana KQL）

```text
service:"rag-app" and level:"ERROR" and trace_id:"abc-123"
```

### 這段查詢怎麼寫

- 用途：用 Kibana 直接找特定服務、特定等級、特定 trace 的 log。
- 吃的參數：欄位名稱與值，遵循 KQL 語法。
- 何時要用：你已經知道大概哪個請求、哪個服務有問題，想快速縮小範圍時。
- 從零寫法：先確保 log 裡真的有這些欄位，再開始設計查詢條件。

---

## 常見錯誤與排查

1. 無法關聯：沒有統一 trace_id 欄位。
2. ES 爆量：沒有 index lifecycle，舊資料不清。
3. 日誌難讀：混合純文字與 JSON 格式。

---

## 面試回答角度

- 你如何做故障追蹤：
  - 我用 request_id/trace_id 串接 ingress、app、依賴服務 log，快速收斂故障邊界。

---

## 參考文件

- [Elastic 官方文件（英文）](https://www.elastic.co/guide/index.html)
- [Elasticsearch Reference（英文）](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana Guide（英文）](https://www.elastic.co/guide/en/kibana/current/index.html)
