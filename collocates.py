"""读取 sentences.txt，对“祥子”运行三组搭配词分析并保存 CSV。"""

import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from qhchina.analytics.collocations import find_collocates
from qhchina.helpers import load_stopwords


TARGET_WORD = "祥子"
MAX_P = 0.05


def main():
    # 1. 读取分词结果：每一行变成一个词语列表。
    project_dir = Path(__file__).resolve().parent
    input_path = project_dir / "sentences.txt"
    output_dir = project_dir / "output"

    if not input_path.is_file():
        raise FileNotFoundError("找不到 sentences.txt，请先运行 segment.py。")

    sentences = [
        line.split()
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    target_count = sum(words.count(TARGET_WORD) for words in sentences)
    if target_count == 0:
        raise ValueError(f"分词结果中找不到完整目标词“{TARGET_WORD}”，请检查分词。")

    # 2. 使用 qhchina 自带的简体中文停用词表。
    # 停用词在结果表中被过滤，原来的词语位置仍保留，避免改变窗口距离。
    stopwords = load_stopwords()
    filters = {
        "stopwords": sorted(stopwords),
        "min_word_length": 2,
        "max_p": MAX_P,
    }

    # 3. 定义三组设置；窗口大小表示目标词左右各多少个词。
    runs = [
        ("window5", {"method": "window", "horizon": 5}),
        ("window10", {"method": "window", "horizon": 10}),
        ("sentence", {"method": "sentence"}),
    ]
    output_dir.mkdir(exist_ok=True)

    print(f"输入文件：{input_path}")
    print(f"句子数：{len(sentences)}")
    print(f"目标词：{TARGET_WORD}，词频：{target_count}")
    print(f"停用词数：{len(stopwords)}")
    print("检验方向：greater（寻找比独立假设下预期更常共现的词）")

    run_summaries = []
    # 4. 分别运行分析，按实际共现次数降序排列，并保存全部结果。
    for run_name, settings in runs:
        results = find_collocates(
            sentences=sentences,
            target_words=TARGET_WORD,
            filters=filters,
            alternative="greater",
            sort_by="obs_local",
            ascending=False,
            return_type="dataframe",
            max_sentence_length=None,  # 使用完整句子，不自动截断长句。
            **settings,
        )

        if results.empty:
            # 没有显著结果时，仍保存带列名的 CSV，方便之后读取。
            results = results.reindex(columns=[
                "target", "collocate", "exp_local", "obs_local",
                "ratio_local", "obs_global", "p_value",
            ])
        else:
            # qhchina 的 max_p 包含边界值；这里严格保留 p < 0.05。
            results = results.loc[results["p_value"] < MAX_P].reset_index(drop=True)

        output_path = output_dir / f"collocates_xiangzi_{run_name}.csv"
        results.to_csv(output_path, index=False, encoding="utf-8-sig")
        run_summaries.append({
            "name": run_name,
            **settings,
            "csv": output_path.name,
            "rows": len(results),
            "csv_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        })

        print(f"\n设置：{settings}")
        print(f"符合条件的搭配词：{len(results)} 个")
        print(f"已保存：{output_path}")
        if results.empty:
            print("这组设置没有符合条件的搭配词。")
        else:
            print("前 20 行（CSV 中保存的是全部结果）：")
            print(results.head(20).to_string(index=False))

    # 保存实际设置和输入哈希，结果网页据此显示参数并检查数据是否一致。
    metadata = {
        "target_word": TARGET_WORD,
        "sentence_count": len(sentences),
        "token_count": sum(map(len, sentences)),
        "target_token_count": target_count,
        "sentences_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "alternative": "greater",
        "correction": None,
        "min_word_length": 2,
        "max_p": MAX_P,
        "strict_p_less_than_threshold": True,
        "stopword_language": "zh_sim",
        "stopword_count": len(stopwords),
        "sort_by": "obs_local",
        "ascending": False,
        "max_sentence_length": None,
        "qhchina_version": version("qhchina"),
        "runs": run_summaries,
    }
    (output_dir / "analysis_settings.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
