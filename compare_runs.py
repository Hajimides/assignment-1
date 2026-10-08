"""比较三组搭配词结果的异同，并补查重点人物在不显著时的统计值。"""

import hashlib
import json
from pathlib import Path

import pandas as pd
from qhchina.analytics.collocations import find_collocates
from qhchina.helpers import load_stopwords


TARGET_WORD = "祥子"
MAX_P = 0.05
RUNS = [
    ("window5", {"method": "window", "horizon": 5}),
    ("window10", {"method": "window", "horizon": 10}),
    ("sentence", {"method": "sentence"}),
]
# 即使在某组或全部三组中不显著，也要列出统计值的词。
# “刘四爷”被 jieba 切成“刘”和“四爷”，因此查“四爷”；“强子”是“二强子”的碎片。
FOCUS_WORDS = [
    "心中", "先生", "言语", "高妈", "老程",
    "虎妞", "小福子", "骆驼", "阮明", "四爷", "强子",
]
# 被停用词表或 min_word_length=2 排除、但对解释有用的词。
# 另做一次不过滤停用词、允许单字词的检查：“说”“他”是停用词，“车”是单字词；
# “钱”“买车”“拉车”用来检查小说的核心主题是否异常集中在“祥子”周围。
UNFILTERED_WORDS = ["说", "他", "车", "钱", "买车", "拉车"]
# 按“窗口 5 / 窗口 10 / 句子模式”是否显著来分组。
PATTERNS = {
    (True, True, True): "三组共有",
    (True, True, False): "仅窗口模式显著",
    (False, True, True): "窗口 5 不显著，范围扩大后显著",
    (True, False, True): "窗口 5 与句子模式显著",
    (True, False, False): "仅窗口 5 显著",
    (False, True, False): "仅窗口 10 显著",
    (False, False, True): "仅句子模式显著",
    (False, False, False): "三组都不显著",
}


