from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "项目工程文档"
TEMP_DIR = Path("C:/codex_project_docs_export")
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")

DOC_SOURCES = [
    (
        ROOT / "docs/codex/v1/requirements/自动循环进化编码智能体系统-requirements.md",
        OUT_DIR / "自动循环进化编码智能体系统-需求文档.doc",
        "自动循环进化编码智能体系统",
        "需求文档",
    ),
    (
        ROOT / "docs/codex/v1/designs/自动循环进化编码智能体系统-technical-design.md",
        OUT_DIR / "自动循环进化编码智能体系统-技术方案.doc",
        "自动循环进化编码智能体系统",
        "技术方案",
    ),
    (
        ROOT / "docs/codex/v1/plans/自动循环进化编码智能体系统-mvp-plan.md",
        OUT_DIR / "自动循环进化编码智能体系统-MVP实施计划.doc",
        "自动循环进化编码智能体系统",
        "MVP 实施计划",
    ),
]

PRESENTATION_SOURCE = ROOT / "docs/codex/v1/presentation/自动循环进化编码智能体系统-演讲大纲.md"
PRESENTATION_PDF = OUT_DIR / "自动循环进化编码智能体系统-演讲文档.pdf"
ASSET_DIR = OUT_DIR / "assets"


CSS = """
@page { size: A4; margin: 18mm 18mm 18mm 18mm; }
body {
  font-family: "Microsoft YaHei", "SimSun", Arial, sans-serif;
  color: #1f2933;
  line-height: 1.42;
  font-size: 10.5px;
}
.cover {
  text-align: center;
  padding: 18px 0 16px;
  border-bottom: 3px solid #1f4e79;
  margin-bottom: 16px;
}
.cover h1 {
  color: #1f4e79;
  font-size: 24px;
  margin: 0 0 7px;
  letter-spacing: 0;
}
.cover .subtitle {
  color: #5b6670;
  font-size: 13px;
}
h1 {
  color: #1f4e79;
  font-size: 17px;
  border-bottom: 1px solid #d7e3ef;
  padding-bottom: 4px;
  margin-top: 18px;
}
h2 {
  color: #2f5597;
  font-size: 13.5px;
  margin-top: 14px;
}
h3 {
  color: #374151;
  font-size: 11.5px;
  margin-top: 11px;
}
p { margin: 4px 0; }
ul, ol { margin-top: 3px; margin-bottom: 6px; }
li { margin: 2px 0; }
code {
  font-family: Consolas, "Courier New", monospace;
  color: #b23b3b;
  background: #f7f7f7;
  padding: 1px 4px;
  border-radius: 3px;
}
pre {
  background: #f6f8fa;
  border: 1px solid #d9e2ec;
  border-left: 4px solid #2f5597;
  padding: 7px 9px;
  overflow-wrap: break-word;
  white-space: pre-wrap;
  font-family: Consolas, "Courier New", monospace;
  font-size: 8.5px;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0 11px;
  font-size: 9.5px;
}
th {
  background: #d9eaf7;
  color: #1f2933;
  font-weight: 700;
}
th, td {
  border: 1px solid #aebfd0;
  padding: 4px 5px;
  vertical-align: top;
}
tr:nth-child(even) td { background: #fbfdff; }
.diagram {
  margin: 14px 0 16px;
  text-align: center;
  page-break-inside: avoid;
}
.diagram img {
  max-width: 94%;
  border: 1px solid #d7e3ef;
  box-shadow: 0 2px 8px rgba(31, 78, 121, 0.12);
}
.diagram-title {
  color: #5b6670;
  font-size: 9.5px;
  margin-top: 5px;
}
.slide {
  page-break-inside: avoid;
  border-left: 5px solid #1f4e79;
  padding-left: 14px;
}
"""


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded_rect(draw: ImageDraw.ImageDraw, box, fill, outline="#6b7f93", width=2, radius=14):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_text(draw: ImageDraw.ImageDraw, box, text: str, font, fill="#1f2933") -> None:
    lines = text.split("\n")
    line_heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
    total_h = sum(line_heights) + (len(lines) - 1) * 6
    y = box[1] + ((box[3] - box[1]) - total_h) / 2
    for line, w, h in zip(lines, widths, line_heights):
        x = box[0] + ((box[2] - box[0]) - w) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += h + 6


