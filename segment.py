"""将《骆驼祥子》转换为简体、分句并分词，保存为 sentences.txt。"""

import hashlib
import json
import re
from pathlib import Path

import jieba
from opencc import OpenCC


def main():
    # 以脚本所在文件夹为基准，确定输入和输出文件的位置。
    project_dir = Path(__file__).resolve().parent
    input_path = project_dir / "data" / "骆驼祥子.txt"
    output_path = project_dir / "sentences.txt"

    # 1. 读取原文。utf-8-sig 可以处理文件开头的 BOM 编码标记。
    source_bytes = input_path.read_bytes()
    text = source_bytes.decode("utf-8-sig")
    text = text.replace("\ufeff", "")  # 去掉文本内部残留的 BOM 标记。

    # 当前版本的正文从这句话开始；原始文件保留，不直接修改。
    opening = "我们所要介绍的是祥子"
    start = text.find(opening)
    if start == -1:
        raise ValueError("找不到预期的正文开头，请检查语料版本与清理规则。")
    body_lines = []
    removed_chapter_lines = 0
    removed_end_lines = 0
    for line in text[start:].splitlines():
        stripped = line.strip()
        if re.fullmatch(r"[一二三四五六七八九十]+", stripped):
            removed_chapter_lines += 1
        elif stripped == "（全书完）":
            removed_end_lines += 1
        else:
            body_lines.append(line)
    body_text = "\n".join(body_lines)

    # 2. 在分句和分词之前，先把全文转成简体。
    converter = OpenCC("t2s")
    simplified_text = converter.convert(body_text)

    # 3. 按中文句末标点切分；连续的句末标点作为一个分隔符。
    raw_sentences = [
        sentence.strip()
        for sentence in re.split(r"[。！？]+", simplified_text)
        if sentence.strip()
    ]

    # 4. 分词，去掉标点、符号和空白，再保留至少 5 个词的句子。
    # 为角色姓名设置较高的词典权重，避免被合并为“把祥子”等词。
    # 100000 是分词权重，不是小说中“祥子”的实际出现次数。
    jieba.add_word("祥子", freq=100000)
    tokenized_sentences = []
    for sentence in raw_sentences:
        words = [
            word.strip()
            for word in jieba.lcut(sentence)
            if word.strip().isalnum()
        ]
        if len(words) >= 5:
            tokenized_sentences.append(words)

    # 5. 每行保存一个句子，词与词之间用一个空格分隔。
    with output_path.open("w", encoding="utf-8") as output_file:
        for words in tokenized_sentences:
            output_file.write(" ".join(words) + "\n")

    # 显示处理规模，方便检查和之后记录到报告中。
    word_count = sum(len(words) for words in tokenized_sentences)
    target_count = sum(words.count("祥子") for words in tokenized_sentences)
    # 保存真实统计量，供结果网页和复现时使用。
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)
    stats = {
        "source_file": "data/骆驼祥子.txt",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "removed_prefix_characters": start,
        "removed_chapter_lines": removed_chapter_lines,
        "removed_end_lines": removed_end_lines,
        "simplified_characters_including_whitespace": len(simplified_text),
        "simplified_characters_without_whitespace": sum(
            not char.isspace() for char in simplified_text
        ),
        "split_sentences": len(raw_sentences),
        "retained_sentences": len(tokenized_sentences),
        "discarded_short_sentences": len(raw_sentences) - len(tokenized_sentences),
        "retained_tokens": word_count,
        "target_word": "祥子",
        "target_strings_before_short_sentence_filter": simplified_text.count("祥子"),
        "retained_target_tokens": target_count,
        "sentences_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
    }
    (output_dir / "preprocessing_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"输入文件：{input_path}")
    print(f"已去掉正文前的目录、书名和版次信息：{start} 个字符")
    print(f"已去掉章节编号行：{removed_chapter_lines} 行")
    print(f"简体文本字符数（含空白，不含 BOM）：{len(simplified_text)}")
    print(f"分句后句子数：{len(raw_sentences)}")
    print(f"保留句子数：{len(tokenized_sentences)}")
    print(f"过滤掉的短句数：{len(raw_sentences) - len(tokenized_sentences)}")
    print(f"保留词数：{word_count}")
    print(f"保留句子中“祥子”的词频：{target_count}")
    print(f"输出文件：{output_path}")


if __name__ == "__main__":
    main()
