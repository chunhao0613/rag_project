# GitLab CI（治理閘道）

## 3W

### What

GitLab CI 在本專案角色是「准入治理 gate」，先驗證、再允許進入交付執行。

### Why

- 把品質與安全問題前移。
- 讓不合格變更在最早階段被阻擋。

### Where/How

- Where：`.gitlab-ci.yml`。
- How：`validate -> quality -> security -> trigger` 階段化治理。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| stage | 流程分段 | 先後執行順序 |
| needs | 依賴關係 | 前段失敗即阻擋後段 |
| validate | 基礎品質 | compile + lint |
| quality | 行為品質 | 測試 |
| security | 安全品質 | 依賴/程式掃描 |
| trigger | 交付串接 | 觸發 Jenkins |
| ruff | Python 靜態檢查工具 | 快速抓語法與風格問題 |
| pip-audit | 依賴漏洞掃描工具 | 檢查已知 CVE |
| bandit | Python 安全掃描工具 | 找危險寫法 |

### 協作關係

- GitLab 負責決策（放行或阻擋）。
- Jenkins 負責執行（build/deploy/rollback）。

### 工具各自檢查什麼

- `ruff`：檢查語法、未使用 import、部分風格與高風險錯誤。
  - 何時要用：你想快速做低成本靜態檢查時。
- `pip-audit`：檢查依賴套件是否有已知漏洞。
  - 何時要用：你想把供應鏈風險擋在上游時。
- `bandit`：檢查程式碼中常見安全問題。
  - 何時要用：你要找硬編密鑰、危險 shell、危險反序列化等模式時。
- 從零寫法：先把最不費時、失敗率高的檢查放前面，再依需求加安全掃描。

---

## 手把手實作

```yaml
stages:
  - validate
  - quality
  - security
  - trigger

validate:
  stage: validate
  script:
    - python -m compileall app.py core services
    - ruff check core services tests app.py

quality:
  stage: quality
  script:
    - make test

security:
  stage: security
  script:
    - pip-audit -r requirements.txt
    - bandit -q -r core services app.py
```

### 這段 GitLab CI 怎麼寫

- `stages`：定義管線的執行順序。
- `validate`：語法與 lint 的基礎門。
  - 何時要用：所有變更都必須先過的第一關。
- `quality`：測試門。
  - 何時要用：你要確認行為沒有回歸時。
- `security`：安全門。
  - `pip-audit`：檢查 Python 套件已知漏洞。
  - `bandit`：檢查 Python 程式碼安全風險。
  - 何時要用：當你的交付需要額外安全檢查時。
- 從零寫法：先把最容易失敗且成本最低的檢查放前面，再慢慢加上安全與部署觸發。

## 指令與參數（本機模擬）

```bash
python -m compileall app.py core services
```

- 檢查語法可編譯。
- 何時用：你想把最基本的語法錯誤先攔掉時。

```bash
ruff check core services tests app.py
```

- 快速靜態檢查。
- 何時用：你要在 CI 內做快速、低成本的品質檢查時。

```bash
make test
```

- 跑測試集。
- 何時用：當功能行為是你是否放行的主要依據時。

### 何時用

- 每次 merge request。
- 每次進主分支前。

---

## 常見錯誤與排查

1. stage 都綠但仍壞：漏掉 smoke 或部署後驗證。
2. security 太吵：先定高風險阻擋，再逐步擴規則。

---

## 面試回答角度

- 你的 GitLab CI 價值是什麼：
  - 它是治理層，不是部署層；主要價值是阻擋高風險變更進入交付管線。

---

## 參考文件

- [GitLab CI/CD 官方文件（英文）](https://docs.gitlab.com/ci/)
- [GitLab CI/CD pipelines（英文）](https://docs.gitlab.com/ci/pipelines/)
- [GitLab CI YAML reference（英文）](https://docs.gitlab.com/ci/yaml/)
