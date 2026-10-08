# 《骆驼祥子》人物搭配词分析

CHI3242 Assignment 1 的数据、处理脚本与分析输出。以老舍《骆驼祥子》为语料，目标词为“祥子”，比较两种词语窗口和句子共现模式，为人物空间（character-space）的文学分析提供统计材料。短文报告由学生另行撰写。

## 语料与来源

- 作品：《骆驼祥子》；作者：老舍。
- 直接获取来源：[mcjkurz/qhchina-data 的“中文小说100强”目录](https://github.com/mcjkurz/qhchina-data/tree/main/corpora/中文小说100强)。
- [具体文本：3_骆驼祥子.txt](https://github.com/mcjkurz/qhchina-data/blob/main/corpora/中文小说100强/3_骆驼祥子.txt)。
- 保留原始 UTF-8 文件：`data/骆驼祥子.txt`；脚本不覆盖原始语料。
- 原始文件 SHA-256：`0e89a8dffdfc5811ece1987de8e7992dc115eec538507ec79d398a6cdf80188c`。

[作业要求](https://mcjkurz.github.io/teaching/courses/2026-2027/CHI3242/assignments/assignment-1/)与[第 4 周讲义](https://mcjkurz.github.io/teaching/courses/2026-2027/CHI3242/notes/week-04/)。

## 文件说明

```text
data/骆驼祥子.txt                 原始语料
segment.py                      清理、繁简转换、分句和分词
sentences.txt                   每行一个句子，词之间以空格分隔
collocates.py                   三组搭配词分析
make_report.py                  汇总 CSV，生成结果比较网页
report.md / report.pdf          短文报告（两者内容一致）
compare_runs.py                 比较三组结果的异同，补查不显著的重点人物
requirements.txt                当前运行环境的依赖版本
output/
  collocates_xiangzi_window5.csv
  collocates_xiangzi_window10.csv
  collocates_xiangzi_sentence.csv
  preprocessing_stats.json      语料处理规模和输入哈希
  analysis_settings.json        分析参数、结果行数和文件哈希
  results.html                  可离线打开的结果比较网页
  run_comparison.csv            三组显著模式对照表（由 compare_runs.py 生成）
  unfiltered_check.csv          不过滤停用词与单字词的补查（由 compare_runs.py 生成）
```

`make_report.py` 生成的是统计结果网页。作业的短文报告须另存为 `report.md` 和 `report.pdf`，两者内容一致。

## 安装与运行

本项目已在 Python 3.12.14 下运行。以下命令在仓库根目录执行，适用于 macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python segment.py
python collocates.py
python make_report.py
python compare_runs.py
```

每次重跑会更新相应生成文件。修改语料或分词规则后，应按上述顺序重跑全部脚本。`make_report.py` 会核对输入和 CSV 的哈希，避免混用不同次分析的文件。

直接用浏览器打开 `output/results.html` 即可查看。页面不依赖网络资源，支持三组表格切换、词语搜索、按列排序、前 20 项 / 全部结果切换和 CSV 下载。

如需通过本地网址浏览，可运行：

```bash
python -m http.server 8000 --bind 127.0.0.1
```

然后访问 `http://127.0.0.1:8000/output/results.html`；按 Ctrl+C 结束服务。GitHub 文件页面显示的是 HTML 源码，下载后用浏览器打开才能使用交互功能。

## 预处理规则

1. 按 UTF-8 读取文本，移除开头及内部的 BOM 标记。
2. 从“我们所要介绍的是祥子”开始保留正文，去掉此前的目录、书名和版次信息。本规则针对当前来源版本；更换语料时须调整。
3. 去掉独立成行的章节编号，共 46 行，以及末尾“（全书完）”标记。
4. 使用 OpenCC `t2s` 把正文转为简体，再按 `。！？` 切分句子。
5. 使用 jieba 分词；为“祥子”设置词典权重 `100000`，避免姓名与邻字合并。该权重不是语料中的实际词频。
6. 只保留由文字或数字组成的词，去掉标点、符号和空白；保留至少 5 个词的句子。此阶段保留单字词及停用词，以保留词语位置。

当前处理规模如下；机器可读记录见 `output/preprocessing_stats.json`：

| 指标 | 数量 |
| --- | ---: |
| 清理、转简体后的字符数，含空白 | 135,315 |
| 清理、转简体后的字符数，不含空白 | 134,344 |
| 分句后句子数 | 5,066 |
| 保留句子数 | 4,427 |
| 过滤的短句数 | 639 |
| 保留词数 | 72,970 |
| 清理后、短句筛选前“祥子”的字符串次数 | 801 |
| 保留句子中“祥子”的词频 | 736 |

其中“字符数”包含标点，不等同于纯汉字数量。短句过滤会排除部分姓名出现；分词和标点规则也是影响结果的方法选择。

## 搭配词分析

使用 `qhchina.analytics.collocations.find_collocates`，qhchina 版本为 0.2.7。

| 运行 | 参数 | 显著搭配词数 |
| --- | --- | ---: |
| 窗口 5 | `method="window", horizon=5` | 94 |
| 窗口 10 | `method="window", horizon=10` | 110 |
| 句子模式 | `method="sentence"`，不传入 horizon | 114 |

共同设置：

- `target_words="祥子"`。
- 用 `load_stopwords()` 加载简体中文停用词表，共 806 词，通过 `filters["stopwords"]` 从结果中排除。停用词仍占据原有窗口位置。
- `filters["min_word_length"]=2`、`filters["max_p"]=0.05`；另严格排除 `p_value >= 0.05` 的行。
- Fisher 精确检验方向为 `alternative="greater"`，用于寻找高于独立假设预期的共现。本次使用原始 p 值，未做多重检验校正。
- 按 `obs_local` 降序排列。CSV 保存全部结果；终端只显示每组前 20 行。
- `max_sentence_length=None`，保留完整句子。

`horizon=5` 表示左右各 5 个分词后的词，窗口限定在句子内。句子模式把同一句作为共现单位，同一句中重复出现不会增加该句的计数。因此，两种模式的频数单位不同。

## 三组结果比较

`compare_runs.py` 用与 `collocates.py` 相同的设置重跑三组分析，但不设 `max_p`，以便查看不显著词的 p 值；显著与否仍按 `p < 0.05` 判断，并先核对重跑的显著词与已保存的 CSV 完全一致。输出 `output/run_comparison.csv`，列出任一组显著的词及若干重点人物（含三组都不显著的“四爷”），按“三组共有”“仅窗口模式显著”“窗口 5 不显著，范围扩大后显著”“仅句子模式显著”等模式分组。窗口模式与句子模式的 `obs` 单位不同，只能比较是否显著，不能直接比较次数。

脚本另做一次补查：不过滤停用词、允许单字词，只取“说”“他”“车”“钱”“买车”“拉车”六个词，结果写入 `output/unfiltered_check.csv`。“说”“他”是停用词，“车”“钱”是单字词，正式结果中不会出现；这些数字只用于解释（例如小说的核心主题是否异常集中在“祥子”周围），不属于正式的搭配词结果。

## 结果列

| 列名 | 含义 |
| --- | --- |
| `target` | 目标词 |
| `collocate` | 搭配词 |
| `obs_local` | 实际局部共现计数；窗口模式统计语境内词语位置，句子模式统计共同出现的句子数 |
| `exp_local` | 按当前方法的列联表，在独立假设下的预期共现计数 |
| `ratio_local` | 实际 / 预期，即 `obs_local / exp_local` |
| `obs_global` | 全局频数；窗口模式为词频，句子模式为包含该词的句子数 |
| `p_value` | Fisher 精确检验的原始 p 值 |

统计显著性提供共现线索；它不能证明词语描述的是祥子，也不能替代原文语境核对、叙事视角分析或人物空间的文学解释。

## 提交状态

数据、脚本、三份 CSV、比较网页、三组结果对照（`compare_runs.py`）及短文报告 `report.md` / `report.pdf`（内容一致）均已提交。