def arrow(draw: ImageDraw.ImageDraw, start, end, fill="#2f5597", width=3) -> None:
    draw.line([start, end], fill=fill, width=width)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        pts = [(x2, y2), (x2 - direction * 12, y2 - 7), (x2 - direction * 12, y2 + 7)]
    else:
        direction = 1 if y2 > y1 else -1
        pts = [(x2, y2), (x2 - 7, y2 - direction * 12), (x2 + 7, y2 - direction * 12)]
    draw.polygon(pts, fill=fill)


def save_architecture_diagram(path: Path) -> None:
    img = Image.new("RGB", (1200, 620), "#ffffff")
    draw = ImageDraw.Draw(img)
    title_font = load_font(30, True)
    font = load_font(20, True)
    small = load_font(16)
    draw.text((36, 28), "总体架构：控制层驱动 Agent，质量与安全双门控", font=title_font, fill="#1f4e79")
    boxes = {
        "用户任务": (60, 160, 220, 240),
        "Orchestrator\n流程控制": (300, 140, 500, 260),
        "Agent Runtime\nOMX / Codex CLI": (620, 120, 890, 240),
        "工程工作区\nWorktree / Tests": (620, 330, 890, 450),
        "Quality Gate\n质量门控": (300, 330, 500, 450),
        "Safety Policy\n安全策略": (60, 330, 220, 450),
        "Run State\n日志与报告": (970, 230, 1140, 350),
    }
    colors = ["#eaf3f8", "#d9eaf7", "#e8f5e9", "#fff3cd", "#fce4ec", "#ede7f6", "#f4f6f8"]
    for (label, box), color in zip(boxes.items(), colors):
        rounded_rect(draw, box, fill=color)
        center_text(draw, box, label, font)
    arrow(draw, (220, 200), (300, 200))
    arrow(draw, (500, 195), (620, 180))
    arrow(draw, (755, 240), (755, 330))
    arrow(draw, (620, 390), (500, 390))
    arrow(draw, (300, 390), (220, 390))
    arrow(draw, (500, 200), (970, 275))
    arrow(draw, (890, 390), (970, 310))
    draw.text((70, 505), "核心思想：Agent 负责生成，Gate 负责质量，Policy 负责边界，State 负责恢复。", font=small, fill="#5b6670")
    img.save(path)


def save_workflow_diagram(path: Path) -> None:
    img = Image.new("RGB", (1200, 520), "#ffffff")
    draw = ImageDraw.Draw(img)
    title_font = load_font(30, True)
    font = load_font(18, True)
    draw.text((36, 28), "单任务自动循环流程", font=title_font, fill="#1f4e79")
    labels = ["任务输入", "安全预检", "Agent 编码", "Hard Check", "Reviewer", "Quality Gate", "完成 / 暂停"]
    x = 55
    boxes = []
    for label in labels:
        box = (x, 180, x + 135, 255)
        boxes.append(box)
        rounded_rect(draw, box, fill="#eaf3f8")
        center_text(draw, box, label, font)
        x += 160
    for a, b in zip(boxes, boxes[1:]):
        arrow(draw, (a[2], 217), (b[0], 217))
    rounded_rect(draw, (430, 330, 625, 405), "#fff3cd")
    center_text(draw, (430, 330, 625, 405), "失败短路\nFixer 修复", font)
    arrow(draw, (535, 255), (535, 330))
    arrow(draw, (430, 368), (350, 255))
    rounded_rect(draw, (705, 330, 930, 405), "#fce4ec")
    center_text(draw, (705, 330, 930, 405), "JSON 非法 / task_id 不匹配\n最多重试 2 次", font)
    arrow(draw, (810, 255), (810, 330))
    arrow(draw, (705, 368), (695, 255))
    img.save(path)


