### 3W:
* #### What: 
	* 一個容器化平台，類似於輕量虛擬機，不建操作系統只建環境
* #### Why: 
	* 解決本機能跑，到其他機就不能跑的問題 -> 確保環境一致性
	* 防止一台中毒/出錯就整個系統報廢的問題 -> 容器間相互隔離
	* 在一台機器上跑出隔離與環境一致，又不像傳統虛擬機依樣笨重
* #### Where: 
	* 微服務架構(大系統拆n小容器)
	* CI/CD整合(測試拉起一個乾淨容器，用後即焚)
	* 本地端開發(用 `docker-compose` 一鍵啟動 Database + Redis + Backend)
* #### How: 
	* 透過
	![[sre.drawio.png]]
	圖（一）Docker內部協作與定位圖
### 核心名詞定位與功能意義

| **關鍵名詞**       | **在架構圖中的定位**                      | **核心作用 / 在你專案中的體現**      | **解釋**                                                             |
| -------------- | --------------------------------- | ------------------------ | ------------------------------------------------------------------ |
| **Dockerfile** | **Client 端 (圖層 1)**               | **環境配置腳本**。<br><br>      | 「Dockerfile 將環境建置過程版本化、可追溯。」                                       |
| Image          | **Registry (圖層 4) 或 Daemon 本地快取** | **不可變藍圖**。               | 「Image 是唯讀的，保證環境部署的一致性，是 CI/CD 交付的最小標準單位。」                         |
| Container      | **宿主機底層 (圖層 6)**                  | **執行實體**。                | 「Container 本質上是一個被隔離的 Linux Process (行程)。」                         |
| UnionFS        | **宿主機核心機制 (圖層 5)**                | **分層與快取 (Layer Cache)**。 | 「使用Docker中的Layer技術，將Build Image的過程加速(從快取讀取)」                       |
| Namespace      | **宿主機核心機制 (圖層 5)**                | **資源隔離 (Isolation)**。    | 「Namespace 騙過了容器，讓它以為自己擁有完整的系統（獨立的 PID、Network、Mount），實現了安全的隔離環境。」 |
| Cgroups        | **宿主機核心機制 (圖層 5)**                | **資源限制 (Limitation)**。   | 「Cgroups 防止了單一容器發生 OOM 或 CPU 飆高時，把整台宿主機拖垮的風險（防範吵鬧的鄰居效應）。」          |
### 如何開始？
* #### 根據圖一中的流程開始建立第一個容器 
	1.目錄看起來會像這樣：
```
my-rag-project/
├── app.py              # 主程式 (例如使用 FastAPI)
├── requirements.txt    # 相依套件清單
└── Dockerfile          # Docker 打包配方
```
	
	2.撰寫Dockerfile文件:
```Dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
		
COPY . .
		
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
	CMD curl -fsS http://localhost:8000/_stcore/health || exit 1
		
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port", "8000", "--server.address", "0.0.0.0"]
```
> **解釋**:
> 	FROM python:3.11-slim
> 	- 結構 (`FROM <Image>:<Image's Tag>`)
> 	> 	Image與Tag均需要去DockerHub尋找
> 	- 用來指定基底映像檔(Base Image)
> 
> 	WORKDIR /app
> 	- 結構 (`WORKDIR <path> `)：
> 	- 相當於Linux中的cd + mkdir
> 	-  讓Docker從此行開始之後的指令都在Container中的 /app 資料夾執行(若不存在則自動建立)
> 	
> 	COPY requirements.txt ./
> 	- 將檔案從宿主機複製進Container中
> 	- 結構 (`COPY <來源> <目的地>`)：
> 		- 來源：電腦上當前目錄的相依套件清單(requirements.txt)。
> 		- 目的地：複製進容器裡的哪，" .或是./ "就是當前目錄(因WORKDIR所以會到/app)。
> 	
> 	RUN pip install --no-cache-dir -r requirements.txt
> 	- 建置(build)階段執行的linux指令。用RUN來完成平時終端下的指令(如apt-get install或pip install)
> 	
> 	EXPOSE 8000
> 	- 宣告/文件說明，用來告訴未來使用此image的人，此容器預設跑在8000 port，但須注意這只是標記，實際上的指派還是透過docker run或docker-compose。
> 	
> 	CMD [...]
> 	- 預設啟動指令 : 當image被啟動成container時，預設要執行的指令。
> 	- 使用["A", "B", "C"] :這是Exec格式，會直接呼叫而不經過linux的shell
docker ps
docker stop `<ID>
docker restart `<ID>
docker rm `<ID>
docker exec -it `<ID> /bin/bash


### 容器化後的多關聯容器定義、啟動與管理
- #### 建立Docker-compose.yml

```YAML
version: '3.8' # 指定 Compose 檔案格式版本

services: # 開始定義你要跑的各個服務 (容器)

  # 服務一：你的 RAG API 後端
  api:
    build: .                 # 告訴 Compose 去當前目錄找 Dockerfile 現場建置
    container_name: rag_api  # 啟動後的容器名稱
    ports:
      - "8000:8000"          # 對外開放的 port
    environment:             # 設定環境變數 (例如資料庫連線字串)
      - REDIS_URL=redis://redis_cache:6379/0
    depends_on:              # 定義啟動順序，確保 Redis 先起來，API 才起來
      - redis_cache
    volumes:                 # 掛載本機目錄 (適合開發期，程式碼改了不用重 build)
      - .:/app

  # 服務二：Redis 快取伺服器
  redis_cache:
    image: redis:7-alpine    # 不需要自己 build，直接從 Docker Hub 拉取官方現成 Image
    container_name: rag_redis
    ports:
      - "6379:6379"          # 如果你想從本機連進去檢查資料，才需要這行
    # 注意：在 Compose 內部網路中，API 容器可以直接透過 `redis_cache` 這個名字連到這裡，不需要知道實體 IP。
```