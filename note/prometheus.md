# Prometheus

## 3W

### What

Prometheus 是以時間序列為核心的監控系統，透過 pull 模式抓取 metrics。

### Why

- 只看 log 無法快速量化趨勢。
- 需要可計算的 SLI/SLO 指標（延遲、錯誤率、吞吐量）。

### Where/How

- Where：K8s 叢集與服務層。
- How：服務暴露 `/metrics`，Prometheus 定期 scrape，PromQL 做查詢與告警規則。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| metric | 指標資料點 | label 維度 |
| scrape | 抓取週期 | job/target |
| label | 維度標籤 | 聚合與過濾 |
| PromQL | 查詢語言 | dashboard/alert |
| rule | 記錄/告警規則 | Alertmanager |
| Counter | 累加型指標 | 只增不減 |
| Gauge | 即時型指標 | 可上下變動 |
| Histogram | 分布型指標 | buckets / quantile |
| Cardinality | 唯一 label 組合數 | 影響查詢效能 |

### 協作關係

- App exporter -> Prometheus scrape -> rule 觸發 -> Alertmanager 通知。

### 指標類型怎麼選

- `Counter`：只會增加的數值。
  - 用途：請求數、錯誤數、事件發生次數。
  - 何時要用：只想看累積量或速率時。
- `Gauge`：可上下變動的即時數值。
  - 用途：佇列長度、目前處理中的任務數、記憶體使用量。
  - 何時要用：你想看「現在是多少」而不是「累積多少」時。
- `Histogram`：觀察分布與分位數。
  - 用途：延遲、payload size、向量檢索時間。
  - 何時要用：需要 p95/p99 或區間分布時。
- `cardinality`：label 組合太多會拖慢查詢與記憶體。
  - 用途：提醒不要把 user_id、request_id 直接當 label。
  - 何時要注意：任何高流量系統都要管控。
- 從零寫法：先問自己這個值是「累加、即時、分布」哪一種，再選對 metric 類型。

---

## 手把手實作

## Python 暴露 metrics

```python
from prometheus_client import Counter, Histogram, start_http_server

REQUEST_COUNT = Counter('rag_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('rag_request_latency_seconds', 'Request latency')

start_http_server(8001)
```

### 這段 metrics 程式怎麼寫

- `Counter(...)`：累加型指標。
  - 用途：記錄請求數、錯誤數、事件次數。
  - 吃的參數：metric 名稱、說明文字。
  - 何時要用：當數值只會增加、不需要回退時。
- `Histogram(...)`：分布型指標。
  - 用途：觀察延遲分布、大小分布。
  - 吃的參數：名稱、說明，必要時還能加 bucket。
  - 何時要用：你想看 p95/p99 這類延遲分位數時。
- `bucket`：Histogram 的區間切點。
  - 用途：把樣本分到不同區間。
  - 何時要用：你需要知道延遲落在哪些範圍時。
- `start_http_server(8001)`：開啟 metrics HTTP server。
  - 用途：讓 Prometheus 可以抓取 `/metrics`。
  - 吃的參數：監聽 port。
  - 何時要用：你的應用本身不方便直接把 metrics 和主服務混在一起時。
- 從零寫法：先決定你要量的是「數量」還是「分布」，再選 Counter 或 Histogram。

## scrape 設定片段

```yaml
scrape_configs:
  - job_name: 'rag-app'
    static_configs:
      - targets: ['rag-app:8001']
```

### 這段 scrape 設定怎麼寫

- `job_name`：這組 target 的名字。
  - 用途：在 Prometheus 內辨識不同抓取任務。
  - 何時要用：每個服務群組都應該有獨立 job 名稱。
- `static_configs.targets`：固定 target 清單。
  - 用途：指定要抓哪個 host:port。
  - 何時要用：目標少且固定時最簡單；若是動態叢集就要改成 service discovery。
- 從零寫法：先弄清楚 metrics 是哪個 port 再寫 targets，不要把主服務 port 和 metrics port 混掉。

## PromQL 範例

```promql
sum(rate(rag_requests_total[5m]))
```

- 5 分鐘內平均每秒速率。
- 何時用：你想看服務吞吐量趨勢時。
- 從零寫法：先用 `rate()` 把 Counter 變成速率，再用 `sum()` 聚合多個 instance。

```promql
histogram_quantile(0.95, sum(rate(rag_request_latency_seconds_bucket[5m])) by (le))
```

- 計算 p95 延遲。
- 何時用：你需要 SLA / SLO 常看的分位數延遲時。
- 從零寫法：先用 `rate()` 算 bucket 速率，再依 `le` 聚合，最後用 `histogram_quantile()` 算分位數。

---

## 常見錯誤與排查

1. 指標未出現：/metrics 未暴露或 target 無法連通。
2. label 爆炸：把 user_id 當 label，造成高 cardinality。
3. 查詢不穩：窗口太短導致抖動。

---

## 面試回答角度

- 你怎麼挑指標：
  - 先從 RED（Rate, Errors, Duration）建最小監控，再按業務風險加指標。

---

## 參考文件

- [Prometheus 官方文件（英文）](https://prometheus.io/docs/introduction/overview/)
- [Prometheus 查詢語言 PromQL（英文）](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Prometheus client_python（英文）](https://github.com/prometheus/client_python)