def save_gate_diagram(path: Path) -> None:
    img = Image.new("RGB", (1200, 540), "#ffffff")
    draw = ImageDraw.Draw(img)
    title_font = load_font(30, True)
    font = load_font(19, True)
    small = load_font(16)
    draw.text((36, 28), "质量门控：硬性检查优先，综合评分放行", font=title_font, fill="#1f4e79")
    items = [
        ("测试通过\n40分", "#d9ead3"),
        ("Lint 通过\n10分", "#d9ead3"),
        ("类型检查\n10分", "#d9ead3"),
        ("Review 通过\n20分", "#d9eaf7"),
        ("置信度\n10分", "#d9eaf7"),
        ("Diff 风险\n10分", "#fff3cd"),
    ]
    x = 70
    for label, color in items:
        box = (x, 155, x + 150, 245)
        rounded_rect(draw, box, color)
        center_text(draw, box, label, font)
        x += 180
    rounded_rect(draw, (365, 340, 835, 430), "#ede7f6", width=3)
    center_text(draw, (365, 340, 835, 430), "通过条件：总分 >= 80 + 无阻断项 + 未触发安全策略", font)
    for start_x in [145, 325, 505, 685, 865, 1045]:
        arrow(draw, (start_x, 245), (600, 340))
    draw.text((70, 470), "Hard Check 失败时直接短路，不调用 Reviewer，避免浪费 Token 和无意义审查。", font=small, fill="#5b6670")
    img.save(path)


def save_roadmap_diagram(path: Path) -> None:
    img = Image.new("RGB", (1200, 500), "#ffffff")
    draw = ImageDraw.Draw(img)
    title_font = load_font(30, True)
    font = load_font(18, True)
    small = load_font(15)
    draw.text((36, 28), "MVP 实施路线图", font=title_font, fill="#1f4e79")
    steps = [
        ("M1\nCLI 骨架"),
        ("M2\n安全与状态"),
        ("M3\nHard Check"),
        ("M4\nReview JSON"),
        ("M5\nQuality Gate"),
        ("M6\nAgent Adapter"),
        ("M7\n最终报告"),
    ]
    x = 55
    y = 200
    last = None
    for idx, step in enumerate(steps):
        box = (x, y, x + 135, y + 82)
        rounded_rect(draw, box, "#eaf3f8" if idx < 3 else "#fff3cd" if idx < 5 else "#e8f5e9")
        center_text(draw, box, step, font)
        if last:
            arrow(draw, (last[2], y + 41), (box[0], y + 41))
        last = box
        x += 160
    draw.text((70, 350), "路线原则：先跑通单任务闭环，再扩展多 Agent、Dashboard 和受控技能进化。", font=small, fill="#5b6670")
    img.save(path)


def ensure_diagrams() -> dict[str, Path]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    diagrams = {
        "architecture": ASSET_DIR / "architecture.png",
        "workflow": ASSET_DIR / "workflow.png",
        "gate": ASSET_DIR / "quality-gate.png",
        "roadmap": ASSET_DIR / "roadmap.png",
    }
    save_architecture_diagram(diagrams["architecture"])
    save_workflow_diagram(diagrams["workflow"])
    save_gate_diagram(diagrams["gate"])
    save_roadmap_diagram(diagrams["roadmap"])
    return diagrams


