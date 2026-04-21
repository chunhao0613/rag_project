# Docker

## 3W

### What

Docker 是把「應用 + 依賴 + 啟動方式」封裝成不可變工件（Image）的容器化平台。

### Why

- 解決環境不一致：同一個 image 在不同機器行為一致。
- 解決依賴污染：服務彼此隔離，不互相汙染系統套件。
- 解決交付不可追溯：每次發布對應唯一 image tag。

### Where/How

- Where：本機開發、CI build、部署前交付工件層。
- How：透過 Dockerfile 定義 build 配方，再用 `docker build` 產生 image，用 `docker run` 啟動 container。

---

## 核心名詞與關聯

| 名詞 | 你要先理解什麼 | 和誰關聯 |
|---|---|---|
| Dockerfile | 建置腳本，不是執行腳本 | image, layer cache |
| Base image | image 的起點 | 決定 OS 與 runtime |
| Build context | Docker build 可見範圍 | 影響 COPY 與 cache |
| Image | 不可變工件（唯讀層） | container, registry |
| Container | image 的執行態 | namespace, cgroups |
| Layer | 每條 Dockerfile 指令形成一層 | cache 命中率 |
| Registry | image 儲存與分發中心 | CI/CD push/pull |
| Namespace | 進程/網路/掛載隔離 | container 安全邊界 |
| Cgroups | CPU/Memory 資源限制 | 避免 noisy neighbor |

### 協作關係（簡化）

1. Dockerfile 定義 build 步驟。
2. Docker build 產生 image layers。
3. Image push 到 registry。
4. 執行環境 pull image -> run 成 container。
5. container 由 namespace 隔離、由 cgroups 限制資源。

### 這兩個詞怎麼理解

- `Base image`：Dockerfile 的起點。
  - 用途：決定你從哪個作業系統與 runtime 開始。
  - 何時要用：任何 Dockerfile 都要先選 base image，常見如 `python:3.11-slim`。
- `Build context`：`docker build` 時 Docker 可以讀到的檔案範圍。
  - 用途：決定 `COPY` 能拿到哪些檔案。
  - 何時要用：當你遇到檔案複製失敗、cache 不如預期時，先檢查 context 是否正確。
- 從零寫法：先選 base image，再確認 build context 裡真的有你要 COPY 的檔案。

---

## 手把手實作

## 範例程式

```python
# app.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
```

### 這段程式怎麼寫

- 用途：提供最小健康檢查端點，讓 Docker `HEALTHCHECK` 或外部監控確認服務真的有回應。
- 吃的參數：`/healthz` 這個路由不吃輸入參數；回傳固定 JSON。
- 何時要用：任何要被容器化的 HTTP 服務，都應該先有一個穩定、低依賴的健康端點。
- 從零寫法：先把這個端點定義成「只檢查程序活著」，不要一開始就把 DB、外部 API 依賴全塞進來。

```text
requirements.txt
fastapi==0.115.0
uvicorn==0.30.6
```

### 這份依賴清單怎麼寫

- 用途：固定應用執行與啟動伺服器所需的 Python 套件版本。
- 吃的參數：每一行是套件與版本鎖定，常見格式是 `package==version`。
- 何時要用：當你想讓本機、CI、容器內環境一致時，核心依賴就要鎖版本。
- 從零寫法：先列出框架與啟動器，再補測試與工具套件；正式環境通常要明確版本，不要只寫範圍。

## Dockerfile 範例

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 這段 Dockerfile 怎麼寫

- `FROM python:3.11-slim`：選基底映像，決定容器內的作業系統與 Python 版本。
  - 用途：建立可重現的執行環境。
  - 何時要用：所有 Python 服務都需要一個固定基底，尤其正式環境。
- `WORKDIR /app`：設定容器內工作目錄。
  - 用途：後續 `COPY`、`RUN`、`CMD` 都以這個目錄為基準。
  - 何時要用：只要你的應用不是直接放在根目錄，就應該先設定。
- `COPY requirements.txt ./` + `RUN pip install ...`：先裝依賴。
  - 用途：把變動較少的依賴層放在前面，提升 layer cache 命中率。
  - 何時要用：當你的需求是「程式改了，但依賴沒改」時，這樣可以加快 build。
