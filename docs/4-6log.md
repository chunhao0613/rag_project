# Block 03：4~6h 容器化基線學習紀錄

## 目標
讓應用具備一致、可重現的執行單位，建立 SRE 後續工作的共同基礎。

## 核心原理（20 分鐘理解）

### 為什麼要容器化？
1. **不可變工件**：同一個映像穿越建置、測試、部署、上線，避免「在我的機器上跑得好好的」的問題。
2. **環境一致性**：開發機、CI 環境、K8s 都跑同一個映像，消除環境差異 bug。
3. **可追溯性**：映像可以貼 label（digest、version）與 git commit 對應，故障時知道跑的是哪一版。
4. **隔離與限制**：容器提供 namespace 隔離與 cgroup 資源限制，降低相互干擾。

### 容器化的關鍵決策點
- **Base image**：python:3.11-slim（輕量化、包含 python）vs python:3.11（含更多工具，更大）。
- **Layer cache**：每一層 RUN、COPY 都可被快取，改一行程式碼不必重新 pip install。
- **Health check**：容器活著不等於服務可用，HEALTHCHECK 讓平台知道何時才算真正就緒。
- **.dockerignore**：不把 venv、.env、快取資料、舊向量庫傳進 build context，縮短建置時間與映像大小。

## 具體做法（70 分鐘實作）

### 1. 建立 Dockerfile

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

RUN mkdir -p data/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/_stcore/health || exit 1

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port", "8000", "--server.address", "0.0.0.0"]
```

**每一行的意義**

| 行 | 說明 |
|---|---|
| `FROM python:3.11-slim` | 選擇輕量基底，包含 Python 3.11，約 110MB |
| `ENV PYTHONDONTWRITEBYTECODE=1` | 不產生 .pyc，減少層疊 |
| `ENV PYTHONUNBUFFERED=1` | Streamlit 日誌即時輸出，不緩衝 |
| `ENV PIP_NO_CACHE_DIR=1` | pip 快取不進映像，減小尺寸 |
| `WORKDIR /app` | 設定工作目錄 |
| `RUN apt-get update ... && apt-get install curl` | 安裝 curl（用於 HEALTHCHECK），並清理快取 |
| `COPY requirements.txt ./` | 先複製依賴，利用 layer cache |
| `RUN pip install -r requirements.txt` | 安裝依賴（這層最容易在開發時被快取，加快迭代） |
| `COPY . ./` | 複製整個專案代碼 |
| `RUN mkdir -p data/uploads` | 預先建立應用需要的目錄 |
| `EXPOSE 8000` | 告知平台這個容器在 8000 port 監聽 |
| `HEALTHCHECK` | 每 30 秒檢查一次 `/health` 路徑，失敗 3 次才標記為 unhealthy |
| `CMD` | 啟動指令，與 startup.sh 內容相同 |

### 2. 建立 .dockerignore

```
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.mypy_cache/
.ruff_cache/
.git/
.gitignore
.DS_Store
.env
.venv/
venv/
env/
build/
dist/
*.egg-info/
data/uploads/
data/chroma_db/
data/chroma_db_cohere/
data/chroma_db_hf/
**/node_modules/
docs/
```

**為什麼要排除這些？**

| 排除項 | 理由 |
|---|---|
| `__pycache__/`, `*.pyc` 等 | 編譯快取，進映像只浪費空間 |
| `.env` | 機密資訊不進映像，應該用環境變數或 K8s secrets 注入 |
| `data/` 目錄 | chroma_db 通常很大，uploads 是應用運行時產生的，不應固化進映像 |
| `.git/` | git 歷史不需進容器，使用 .dockerignore 時自動排除 |

## 驗證（30 分鐘檢查）

### Step 1：本機建置
```bash
docker build -t rag-project-sre-mvp:local .
```

**預期輸出**
```
[+] Building 135.8s (12/13)
 => [1/7] FROM python:3.11-slim@sha256:...  3.9s
 => [3/7] RUN apt-get update ...             5.6s
 => [5/7] RUN pip install -r requirements.txt   72.1s
 => [6/7] COPY . ./                          0.5s
 => [7/7] RUN mkdir -p data/uploads           0.4s
 => exporting to image                       48.7s
 => => unpacking to docker.io/library/rag-project-sre-mvp:local  6.5s
```

**建置時間分析**
- 第一次建置：~140s（pip install 最長）
- 第二次建置（只改代碼）：~5s（layer cache 命中）
- 映像大小：約 1.2GB（包含 streamlit、langchain、torch 等重量級套件）

### Step 2：驗證映像存在
```bash
docker image inspect rag-project-sre-mvp:local --format '{{.Id}}'
```

**預期輸出**
```
sha256:7b700dbad2a4b16a4c399e2a4ab6e73e603fa1248fe771a0ee5f30206e106582
```

### Step 3：未來驗證（需要搭配 6~8h docker-compose）
```bash
docker run -p 8000:8000 -v $(pwd)/data:/app/data rag-project-sre-mvp:local
```

**預期應用啟動**
- 容器日誌顯示 Streamlit 綁定 0.0.0.0:8000
- Health check 每 30 秒執行一次，成功則顯示 healthy

## 面試敘事與關鍵概念

### 一句話總結
> 我用 Dockerfile 把 RAG 應用封裝成一個不可變的容器映像，確保開發、測試、上線環境完全一致。.dockerignore 避免把快取與敏感資料進映像，layer cache 優化每次迭代的建置時間，HEALTHCHECK 讓平台能正確判定服務健康狀態。

### 面試官可能的追問

**Q1：為什麼選 python:3.11-slim 而不是 ubuntu + python？**  
A：slim 已含 Python，節省 layer 與 build 時間；ubuntu 會帶很多不需要的工具（如編譯器、man pages），導致映像肥大。只有需要 C 編譯環境時，才考慮用 -dev 標籤，並在後期 multi-stage build 去掉它們。

**Q2：.dockerignore 和 .gitignore 有什麼差別？**  
A：.gitignore 控制版版本控制，.dockerignore 控制構建上下文（build context）。即使 .gitignore 排除了 .env，如果沒有 .dockerignore 排除也會進映像。兩者應該配合。

**Q3：為什麼 HEALTHCHECK 用 curl http://localhost:8000/_stcore/health？**  
A：Streamlit 提供了內建的健康檢查端點 `_stcore/health`，200 表示服務可用。我沒有改應用程式碼，直接善用 Streamlit 的機制。後面如果要自定義健康檢查（如檢查 Chroma 可達），可代替成應用層的 /health 路由。

**Q4：Layer cache 怎麼優化迭代速度？**  
A：把 COPY requirements.txt 放在 COPY . 之前，讓 pip 那一層單獨被快取。開發時只改程式碼，不改依賴，Docker 會直接用快取層，skip pip install，從 140s 降到 5s。

**Q5：映像 1.2GB 太大，怎麼辦？**  
A：可嘗試 multi-stage build（build stage + runtime stage）或用更輕量的基底（Alpine），但會犧牲相容性（Alpine 缺某些 C 庫）。對 SRE MVP 來說，1.2GB 還在可接受範圍，不是瓶頸。後期如果很在乎，再做優化。

## 下一步預告（6~8h）

下一個區塊會補上 `docker-compose.yml`，讓你不用手打 docker run 指令，一鍵啟動完整開發環境。並把健康檢查與容器重啟機制講清楚，區分「程序崩潰」與「依賴不可達」的故障場景。