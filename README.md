# lecture-answer-first_group16_speckit

## 課堂學習單搶答加分師生互動系統

開發方針：SpecKit

組員：jacky0407、EricC430

## 協作規章

專案管理、GitHub 版本管理及 Claude + Spec Kit 開發流程請參閱[協作規章](docs/PROJECT_WORKFLOW.md)。

## 開發環境與擴充約定

環境建立、lint／型別／測試指令、啟動方式，以及 002～005 擴充共用檔案（`main.py`、`teacher.html`／`student.html`、`js/<能力>.js`）的約定，請參閱[開發指南](docs/DEVELOPMENT.md)。

快速開始（Windows，Python 3.11 以上）：

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
# 只有專案路徑含中文時才需要下一行（Python 3.13 以上也不需要），原因見開發指南
Set-Content .venv\Lib\site-packages\_editable_impl_lecture_quiz.pth "../../../src" -Encoding ascii
.venv\Scripts\python -m lecture_quiz
```
