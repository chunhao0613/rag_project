# Alertmanager

## 3W

### What

Alertmanager 接收 Prometheus 告警，做分組、抑制、路由與通知。

### Why

- 沒有治理的告警會造成告警風暴與疲勞。
- 需要告警策略與升級路徑（on-call、頻率、抑制規則）。

### Where/How

- Where：觀測平台告警層。
- How：Prometheus rule 產生 alert，Alertmanager 依 route 規則分派到通知渠道。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| route | 告警路由 | team/severity |
| group_by | 同類告警分組 | 降低噪音 |
| inhibit_rules | 抑制次級告警 | 避免重複通知 |
| receiver | 通知目的地 | Slack/Webhook/Email |
| group_wait | 首次聚合等待時間 | 降低短暫抖動 |
| group_interval | 同組後續通知間隔 | 控制通知頻率 |
| repeat_interval | 重複通知間隔 | 持續未恢復時提醒 |
| matchers | 路由條件 | 依 label 分流 |

### 協作關係

- Prometheus alert -> Alertmanager route -> receiver。
- 高優先事件可覆蓋低優先告警。

### 這些路由參數怎麼看

- `group_wait`：第一次等多久再發。
  - 用途：把短暫抖動先聚合掉。
  - 何時要用：訊號容易瞬間跳動時。
- `group_interval`：同一組告警多久可以再發一次。
  - 用途：控制通知密度。
  - 何時要用：同一個事件可能反覆觸發時。
- `repeat_interval`：同一事件持續未解決時多久重複提醒。
  - 用途：避免完全遺漏長時間未修復事件。
  - 何時要用：on-call 需要定期提醒時。
- `matchers`：根據 label 分流。
  - 用途：讓 critical 送 on-call、warning 送摘要。
  - 何時要用：你有多個通知渠道時。
- 從零寫法：先定預設 receiver，再加 critical route，最後調 group 與 repeat 參數。

---

## 手把手實作

## Alert rule 範例

```yaml
groups:
  - name: rag-alerts
    rules:
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "RAG 5xx error rate > 5%"
```

### 這段告警規則怎麼寫

- `groups`：告警規則群組。
  - 用途：把同類規則放一起管理。
  - 何時要用：當你有多個告警主題時。
- `alert: HighErrorRate`：告警名稱。
  - 用途：作為告警識別。
  - 何時要用：名稱應該能直接看懂問題類型。
- `expr`：PromQL 條件。
  - 用途：定義什麼情況觸發告警。
  - 何時要用：任何要被自動通知的異常指標都需要。
- `for: 10m`：持續多久才真正觸發。
  - 用途：避免瞬間波動造成誤報。
  - 何時要用：指標容易短暫抖動時。
- `labels.severity`：告警分級。
  - 用途：提供路由與優先級判斷。
  - 何時要用：你需要 critical / warning 分流時。
- `annotations.summary`：給人看的摘要。
  - 用途：讓收告警的人一眼看懂。
  - 何時要用：任何告警都應該帶簡明描述。
- 從零寫法：先寫出最穩定、最有業務意義的指標，再逐步加上分級與註解。

## Alertmanager route 片段

```yaml
route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 30m
  receiver: 'default'
  routes:
    - matchers:
        - severity="critical"
      receiver: 'oncall'
```

### 這段路由怎麼寫

- `route`：總路由入口。
  - 用途：定義所有告警的預設路徑。
  - 何時要用：你有多種通知對象時。
- `group_by`：群組依據。
  - 用途：把同類告警聚合。
  - 何時要用：當你不想收到同一問題的多封通知時。
- `group_wait` / `group_interval` / `repeat_interval`：控制通知節奏。
  - 用途：降低告警噪音。
  - 何時要用：正式環境幾乎一定要調。
- `receiver`：預設接收者。
  - 用途：指定預設通知目的地。
  - 何時要用：所有未命中的告警最後要有落點。
- `routes.matchers`：分流條件。
  - 用途：依 severity 或 service 分配不同通知渠道。
  - 何時要用：critical 要直接到 on-call，其他送摘要頻道時。
- 從零寫法：先設預設路由，再補 critical 路由，最後才加抑制規則。

## 參數解釋

- `group_wait`：等待同類告警聚合後再發第一封。
- `group_interval`：同組後續通知最小間隔。
- `repeat_interval`：持續未恢復時重複通知間隔。

### 這些參數怎麼調

- `group_wait` 太短：容易被短抖動洗版。
- `group_interval` 太短：同組告警會一直打擾。
- `repeat_interval` 太短：未解除前會重複通知太頻繁。
- 實務上：先從保守值開始，再依 incident 回顧調整。

---

## 常見錯誤與排查

1. 告警太多：缺少抑制與分組策略。
2. 告警太慢：`for` 太長或 route 間隔設太保守。
3. 假陽性高：閾值未配合流量基線。

---

## 面試回答角度

- 你如何降低告警疲勞：
  - 我用分組 + 抑制 + 分級路由，讓 critical 直接 on-call，低優先只進摘要頻道。

---

## 參考文件

- [Prometheus Alerting 官方文件（英文）](https://prometheus.io/docs/alerting/latest/overview/)
- [Alertmanager 官方文件（英文）](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Alertmanager Configuration（英文）](https://prometheus.io/docs/alerting/latest/configuration/)
