# Jenkins（交付執行與自動回復）

## 3W

### What

Jenkins 負責從已通過治理 gate 的程式碼，執行 build/test/scan/deploy/smoke/rollback。

### Why

- 把交付執行鏈路自動化。
- 保留可審計證據（log、artifact、revision）。

### Where/How

- Where：`Jenkinsfile`。
- How：前半（工件可信）+ 後半（部署可用）+ 失敗自動回復。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| stage | 流程節點 | 可分段追蹤失敗 |
| artifact | 工件與證據 | image/tag/rollback history |
| smoke test | 部署後最小驗證 | 成功定義的一部分 |
| rollback | 失敗回復 | 依 revision 恢復 |
| post failure | 失敗鉤子 | 自動執行止血流程 |
| Groovy | Jenkinsfile 腳本語言 | 控制 stage/steps/post |
| env | 環境變數物件 | 存放 job 與部署參數 |
| credentials | 憑證管理 | 安全存取 registry / k8s |

### 協作關係

- GitLab 通過後觸發 Jenkins。
- Jenkins build image -> deploy to K8s via Helm。
- 失敗時 Jenkins 觸發 rollback 並保留證據。

### Jenkinsfile 基本語法怎麼看

- `Groovy`：Jenkins Pipeline 主要語言。
  - 用途：撰寫 stage、條件式、變數與函式。
  - 何時要用：只要你要把流程寫進 Jenkinsfile，就一定會碰到。
- `env.VAR`：讀寫 pipeline 環境變數。
  - 用途：存放 image tag、namespace、release 名稱等參數。
  - 何時要用：當某些值要在不同 stage 間共享時。
- `credentials(...)`：取用 Jenkins 管理的密鑰。
  - 用途：避免把 token 寫死在程式中。
  - 何時要用：觸發外部系統、登入 registry、連 k8s API 時。
- `sh`：在 agent shell 執行命令。
  - 用途：跑 docker、helm、kubectl、測試指令。
  - 何時要用：當你需要真正呼叫系統工具時。
- 從零寫法：先定義 `env` 與 credentials，再寫 stage；不要把所有字串都硬編在 shell 命令裡。

---

## 手把手實作

## 前半（可信工件）

```groovy
stage('Checkout') {
  steps {
    checkout scm
  }
}

stage('Build') {
  steps {
    sh 'docker build -t "${LOCAL_IMAGE}" .'
  }
}

stage('Test') {
  steps {
    sh 'make check'
  }
}
```

### 這段 Jenkins Pipeline 怎麼寫

- `stage('Checkout')`：把原始碼拉進工作區。
  - 用途：建立這次 pipeline 的工作內容。
  - 何時要用：幾乎每條 pipeline 都需要先 checkout。
- `checkout scm`：使用 Jenkins 內建 SCM 定義。
  - 用途：從當前分支或 PR 來源抓程式碼。
  - 何時要用：Git repository 是 pipeline 的輸入來源時。
- `stage('Build')`：產生 image。
  - `docker build -t "${LOCAL_IMAGE}" .`：把目前 workspace build 成 image。
  - 何時要用：你要在部署前先產生可追溯工件時。
- `artifact`：build/test/deploy 後留下來的輸出。
  - 用途：保存 jar、image tag、測試報告、部署紀錄。
  - 何時要用：你想讓失敗可以回溯、審計可以查證時。
- `stage('Test')`：跑品質閘道。
  - `make check`：統一執行 lint + test。
  - 何時要用：在 build 後、deploy 前確認程式沒壞時。
- 從零寫法：先把流程拆成 checkout / build / test / deploy 四段，再把每段的失敗原因分開處理。

## 後半（可用交付）

```groovy
stage('Deploy') {
  steps {
    sh '''
      helm upgrade --install "${HELM_RELEASE}" "${HELM_CHART}" \
        -n "${HELM_NAMESPACE}" -f "${HELM_VALUES}"
    '''
  }
}

stage('Smoke Test') {
  steps {
    sh 'kubectl -n "${HELM_NAMESPACE}" rollout status deployment/"${HELM_RELEASE}" --timeout="${ROLLOUT_TIMEOUT}"'
  }
}
```

### 這段部署與驗證怎麼寫

- `stage('Deploy')`：執行 Helm 發布。
  - `helm upgrade --install`：同一指令處理首次安裝與後續升級。
  - 何時要用：你想讓 pipeline 不用分支判斷是否已存在 release。
- `stage('Smoke Test')`：部署後驗證。
  - `kubectl rollout status`：確認 Deployment 真正完成 rollout。
  - 何時要用：部署成功不等於服務可用，必須再補驗證。
- 從零寫法：把部署與驗證拆開，不要讓「有套上 YAML」誤當成「服務可用」。

## 回滾（失敗鉤子）

```groovy
post {
  failure {
    sh 'helm rollback "${HELM_RELEASE}" "${PREV_REV}" -n "${HELM_NAMESPACE}" --wait --timeout="${ROLLOUT_TIMEOUT}"'
  }
}
```

### 這段回滾怎麼寫

- `post { failure { ... } }`：只在 pipeline 失敗時執行。
- `helm rollback`：回到上一個穩定 revision。
- 何時要用：當部署後驗證失敗、或健康指標惡化時。
- 從零寫法：先確定你有記錄前一版可用 revision，再設計自動回滾。

## 指令與參數重點

- `helm upgrade --install`：安裝或升級統一入口。
- `kubectl rollout status --timeout`：等待部署完成，不無限阻塞。
- `helm rollback <release> <revision>`：回到指定穩定版。

---

## 常見錯誤與排查

1. rollout 成功但服務不可用：漏做 smoke test。
2. rollback 失敗：未記錄前一個穩定 revision。
3. 證據不足：未 archive 重要檔案。

---

## 面試回答角度

- 你如何定義部署成功：
  - 不只 rollout success，還要 smoke test 和關鍵指標不惡化；否則觸發回滾。

---

## 參考文件

- [Jenkins 官方文件（英文）](https://www.jenkins.io/doc/)
- [Jenkins Pipeline 官方文件（英文）](https://www.jenkins.io/doc/book/pipeline/)
- [Jenkinsfile 語法參考（英文）](https://www.jenkins.io/doc/book/pipeline/jenkinsfile/)
