# Python 品質閘道（pytest + ruff + make）

## 3W

### What

用 `ruff`（靜態檢查）+ `pytest`（行為測試）+ `make`（統一入口）建立最小品質門。

### Why

- 壞變更不應流入 build/deploy。
- 減少人工跑命令差異。
- 提升回歸檢查可重現性。

### Where/How

- Where：本機開發、CI validate/quality stage。
- How：`make check` 一鍵執行 lint + test。

---

## 核心名詞與關聯

| 名詞 | 功能 | 關聯 |
|---|---|---|
| ruff | 快速 lint | 先擋語法與高風險錯誤 |
| pytest | 單元測試框架 | 驗證核心路徑不回歸 |
| Makefile | 命令入口 | CI 與本機共用 |
| conftest.py | pytest 共用設定 | fix import path / fixture |
| fixture | 測試共用資料/資源 | 重用 setup / teardown |

### 協作關係

- 開發者跑 `make check`。
- CI 同步跑 `make check`。
- 結果一致，避免「本機過、CI 不過」。

### ruff 錯誤代碼代表什麼

- `E9`：語法錯誤或解析失敗。
    - 用途：先擋掉無法執行的程式。
- `F63`：比較或常數相關問題。
    - 用途：避免明顯邏輯錯誤。
- `F7`：語法樹層級的問題。
    - 用途：抓出較底層的 Python 語法問題。
- `F82`：未定義名稱相關問題。
    - 用途：避免 runtime NameError。
- `fixture`：pytest 用來提供共用前置資料或資源。
    - 用途：集中建立測試資料、暫存目錄、mock 物件。
    - 何時要用：多個測試共用 setup/teardown 時。
- 從零寫法：先補核心成功路徑測試，再用 fixture 抽共用資料。

---

## 手把手實作

## 範例測試

```python
# tests/test_math_demo.py

def add(a: int, b: int) -> int:
    return a + b


def test_add() -> None:
    assert add(1, 2) == 3
```

### 這段測試怎麼寫

- `add(a: int, b: int) -> int`：最小可測函式。
    - 用途：示範怎麼把邏輯拆成可驗證單元。
    - 吃的參數：兩個整數，回傳相加結果。
    - 何時要用：當你想測試純邏輯、不要依賴外部系統時。
- `test_add()`：pytest 測試函式。
    - 用途：驗證 `add(1, 2)` 的預期結果。
    - 何時要用：每個核心邏輯都至少要有一個成功路徑測試。
- 從零寫法：先找出最不依賴外部資源的函式，寫最小輸入和最明確輸出，再慢慢擴展邊界值。

## Makefile

```makefile
lint:
	ruff check core services tests app.py

test:
	pytest -q

check: lint test
```

### 這份 Makefile 怎麼寫

- `lint`：定義 lint 任務。
    - 用途：統一靜態檢查入口。
    - 何時要用：任何要在本機與 CI 共用的檢查流程，都適合包成一個 target。
- `ruff check core services tests app.py`：指定檢查範圍。
    - 吃的參數：一串檔案/目錄路徑。
    - 何時要用：你要把檢查限制在專案程式碼，不想掃到不相關檔案時。
- `test`：定義測試任務。
    - 用途：統一執行 pytest。
    - 何時要用：測試是獨立品質閘門時。
- `check: lint test`：把兩個任務串成單一入口。
    - 用途：一個命令完成全部品質檢查。
    - 何時要用：push 前、CI 前、或教學示範時。

## pyproject.toml 重點

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E9", "F63", "F7", "F82"]
```

### 這份 pyproject 怎麼寫

- `[tool.pytest.ini_options]`：pytest 設定區。
    - `minversion`：限制 pytest 最低版本。
    - `testpaths`：告訴 pytest 去哪找測試。
    - `addopts`：預設加上的命令列參數。
- `[tool.ruff]`：ruff 全域設定。
    - `line-length`：控制單行長度。
    - 何時要用：你想統一團隊格式規範時。
- `[tool.ruff.lint]`：lint 規則集合。
    - `select`：只開你要的規則類型。
    - 何時要用：從高風險錯誤開始，再逐步擴大規則覆蓋。

## 指令與參數

```bash
make lint
```

- 跑 ruff 靜態檢查。

```bash
make test
```

- 跑 pytest。

```bash
make check
```

- 一次跑完 lint + test。
- 何時用：push 前必跑。

```bash
pytest -q
```

- `-q`：精簡輸出，CI log 更乾淨。
- 何時用：你要快速看整體品質是否過關，而不是逐條讀細節時。

---

## 常見錯誤與排查

1. 測試 import 失敗：加 `tests/conftest.py` 或調整 PYTHONPATH。
2. Lint 規則太嚴造成噪音：先開高風險規則，再逐步擴大。
3. 測試不穩定：避免依賴外部網路與時間。

---

## 面試回答角度

- 為什麼品質門先於 CI/CD：
  - 因為 CI/CD 只是傳遞變更，若無品質門，只會自動化傳遞風險。
