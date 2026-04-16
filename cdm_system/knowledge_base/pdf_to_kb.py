"""
PDF 知识库预处理脚本
用途：将《中国2型糖尿病防治指南（2024版）》PDF 转换为适合 RAG 的文本分块文件
运行方式：
    cd cdm_system/knowledge_base
    python pdf_to_kb.py                          # 处理 raw/ 目录下的所有 PDF
    python pdf_to_kb.py --pdf raw/指南.pdf       # 处理指定 PDF
    python pdf_to_kb.py --preview               # 仅预览，不写文件
输出：knowledge_base/doctor_guideline_chXX.txt（每章一个文件）
"""
import argparse
import re
import sys
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("请先安装 pymupdf：pip install pymupdf")
    sys.exit(1)

# ─── 配置 ───────────────────────────────────────────────────────────────────────

# 《中国2型糖尿病防治指南2024》目录结构（按页码/章节标题匹配）
# 如果实际章节标题不同，可在这里调整关键词
CHAPTER_PATTERNS = [
    r"^第[一二三四五六七八九十百]+章",           # 第X章
    r"^\d{1,2}\s+[^\d\s].{2,}",              # 数字开头的章节 如 "1  概述"
    r"^[一二三四五六七八九十]+、",              # 汉字序号 一、二、
]

# 每个分块的目标字符数（RAG 最佳实践：500-1500 字）
TARGET_CHUNK_CHARS = 800
MIN_CHUNK_CHARS = 100   # 过短的段落直接合并到上一块

OUTPUT_DIR = Path(__file__).parent


# ─── 工具函数 ──────────────────────────────────────────────────────────────────

def is_chapter_heading(text: str) -> bool:
    text = text.strip()
    if not text or len(text) > 80:
        return False
    for pat in CHAPTER_PATTERNS:
        if re.match(pat, text):
            return True
    return False


def is_section_heading(text: str) -> bool:
    """二级标题：如 "1.1 " "（一）" "（1）" 等"""
    text = text.strip()
    if not text or len(text) > 60:
        return False
    patterns = [
        r"^\d+\.\d+[\s　]",
        r"^（[一二三四五六七八九十\d]+）",
        r"^\([一二三四五六七八九十\d]+\)",
        r"^[\[【][一二三四五六七八九十\d]+[\]】]",
    ]
    for pat in patterns:
        if re.match(pat, text):
            return True
    return False


def clean_text(text: str) -> str:
    """清洗提取的文本：去除页眉页脚、乱码、连字符断行等"""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        # 跳过纯数字行（页码）
        if re.fullmatch(r"\d{1,4}", line):
            continue
        # 跳过过短无意义行
        if len(line) < 2:
            continue
        # 跳过典型页眉/页脚模式
        if re.search(r"中国糖尿病杂志|Chinese Journal|版权所有|doi:|DOI:", line):
            continue
        # 去除连字符断行（如 "治疗-\n方案" → "治疗方案"）
        if cleaned and cleaned[-1].endswith("-"):
            cleaned[-1] = cleaned[-1][:-1] + line
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """提取 PDF 每页文本，返回 [(页码, 文本), ...]"""
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        text = clean_text(text)
        if text.strip():
            pages.append((i + 1, text))
    doc.close()
    print(f"  提取了 {len(pages)} 页有效内容")
    return pages


def split_into_chunks(pages: list[tuple[int, str]]) -> list[dict]:
    """
    将页面文本按章节/段落切分为 RAG 分块。
    每个分块：{"title": str, "content": str, "pages": [int], "chunk_id": str}
    """
    chunks = []
    current_title = "概述"
    current_content = []
    current_pages = []

    def flush(title, content_lines, pages):
        text = "\n".join(content_lines).strip()
        if len(text) >= MIN_CHUNK_CHARS:
            chunks.append({
                "title": title,
                "content": text,
                "pages": pages[:],
            })

    for page_num, page_text in pages:
        lines = page_text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if is_chapter_heading(line):
                # 保存当前块
                flush(current_title, current_content, current_pages)
                current_title = line
                current_content = []
                current_pages = [page_num]
            elif is_section_heading(line):
                # 段落积累到一定大小时分块
                accumulated = "\n".join(current_content)
                if len(accumulated) >= TARGET_CHUNK_CHARS:
                    flush(current_title, current_content, current_pages)
                    current_content = []
                    current_pages = [page_num]
                current_content.append(f"\n【{line}】")
            else:
                current_content.append(line)
                if page_num not in current_pages:
                    current_pages.append(page_num)

                # 超出目标大小时，在自然段落处切割
                if len("\n".join(current_content)) >= TARGET_CHUNK_CHARS * 2:
                    flush(current_title, current_content, current_pages)
                    current_content = []
                    current_pages = [page_num]

    flush(current_title, current_content, current_pages)
    return chunks