def main():
    project_dir = Path(__file__).resolve().parent
    input_path = project_dir / "sentences.txt"
    output_dir = project_dir / "output"
    settings_path = output_dir / "analysis_settings.json"

    # 1. 确认 sentences.txt 与三份 CSV 来自同一次分析。
    if not settings_path.is_file():
        raise FileNotFoundError("找不到 analysis_settings.json，请先运行 collocates.py。")
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != settings["sentences_sha256"]:
        raise ValueError("sentences.txt 与现有 CSV 不一致，请重新运行 collocates.py。")

    sentences = [
        line.split()
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # 2. 用与 collocates.py 相同的设置重跑，但不设 max_p，
    # 这样不显著的词也有 p 值可查。显著与否仍按 p < 0.05 判断。
    stopwords = set(load_stopwords())
    filters = {
        "stopwords": sorted(stopwords),
        "min_word_length": 2,
    }
    full_results = {}
    unfiltered_rows = []
    for run_name, run_settings in RUNS:
        results = find_collocates(
            sentences=sentences,
            target_words=TARGET_WORD,
            filters=filters,
            alternative="greater",
            return_type="dataframe",
            max_sentence_length=None,
            **run_settings,
        )
        full_results[run_name] = results.set_index("collocate")

        # 重跑结果中的显著词应与已保存的 CSV 完全一致。
        saved = pd.read_csv(
            output_dir / f"collocates_xiangzi_{run_name}.csv", encoding="utf-8-sig"
        )
        rerun_significant = set(results.loc[results["p_value"] < MAX_P, "collocate"])
        if rerun_significant != set(saved["collocate"]):
            raise ValueError(f"{run_name} 的重跑结果与已保存的 CSV 不一致。")

        # 不过滤停用词、允许单字词，只取 UNFILTERED_WORDS 中的词。
        # 这些数字只用于解释，不属于正式的搭配词结果。
        unfiltered = find_collocates(
            sentences=sentences,
            target_words=TARGET_WORD,
            filters={"min_word_length": 1},
            alternative="greater",
            return_type="dataframe",
            max_sentence_length=None,
            **run_settings,
        ).set_index("collocate")
        for word in UNFILTERED_WORDS:
            row = {"run": run_name, "collocate": word}
            if word in unfiltered.index:
                result = unfiltered.loc[word]
                row.update({
                    "obs_local": int(result["obs_local"]),
                    "exp_local": round(float(result["exp_local"]), 3),
                    "ratio_local": round(float(result["ratio_local"]), 3),
                    "obs_global": int(result["obs_global"]),
                    "p_value": float(result["p_value"]),
                    "significant": bool(result["p_value"] < MAX_P),
                })
            else:
                row.update({"obs_local": 0, "significant": False})
            row["is_stopword"] = word in stopwords
            row["is_single_char"] = len(word) == 1
            unfiltered_rows.append(row)

    # 3. 汇总：任何一组显著的词，加上需要补查的重点词。
    significant = {
        run_name: set(results.index[results["p_value"] < MAX_P])
        for run_name, results in full_results.items()
    }
    words = set().union(*significant.values()) | set(FOCUS_WORDS)

    rows = []
    for word in words:
        row = {"collocate": word}
        flags = []
        for run_name, results in full_results.items():
            if word in results.index:
                result = results.loc[word]
                row[f"{run_name}_obs"] = int(result["obs_local"])
                row[f"{run_name}_ratio"] = round(float(result["ratio_local"]), 3)
                row[f"{run_name}_p"] = float(result["p_value"])
            else:
                # 该词从未进入这组设置的语境，没有共现。
                row[f"{run_name}_obs"] = 0
                row[f"{run_name}_ratio"] = None
                row[f"{run_name}_p"] = None
            flags.append(word in significant[run_name])
            row[f"{run_name}_sig"] = flags[-1]
        row["pattern"] = PATTERNS[tuple(flags)]
        rows.append(row)

    pattern_order = {label: i for i, label in enumerate(PATTERNS.values())}
    comparison = pd.DataFrame(rows)
    comparison = comparison.sort_values(
        by=["pattern", "sentence_obs", "window10_obs"],
        key=lambda column: column.map(pattern_order) if column.name == "pattern" else -column,
    ).reset_index(drop=True)
    comparison = comparison[
        ["collocate", "pattern"]
        + [col for run_name, _ in RUNS for col in (
            f"{run_name}_obs", f"{run_name}_ratio", f"{run_name}_p", f"{run_name}_sig"
        )]
    ]

    output_path = output_dir / "run_comparison.csv"
    comparison.to_csv(output_path, index=False, encoding="utf-8-sig")

    # 4. 在终端打印摘要。注意：窗口模式数词的位置，句子模式数句子，
    # 不同模式的 obs 不能直接比较，只能比较是否显著。
    print("各组显著搭配词数：")
    for run_name, words_in_run in significant.items():
        print(f"  {run_name}: {len(words_in_run)}")

    print("\n按显著模式分组（括号内为句子模式共现句数）：")
    for label, group in comparison.groupby("pattern", sort=False):
        listed = "、".join(
            f"{word}({obs})" for word, obs in zip(group["collocate"], group["sentence_obs"])
        )
        print(f"\n[{label}] {len(group)} 个")
        print(f"  {listed}")

    print("\n重点词（obs / ratio / p，✓ 表示 p < 0.05）：")
    focus = comparison.set_index("collocate").loc[FOCUS_WORDS]
    for word, row in focus.iterrows():
        cells = []
        for run_name, _ in RUNS:
            ratio = row[f"{run_name}_ratio"]
            p_value = row[f"{run_name}_p"]
            mark = "✓" if row[f"{run_name}_sig"] else "✗"
            if pd.isna(p_value):
                cells.append(f"{run_name} 0 {mark}")
            else:
                cells.append(f"{run_name} {row[f'{run_name}_obs']} / {ratio:.2f} / {p_value:.3f} {mark}")
        print(f"  {word}：" + "；".join(cells))

    unfiltered_path = output_dir / "unfiltered_check.csv"
    unfiltered_table = pd.DataFrame(unfiltered_rows)
    # 没有共现的词其余列为空；用可空整数类型，避免次数显示为 350.0。
    unfiltered_table["obs_global"] = unfiltered_table["obs_global"].astype("Int64")
    unfiltered_table.to_csv(unfiltered_path, index=False, encoding="utf-8-sig")

    print("\n不过滤停用词与单字词时的补查（obs / exp / ratio / p）：")
    for word, group in unfiltered_table.groupby("collocate", sort=False):
        notes = []
        if group["is_stopword"].iloc[0]:
            notes.append("停用词")
        if group["is_single_char"].iloc[0]:
            notes.append("单字词")
        cells = []
        for _, row in group.iterrows():
            mark = "✓" if row["significant"] else "✗"
            if pd.isna(row.get("p_value")):
                cells.append(f"{row['run']} 0 {mark}")
            else:
                cells.append(
                    f"{row['run']} {row['obs_local']} / {row['exp_local']:.1f} / "
                    f"{row['ratio_local']:.2f} / {row['p_value']:.3f} {mark}"
                )
        label = f"（{'、'.join(notes)}）" if notes else ""
        print(f"  {word}{label}：" + "；".join(cells))

    print(f"\n已保存：{output_path}")
    print(f"已保存：{unfiltered_path}")


if __name__ == "__main__":
    main()
