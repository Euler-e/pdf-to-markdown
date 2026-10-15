# 扫描教材转 Markdown

原书 `input/大学物理学力学、电磁学(第三版).pdf` 保持不变。仅完成十页样本验证，未经授权不转换全书。

## 已发布环境运行

```bash
cd /workspace/pdf-to-markdown
/workspace/pdf-env/venv/bin/python scripts/convert.py --pages 14,20,21,29,30,40,80,150,260,350 --batch-size 2
```

`--pages 30-40,80` 支持一基 PDF 实际页码；`--output` 指定独立结果目录；`--env` 指定依赖/模型根目录；`--force` 重做已完成页。每页 JSON 先写 processing，完成后原子写入 complete；重启自动跳过 complete，重试失败及中断页。区域异常写入每页 errors，汇总至 `output/reports/errors.json`。批次连续执行，每页均落盘。

## 重建环境

CPU 环境使用两个 Python 3.11 虚拟环境，避免 RapidLayout 的 NumPy 2 与 OCR 的 NumPy 1 冲突：

```bash
python3 -m venv /workspace/pdf-env/venv
/workspace/pdf-env/venv/bin/pip install -r scripts/requirements.txt
python3 -m venv /workspace/pdf-env/layout-venv
/workspace/pdf-env/layout-venv/bin/pip install -r scripts/layout-requirements.lock
/workspace/pdf-env/venv/bin/python scripts/download_layout_model.py
/workspace/pdf-env/venv/bin/python scripts/download_latex_models.py
```

下载脚本使用官方发布地址并校验 SHA-256；现有模型可离线复用，不使用 MinerU。模型不提交到 Git。RapidOCR 默认模型随安装包提供。模型下载脚本默认目录 `/workspace/pdf-env`，迁移路径时需同步调整或保留该目录。

## 文档与引用

入口 `output/sample/README.md`；逐页 Markdown、区域 JSON、版面框图及处理状态在 `pages/`；全页图与所有区域原图在 `assets/`；按 PDF 原有书签组织的章节合并在 `chapters/`。非连续样本不补写缺页。原书完整目录保存在 `toc.json`，PDF 页码与印刷页码分开保存在 `page-map.json`。关键词索引定位至区域锚点。建议先搜索文字、再按页和区域回看原图。

引用格式：书名、章节、印刷页码（经核对）、PDF 第 N 页、区域 `pNNNN-bNNN`。区域 JSON 同时给出像素坐标和 PDF 点坐标。

所有独立公式均保存原图与 LaTeX 候选，默认待复核；识别清单见 `output/reports/formula-review.json`。正文区域原图覆盖行内公式，行内公式尚未单独检测和转换，不得将其普通 OCR 字符当成可靠数学表达。表格保存图片与 OCR 文本，未重建单元格。阅读顺序使用版面框纵向排序，复杂双栏仍需检查。识别文本不做语言润色或推测补全。质量报告记录实际限制。

人工核对的印刷页码存入样本 `annotations.json`（仅元数据，OCR 原文不改）。修改后运行 `/workspace/pdf-env/venv/bin/python scripts/rebuild.py` 重新生成章节、页码及索引，不触发识别。`scripts/validate_output.py` 检查文件链接、区域溯源、中文检索和源 PDF 哈希；`scripts/verify_resume.py` 实际重跑并检查完成页被跳过、截图未变。