def merge_short_chunks(chunks: list[dict]) -> list[dict]:
    """合并过短的分块到前一块"""
    merged = []
    for chunk in chunks:
        if merged and len(chunk["content"]) < MIN_CHUNK_CHARS:
            merged[-1]["content"] += "\n" + chunk["content"]
            merged[-1]["pages"] = list(set(merged[-1]["pages"] + chunk["pages"]))
        else:
            merged.append(chunk)
    return merged


def assign_audience(title: str, content: str) -> str:
    """根据内容判断受众：patient / doctor / both"""
    patient_kw = ["患者", "自我管理", "饮食", "运动", "足部护理", "家属", "提醒"]
    doctor_kw = ["指南", "诊断标准", "HbA1c目标", "用药方案", "随访频率", "筛查", "转诊",
                 "胰岛素", "SGLT2", "GLP-1", "联合用药", "并发症管理"]
    text = title + content
    has_patient = any(kw in text for kw in patient_kw)
    has_doctor = any(kw in text for kw in doctor_kw)
    if has_patient and has_doctor:
        return "both"
    if has_patient:
        return "patient"
    return "doctor"


def chunks_to_files(chunks: list[dict], prefix: str = "doctor_guideline") -> list[Path]:
    """将分块写入 txt 文件，文件名按受众自动区分"""
    # 按受众分组
    groups: dict[str, list[str]] = {"doctor": [], "patient": [], "both_doctor": [], "both_patient": []}

    for i, chunk in enumerate(chunks):
        audience = assign_audience(chunk["title"], chunk["content"])
        header = f"【{chunk['title']}】（第{chunk['pages'][0]}页）"
        paragraph = header + "\n" + chunk["content"] + "\n"

        if audience == "doctor":
            groups["doctor"].append(paragraph)
        elif audience == "patient":
            groups["patient"].append(paragraph)
        else:
            groups["both_doctor"].append(paragraph)
            groups["both_patient"].append(paragraph)

    written = []
    file_map = {
        "doctor": f"{prefix}_doctor.txt",
        "patient": f"patient_{prefix}.txt",
        "both_doctor": f"{prefix}_shared.txt",
    }

    for key, filename in file_map.items():
        paras = groups[key]
        if not paras:
            continue
        out_path = OUTPUT_DIR / filename
        out_path.write_text("\n\n".join(paras), encoding="utf-8")
        written.append(out_path)
        print(f"  写入 {out_path.name}：{len(paras)} 个段落")

    return written


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def process_pdf(pdf_path: Path, preview: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"处理 PDF：{pdf_path.name}")
    print(f"{'='*60}")

    print("步骤 1/4：提取页面文本...")
    pages = extract_pages(pdf_path)

    print("步骤 2/4：切分章节分块...")
    chunks = split_into_chunks(pages)
    chunks = merge_short_chunks(chunks)
    print(f"  切分出 {len(chunks)} 个分块")

    if preview:
        print("\n─── 预览前 5 个分块 ───")
        for i, chunk in enumerate(chunks[:5]):
            print(f"\n[分块 {i+1}] {chunk['title']} (p{chunk['pages']})")
            print(chunk["content"][:200], "...")
        print("\n─── 分块字符数分布 ───")
        sizes = [len(c["content"]) for c in chunks]
        print(f"  最小: {min(sizes)}, 最大: {max(sizes)}, 平均: {sum(sizes)//len(sizes)}")
        return

    print("步骤 3/4：判断受众并写入文件...")
    written = chunks_to_files(chunks, prefix=pdf_path.stem.replace(" ", "_")[:30])

    print("步骤 4/4：完成！")
    print(f"\n生成了 {len(written)} 个知识库文件：")
    for p in written:
        print(f"  {p}")

    print("\n下一步：重建向量索引")
    print("  cd d:\\MasInDiabetes\\cdm_system")
    print("  python manage.py init_kb --reset")


def main():
    parser = argparse.ArgumentParser(description="PDF 知识库预处理")
    parser.add_argument("--pdf", type=Path, help="指定 PDF 路径（默认处理 raw/ 目录下所有 PDF）")
    parser.add_argument("--preview", action="store_true", help="仅预览分块，不写文件")
    args = parser.parse_args()

    raw_dir = OUTPUT_DIR / "raw"

    if args.pdf:
        pdfs = [args.pdf]
    else:
        pdfs = list(raw_dir.glob("*.pdf"))
        if not pdfs:
            print(f"未在 {raw_dir} 中找到 PDF 文件")
            print("请将 PDF 放入该目录后重新运行")
            return

    for pdf_path in pdfs:
        process_pdf(pdf_path, preview=args.preview)


if __name__ == "__main__":
    main()