- `COPY . ./`：把應用程式碼放進容器。
  - 用途：把真正變動的程式碼加入 image。
  - 何時要用：依賴安裝後再拷貝程式碼，避免每次改檔都重裝套件。
- `EXPOSE 8000`：宣告容器預期會用的 port。
  - 用途：文件化用途，不是實際開 port。
  - 何時要用：服務對外提供 HTTP/gRPC 時，讓人一眼看出對應埠號。
- `HEALTHCHECK ... CMD curl ...`：定期檢查服務是否存活。
  - 用途：讓 Docker 可以標記 healthy/unhealthy。
  - 何時要用：只要服務不是純背景批次任務，就應該加健康檢查。
- `CMD ["uvicorn", ...]`：容器預設啟動命令。
  - 用途：定義 container 起來後執行什麼。
  - 何時要用：當 image 的主要角色就是跑這個服務時。

### 從零寫 Dockerfile 的順序

1. 先選 base image。
2. 再設定工作目錄。
3. 先 copy 依賴檔並安裝。
4. 再 copy 程式碼。
5. 補健康檢查。
6. 定義啟動命令。

## 指令教學（參數解釋）

```bash
docker build -t note-fastapi:0.1 .
```

- `build`：依 Dockerfile 建 image。
- `-t note-fastapi:0.1`：設定 `name:tag`，方便後續辨識與部署。
- `.`：build context（目前目錄），代表 Docker 可以讀取的檔案範圍。
- 何時用：程式或依賴有變更時；只要 image 內容要更新就會重建。
- 從零寫法：先確認 build context 裡有 Dockerfile 與應用碼，再用明確 tag 建立可追蹤版本。

```bash
docker run --rm -p 8000:8000 --name note-fastapi note-fastapi:0.1
```

- `run`：從 image 啟動 container。
- `--rm`：停止後自動刪除容器，適合一次性測試。
- `-p 8000:8000`：主機 port 對應容器 port，前者是外部存取，後者是容器內監聽埠。
- `--name`：容器名稱，方便 logs/exec/stop。
- 何時用：本機驗證 image 是否能正常啟動時。
- 從零寫法：先決定對外 port，再確認應用內部監聽 port 一致，最後補上容器名稱方便除錯。

```bash
docker ps
```

- 看正在運行的容器。
- 何時用：想快速確認 container 有沒有起來、port 是否正常映射時。

```bash
docker logs note-fastapi --tail 50
```

- 看最近 50 行日誌，排查啟動問題。
- `--tail 50`：只看最後 50 行，避免 log 太長。
- 何時用：容器啟動失敗、healthcheck 失敗、或應用直接 crash 時。

```bash
docker exec -it note-fastapi /bin/sh
```

- 進容器做臨時檢查（檔案、環境變數、連線）。
- `-it`：互動式終端，適合手動排查。
- 何時用：你要檢查容器內檔案是否存在、環境變數是否正確、或想直接測連線時。
- 從零寫法：只有在真的需要看容器內部狀態時才進去，平常不要依賴 `exec` 當成正常流程。

---

## 常見錯誤與排查

1. `ModuleNotFoundError`：通常是 `COPY` 路徑或 `WORKDIR` 錯。
2. container 一直 unhealthy：health endpoint 路徑錯，或服務尚未啟動就檢查。
3. image 太大：未使用 slim base、未清理 apt cache。

---

## 面試回答角度

- 你為什麼用 Docker：
  - 我把交付單位標準化成不可變 image，降低環境差異，讓 CI/CD 可追溯。
- 你如何控制風險：
  - healthcheck + 固定 tag + 嚴格 base image，並以最小工具集降低攻擊面。

---

## 參考文件

- [Docker Practice（中文）](https://yeasy.gitbook.io/docker_practice)
- [Docker 官方文件：Dockerfile reference（英文）](https://docs.docker.com/reference/dockerfile/)
- [Docker 官方文件：Get started with Docker（英文）](https://docs.docker.com/get-started/)
