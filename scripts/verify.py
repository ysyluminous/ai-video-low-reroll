#!/usr/bin/env python3
"""校验本 skill 是否完整覆盖原文。

用法:
    python scripts/verify.py --source /path/to/原文.md

--source 也可以用环境变量 SOURCE_MD 指定。
不给 source 时只做本地一致性检查（文件是否齐全、提示词是否齐全）。

退出码 0 = 通过，1 = 有缺失。
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROMPT_BLOCKS = [
    ("导演开场", "你当这支短片的总导演，全程负责", "7. 不充值，不买额度。接口返回欠费就停，把已有的片段先粗剪给我看。"),
    ("故事", "我想做的片子：", "如果配歌，转折对副歌，关键动作对重拍。"),
    ("故事审核", "这是一支短片的逐镜头故事。你是第一次看", "每条写：镜头、问题、建议改法。没把握的写“可能”。最后写“通过”或“不通过”。"),
    ("分镜", "把定稿的故事写成分镜表。", "最后用代码给每个镜头画一张 1920×1080 的色块草图"),
    ("首尾帧检查", "首尾帧画完了，帮我按下面这些逐条检查", "把首帧和尾帧叠在一起看有没有错位"),
    ("提交前审核", "你是审核，只读不改。", "最后只写“通过”或“不通过”。不通过就逐条列出要改什么。"),
    ("后期", "用代码做后期：", "做完抽查切点前后 3 帧。"),
    ("成片复核", "这是成片：[文件]。你第一次看", "每条写：时间、帧号、问题。分“硬伤”和“小问题”。"),
    ("四线程", "这支片子用四线程来做。", "不充值，不买额度。欠费就停，先把已有的片段粗剪出来给我看。"),
]

KEY_FACTS = [
    "片长", "画幅", "总预算", "配乐和字幕",
    "ARK_API_KEY", "codex exec --skip-git-repo-check", "generated_images",
    "doubao-seedance-2-5-260628", "doubao-seedance-2-0-mini-260615", "¥1.5/秒", "¥0.5/秒",
    "片段式", "连贯式", "够得着吗", "一句话说清", "身体会往后缩", "分 3 段", "副歌", "重拍",
    "参考片", "逐帧", "38%", "62%", "1920×1080", "色块草图", "转黑白",
    "设定图", "正面、侧面、几个表情", "纹身在左手臂",
    "16:9", "裁一块", "贴回原图", "一两个主要动作", "云里闪一下白光", "13%", "帽檐",
    "720p", "1080p", "测试片", "3 倍", "音效",
    "BT.601", "BT.709", "无损", "lanczos", "轻微锐化", "半帧快门", "8–16", "切点前后 3 帧", "原曲上测",
    "主做", "监督", "代理", "欠费", "粗剪", "新版本存新文件", "先怀疑提示词", "不推不拉不摇",
]

REQUIRED_FILES = [
    "SKILL.md", "README.md", "LICENSE", "CHANGELOG.md",
    "test-prompts.json", "results.tsv",
    "references/prompts.md", "references/tool-setup.md", "references/model-failure-table.md",
]

QUOTES = str.maketrans({"“": "", "”": "", "\"": "", "「": "", "」": ""})


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text.translate(QUOTES))


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def check_files() -> list[str]:
    return [p for p in REQUIRED_FILES if not os.path.exists(os.path.join(ROOT, p))]


def check_prompts(source_text: str, prompts_text: str) -> list[str]:
    lines = source_text.splitlines()
    pn = norm(prompts_text)
    problems = []
    for name, start, end in PROMPT_BLOCKS:
        si = next((i for i, l in enumerate(lines) if start in l), None)
        if si is None:
            problems.append(f"[{name}] 原文里找不到起始句")
            continue
        ei = next((i for i in range(si, len(lines)) if end in lines[i]), None)
        if ei is None:
            problems.append(f"[{name}] 原文里找不到结束句")
            continue
        for line in lines[si:ei + 1]:
            n = norm(line)
            if len(n) < 6:
                continue
            if n not in pn:
                problems.append(f"[{name}] 缺行: {line.strip()[:40]}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.environ.get("SOURCE_MD", ""), help="原文 .md 路径")
    args = ap.parse_args()

    missing = check_files()
    print(f"files: {len(REQUIRED_FILES) - len(missing)}/{len(REQUIRED_FILES)}")
    for m in missing:
        print(f"  MISSING {m}")

    corpus = "\n".join(
        read(os.path.join(ROOT, p))
        for p in REQUIRED_FILES
        if os.path.exists(os.path.join(ROOT, p))
    )

    miss_facts = [k for k in KEY_FACTS if k not in corpus]
    print(f"key facts: {len(KEY_FACTS) - len(miss_facts)}/{len(KEY_FACTS)}")
    for k in miss_facts:
        print(f"  MISSING {k}")

    if not args.source:
        print("prompts: skipped (no --source / SOURCE_MD)")
        return 1 if (missing or miss_facts) else 0

    if not os.path.exists(args.source):
        print(f"source not found: {args.source}")
        return 1

    problems = check_prompts(read(args.source), read(os.path.join(ROOT, "references/prompts.md")))
    bad_blocks = {re.match(r"\[(.+?)\]", p).group(1) for p in problems if p.startswith("[")}
    print(f"prompt blocks: {len(PROMPT_BLOCKS) - len(bad_blocks)}/{len(PROMPT_BLOCKS)}")
    for p in problems:
        print(f"  {p}")

    ok = not (missing or miss_facts or problems)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
