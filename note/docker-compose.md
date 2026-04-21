# Docker Compose

## 3W

### What

Docker Compose 是多容器本機編排工具，透過 `docker-compose.yml` 宣告服務。

### Why

- 一鍵啟動多服務（App + DB + Cache）。
- 本機重現接近線上依賴拓撲。
- 快速驗證服務間連線與啟動順序。

### Where/How

- Where：開發環境、功能驗證、排障重現。
- How：在 `services` 裡定義每個容器的 image/build、ports、volumes、env、healthcheck。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| service | 一個可管理容器單位 | depends_on, network |
| build | 由 Dockerfile 建 image | 來源是目前目錄或指定 context |
| container_name | 容器實體名稱 | 方便 logs/exec/stop |
| ports | 主機與容器埠映射 | 對外連線入口 |
| volume | 資料持久化與檔案同步 | app data, db data |
| network | 服務間 DNS 與通訊 | service-name 直連 |
| depends_on | 啟動順序控制 | 不等於健康保證 |
| healthcheck | 容器健康訊號 | compose ps 狀態 |

### 協作關係

- Compose 先建 network。
- 依序啟動 services。
- 服務用 service name 互相存取（不用寫 IP）。

### 這些詞怎麼理解

- `build`：告訴 Compose 去哪裡找 Dockerfile 並建 image。
  - 用途：本機測試時直接用現有原始碼建出服務。
  - 何時要用：你還沒把 image push 到 registry，或本機改完想立即測試時。
- `container_name`：容器的固定名稱。
  - 用途：讓你在 `docker logs`、`docker exec`、`docker stop` 時更容易指定。
  - 何時要用：本機單人開發、排障時很方便；多人共用環境時則要避免名稱衝突。
- `ports`：主機與容器的 port 映射。
  - 用途：把容器內服務暴露到本機。
  - 何時要用：你需要從瀏覽器或本機工具直接訪問服務時。
- `service name DNS`：Compose 內網會把 service 名稱當作 DNS 名稱。
  - 用途：容器彼此用 `redis_cache`、`api` 直接互連。
  - 何時要用：只要是同一個 compose network 裡的服務互訪就會用到。
- 從零寫法：先決定哪個服務要 build、哪個服務直接用 image，再決定是否需要對外 ports 與內部 service name 連線。

---

## 手把手實作

```yaml
services:
  api:
    build: .
    container_name: rag_api
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis_cache:6379/0
    depends_on:
      - redis_cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 5s
      retries: 3

  redis_cache:
    image: redis:7-alpine
    container_name: rag_redis
    ports:
      - "6379:6379"
```

### 這段 Compose 怎麼寫

- `services`：Compose 的核心區塊，用來定義要啟動哪些容器。
- `api`：主應用服務。
  - `build: .`：代表 image 由目前目錄 build 出來。
  - `ports: "8000:8000"`：把主機 8000 對到容器 8000。
  - `environment`：把依賴服務的連線字串注入容器。
  - `depends_on`：只控制啟動順序，不保證對方已健康。
  - `healthcheck`：確認 API 真正能回應。
- `redis_cache`：依賴服務。
  - `image: redis:7-alpine`：直接用既有 image。
  - `ports`：若只供內網服務使用，其實可以不公開到主機。
- 從零寫法：先列出「主服務」與「依賴服務」，再補 network、env、volume、healthcheck。

## 指令與參數

```bash
docker compose up -d --build
```

- `up`：啟動（若不存在則建立）。
- `-d`：背景執行。
- `--build`：強制重建 image（程式剛改完常用）。
- 何時用：程式碼、Dockerfile、依賴有變更時，想一次啟動整個拓撲。

```bash
docker compose ps
```

- 顯示每個 service 狀態（包含 healthy/unhealthy）。
- 何時用：你想確認服務是否都已經起來，或某個 service 是否卡在 unhealthy。

```bash
docker compose logs -f api
```

- 即時追蹤 `api` 日誌。
- `-f`：follow 新增輸出。
- 何時用：啟動卡住、健康檢查失敗、或你要看初始化輸出時。

```bash
docker compose down
```

- 停掉並移除容器與 network。
- 何時用：你要清理本機測試環境、重建整個拓撲時。

### 何時用

- 本機端想快速完整驗證「服務 + 依賴」。
- CI 本地 smoke 測試前置。

---

## 常見錯誤與排查

1. `depends_on` 誤解：它不保證對方服務已可用。
2. 端口衝突：`Bind for 0.0.0.0:8000 failed`。
3. 服務連線失敗：環境變數用錯 service name。

排查步驟：

```bash
docker compose ps
docker compose logs api --tail 100
docker compose exec api env | grep REDIS_URL
```

---

## 面試回答角度

- 為什麼先 Compose 再 K8s：
  - Compose 讓我低成本先驗證依賴與啟動路徑，縮小問題面後再上 K8s。

---

## 參考文件

- [Docker Practice：Compose 基礎（中文）](https://yeasy.gitbook.io/docker_practice/compose)
- [Docker Compose 官方文件（英文）](https://docs.docker.com/compose/)
- [Compose file reference（英文）](https://docs.docker.com/compose/compose-file/)
