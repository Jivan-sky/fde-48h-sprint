# 输入通道:怎么把需求文档/真实单据读进来

> Phase 0 用。判断输入形态 → 先探测目标环境有没有该工具/权限 → 选通道 → 取文 → 进采矿。
> 不在客户白名单、未安装或无权使用的工具,不得私自安装;改用客户批准替代品、人工桥或 F2。

## 判断分支

```
输入是什么?
├─ 飞书文档 URL / token → lark-cli docs +fetch   (采矿主源,文案都在 markdown 里)
├─ 飞书表格 URL / token → lark-cli drive +download → csv/xlsx
├─ 本地 .xlsx / .csv     → python openpyxl / pandas
├─ 本地 .pdf             → pdftotext (文本型) / pdfplumber (表格型)
├─ 本地 .md / .txt       → 直接 Read
└─ 只有口头              → 进 Phase 3 提问,采矿清单补「请把需求写几行」
```

## 各通道命令

### 飞书文档(采矿主源)

```bash
# 文档 → markdown(文案/细节点/「要是能…就好了」句都在 markdown 里)
lark-cli docs +fetch --doc <URL或token> --doc-format markdown --output doc.md

# 搜索文档
lark-cli docs +search --query "需求" 
```

### 飞书表格 / 文件

```bash
# 表格/文件 → 本地(csv 一步到位)
lark-cli drive +download --file-token <token> --output local.xlsx

# 多维表格 → 结构化数据
lark-cli base +data-query --app-token <token> --table-id <id> --json
```

### 本地 Excel

```bash
python -c "
import openpyxl, json
wb = openpyxl.load_workbook('local.xlsx')
for ws in wb.worksheets:
    rows = [list(r) for r in ws.iter_rows(values_only=True) if any(c is not None for c in r)]
    print(ws.title, 'rows:', len(rows))
"
```
工具:先探测目标环境是否有 `openpyxl`;没有就换客户批准的工具或人工导出。读表格重点是**表头字段**——那就是切片输入线索(采矿线索 3:数据埋点)。

### 本地 PDF

```bash
# 文本型 PDF(大部分 MCN 结算单/后台报表):一个命令
pdftotext -layout report.pdf report.txt

# 表格型 PDF(坐标密集/表格复杂):pdfplumber
python -c "
import pdfplumber
with pdfplumber.open('report.pdf') as pdf:
    for page in pdf.pages:
        for table in page.extract_tables():
            for row in table:
                print(row)
"
```
工具:先探测 `pdftotext` / `pdfplumber` 是否可用;不可用就换客户批准的 PDF 工具或人工导出,不得临时安装。

## 纪律

1. **真实单据优先**:采矿/定切片时,输入必须是真实单据(后台导出/结算单/截图),不是样例。
2. **表格读表头**:xlsx/pdf 表格的表头字段 = 数据埋点 = 切片输入线索,逐列抄进采矿笔记。
3. **文档没提到的格式**:标「文档未提及,待确认」,不脑补。
4. **编码**:读文件统一 UTF-8;Windows 下 `read_text()` 不带 encoding 会踩 GBK 坑,写脚本时显式 `encoding="utf-8"`。
5. **不导出 HAR/原始抓包**:需求文档和客户提供的已批准脱敏导出可以作为输入;网页请求只记录脱敏轮廓,不保存完整请求/响应。
6. **数据边界**:D1/D2 的样本必须经客户批准;生产数据不得落到个人设备/个人云,不得进未批准模型。