def inline_markup(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def parse_table(lines: list[str], start: int) -> tuple[str, int]:
    raw_lines: list[str] = []
    idx = start
    while idx < len(lines) and lines[idx].strip().startswith("|"):
        raw_lines.append(lines[idx].strip())
        idx += 1

    rows: list[list[str]] = []
    for line_no, raw in enumerate(raw_lines):
        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        if line_no == 1 and all(set(cell.replace(":", "").strip()) <= {"-"} for cell in cells):
            continue
        rows.append(cells)

    if not rows:
        return "", idx

    out = ["<table>"]
    for row_no, row in enumerate(rows):
        tag = "th" if row_no == 0 else "td"
        out.append("<tr>" + "".join(f"<{tag}>{inline_markup(cell)}</{tag}>" for cell in row) + "</tr>")
    out.append("</table>")
    return "\n".join(out), idx


def markdown_to_html(markdown_text: str, presentation: bool = False) -> str:
    lines = markdown_text.splitlines()
    out: list[str] = []
    in_code = False
    code_lines: list[str] = []
    list_stack: list[str] = []
    idx = 0

    def close_lists() -> None:
        while list_stack:
            out.append(f"</{list_stack.pop()}>")

    while idx < len(lines):
        line = lines[idx].rstrip()

        if line.startswith("```"):
            if in_code:
                out.append("<pre>" + html.escape("\n".join(code_lines)) + "</pre>")
                code_lines = []
                in_code = False
            else:
                close_lists()
                in_code = True
            idx += 1
            continue

        if in_code:
            code_lines.append(line)
            idx += 1
            continue

        if not line.strip():
            close_lists()
            idx += 1
            continue

        if line.strip().startswith("|"):
            close_lists()
            table_html, idx = parse_table(lines, idx)
            out.append(table_html)
            continue

        if line.startswith("# "):
            close_lists()
            out.append(f"<h1>{inline_markup(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            close_lists()
            heading = inline_markup(line[3:].strip())
            css_class = ' class="slide"' if presentation and heading.startswith("Slide ") else ""
            out.append(f"<h1{css_class}>{heading}</h1>")
        elif line.startswith("### "):
            close_lists()
            out.append(f"<h2>{inline_markup(line[4:].strip())}</h2>")
        elif line.startswith("#### "):
            close_lists()
            out.append(f"<h3>{inline_markup(line[5:].strip())}</h3>")
        elif line.startswith("- "):
            if not list_stack or list_stack[-1] != "ul":
                close_lists()
                out.append("<ul>")
                list_stack.append("ul")
            out.append(f"<li>{inline_markup(line[2:].strip())}</li>")
        elif re.match(r"^\d+\.\s+", line):
            if not list_stack or list_stack[-1] != "ol":
                close_lists()
                out.append("<ol>")
                list_stack.append("ol")
            out.append(f"<li>{inline_markup(re.sub(r'^\d+\.\s+', '', line).strip())}</li>")
        else:
            close_lists()
            out.append(f"<p>{inline_markup(line.strip())}</p>")
        idx += 1

    close_lists()
    return "\n".join(out)


def diagram_html(diagrams: list[tuple[Path, str]]) -> str:
    blocks = []
    for path, caption in diagrams:
        src = path.as_uri()
        blocks.append(
            f'<div class="diagram"><img src="{src}" alt="{html.escape(caption)}">'
            f'<div class="diagram-title">{html.escape(caption)}</div></div>'
        )
    return "\n".join(blocks)


def build_html(
    source: Path,
    title: str,
    subtitle: str,
    presentation: bool = False,
    diagrams: list[tuple[Path, str]] | None = None,
) -> str:
    body = markdown_to_html(source.read_text(encoding="utf-8-sig"), presentation=presentation)
    visual = diagram_html(diagrams or [])
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(title)} - {html.escape(subtitle)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="cover">
  <h1>{html.escape(title)}</h1>
  <div class="subtitle">{html.escape(subtitle)}</div>
</div>
{visual}
{body}
</body>
</html>
"""


def write_doc(source: Path, target: Path, title: str, subtitle: str, diagrams: list[tuple[Path, str]]) -> None:
    target.write_text(build_html(source, title, subtitle, diagrams=diagrams), encoding="utf-8")


def export_pdf(source: Path, target: Path, diagrams: list[tuple[Path, str]]) -> None:
    html_path = TEMP_DIR / "presentation.html"
    html_path.write_text(
        build_html(source, "自动循环进化编码智能体系统", "对外演讲文档", presentation=True, diagrams=diagrams),
        encoding="utf-8",
    )
    if not EDGE.exists():
        raise RuntimeError("Microsoft Edge not found; cannot export PDF.")
    subprocess.run(
        [
            str(EDGE),
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={target}",
            "--print-to-pdf-no-header",
            str(html_path),
        ],
        check=True,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    diagrams = ensure_diagrams()

    doc_diagrams = {
        "需求文档": [
            (diagrams["workflow"], "图 1：单任务自动循环流程"),
            (diagrams["gate"], "图 2：质量门控评分模型"),
        ],
        "技术方案": [
            (diagrams["architecture"], "图 1：系统总体架构"),
            (diagrams["workflow"], "图 2：核心执行流程"),
            (diagrams["gate"], "图 3：质量门控模型"),
        ],
        "MVP 实施计划": [
            (diagrams["roadmap"], "图 1：MVP 实施路线图"),
            (diagrams["workflow"], "图 2：MVP 闭环验证流程"),
        ],
    }

    for source, target, title, subtitle in DOC_SOURCES:
        write_doc(source, target, title, subtitle, doc_diagrams.get(subtitle, []))
    export_pdf(
        PRESENTATION_SOURCE,
        PRESENTATION_PDF,
        [
            (diagrams["architecture"], "总体架构"),
            (diagrams["workflow"], "核心闭环"),
            (diagrams["gate"], "质量门控"),
            (diagrams["roadmap"], "MVP 路线"),
        ],
    )


if __name__ == "__main__":
    main()
