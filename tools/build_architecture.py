"""Build the Workshop architecture diagram (SVG + editable Excalidraw) from official icons.

Run: python tools/build_architecture.py
Writes assets/architecture.svg, .excalidraw and, when Microsoft Edge is installed, .png (1800x1360).
"""
import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BLUE = "#0078D4"
GRAY = "#64748B"
EDGE_PATHS = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
              Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]


class Diagram:
    def __init__(self, name, width, height):
        self.name, self.width, self.height = name, width, height
        self.elements, self.files, self.svg = [], {}, []
        self.serial = 0

    def element(self, kind, x, y, w, h, **kwargs):
        self.serial += 1
        value = {
            "id": f"{self.name}-{self.serial}", "type": kind, "x": x, "y": y,
            "width": w, "height": h, "angle": 0, "strokeColor": BLUE,
            "backgroundColor": "transparent", "fillStyle": "solid",
            "strokeWidth": 1.5, "strokeStyle": "solid", "roughness": 0,
            "opacity": 100, "groupIds": [], "frameId": None, "index": None,
            "roundness": None, "seed": self.serial, "version": 1, "versionNonce": 1,
            "isDeleted": False, "boundElements": None, "updated": 0, "link": None,
            "locked": False,
        }
        value.update(kwargs)
        self.elements.append(value)

    def rect(self, x, y, w, h, stroke=BLUE, dashed=False):
        self.element("rectangle", x, y, w, h, strokeColor=stroke,
                     strokeStyle="dashed" if dashed else "solid", roundness={"type": 3})
        dash = 'stroke-dasharray="7 5"' if dashed else ""
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
                        f'fill="none" stroke="{stroke}" stroke-width="1.5" {dash}/>')

    def text(self, x, y, text, size=18, width=400, bold=False):
        lines = text.split("\n")
        self.element("text", x, y, width, size * 1.45 * len(lines),
                     text=text, originalText=text, fontSize=size, fontFamily=2,
                     strokeColor="#000000", textAlign="left", verticalAlign="top",
                     containerId=None, autoResize=True, lineHeight=1.45)
        weight = "600" if bold else "400"
        self.svg.append(f'<text x="{x}" y="{y + size}" font-size="{size}" '
                        f'font-weight="{weight}" fill="#000000">')
        for i, line in enumerate(lines):
            self.svg.append(f'<tspan x="{x}" dy="{0 if i == 0 else round(size * 1.45, 1)}">'
                            f'{html.escape(line)}</tspan>')
        self.svg.append("</text>")

    def icon(self, name, x, y, size=48):
        raw = (ASSETS / "icons" / name).read_bytes()
        root = ET.fromstring(raw)
        if root.get("viewBox"):
            _, _, iw, ih = map(float, root.get("viewBox").replace(",", " ").split())
        else:
            iw = float(re.match(r"[\d.]+", root.get("width")).group())
            ih = float(re.match(r"[\d.]+", root.get("height")).group())
        scale = size / max(iw, ih)
        w, h = iw * scale, ih * scale
        x, y = x + (size - w) / 2, y + (size - h) / 2
        key = hashlib.sha256(raw).hexdigest()
        data = "data:image/svg+xml;base64," + base64.b64encode(raw).decode()
        self.files[key] = {"id": key, "mimeType": "image/svg+xml", "dataURL": data,
                           "created": 0, "lastRetrieved": 0}
        self.element("image", x, y, w, h, fileId=key, status="saved",
                     scale=[1, 1], crop=None, strokeWidth=0)
        self.svg.append(f'<image x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                        f'preserveAspectRatio="xMidYMid meet" href="{data}"/>')

    def card(self, x, y, w, h, title, detail, icon=None, dashed=False):
        self.rect(x, y, w, h, GRAY if dashed else BLUE, dashed)
        if icon:
            self.icon(icon, x + 16, y + 16, 44)
        self.text(x + (72 if icon else 18), y + 22, title, 19, w - 85, True)
        self.text(x + 18, y + 74, detail, 16, w - 30)

    def arrow(self, points, dashed=False, color=BLUE):
        x, y = points[0]
        relative = [[px - x, py - y] for px, py in points]
        self.element("arrow", x, y, max(px for px, _ in points) - min(px for px, _ in points),
                     max(py for _, py in points) - min(py for _, py in points),
                     points=relative, strokeColor=color,
                     strokeStyle="dashed" if dashed else "solid",
                     startBinding=None, endBinding=None, startArrowhead=None,
                     endArrowhead="arrow", elbowed=False)
        coords = " ".join(f"{px},{py}" for px, py in points)
        dash = 'stroke-dasharray="8 5"' if dashed else ""
        marker = "gray" if color == GRAY else "blue"
        self.svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" '
                        f'stroke-width="2" {dash} marker-end="url(#{marker})"/>')

    def save(self):
        (ASSETS / f"{self.name}.png").unlink(missing_ok=True)
        header = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}" role="img" aria-label="{self.name}">'
            '<defs><style>text {font-family:"Segoe UI","Malgun Gothic",sans-serif;}</style>'
        )
        for key, color in [("blue", BLUE), ("gray", GRAY)]:
            header += (f'<marker id="{key}" viewBox="0 0 10 10" refX="9" refY="5" '
                       f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                       f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>')
        header += f'</defs><rect width="{self.width}" height="{self.height}" fill="white"/>'
        (ASSETS / f"{self.name}.svg").write_text(header + "".join(self.svg) + "</svg>", encoding="utf-8")
        scene = {"type": "excalidraw", "version": 2, "source": "chip-balance-workshop-diagram",
                 "elements": self.elements, "files": self.files,
                 "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None}}
        (ASSETS / f"{self.name}.excalidraw").write_text(
            json.dumps(scene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def architecture():
    d = Diagram("architecture", 1800, 1360)
    d.text(45, 26, "원료 Chip Balance와 긴급 오더 대응 | Azure Databricks + Microsoft Fabric", 30, 1700, True)
    d.text(45, 78, "Azure Databricks에서 정제·계산한 Gold를 Microsoft Fabric에서 활용합니다. "
                   "담당자는 Teams에서 대응안을 승인하고, Copilot 채팅으로 데이터를 질문합니다", 20, 1700)

    steps = [("① 현재 계산", "Databricks 05·10 계산 · Power BI 현황"),
             ("② 판단 기준", "Databricks 10 · 대응안별 기준 충족 여부"),
             ("③ Agent 제안", "Fabric Operations agent → Teams로 제안"),
             ("④ 사람 승인", "Teams에서 Yes/No · 승인 기록 저장")]
    xs = [45, 480, 915, 1350]
    for i, (title, detail) in enumerate(steps):
        x, w = xs[i], (380 if i < 3 else 405)
        d.rect(x, 122, w, 74)
        d.text(x + 18, 130, title, 19, w - 30, True)
        d.text(x + 18, 162, detail, 16, w - 30)
        if i < 3:
            d.arrow([(x + w, 159), (xs[i + 1], 159)])

    # Azure Databricks
    d.rect(40, 222, 600, 790, GRAY, True)
    d.icon("databricks.svg", 60, 242)
    d.text(122, 248, "Azure Databricks | 데이터 정제·계산", 23, 500, True)
    d.text(70, 304, "Classic compute · Notebook · Spark / Delta\n원천 Volume과 Bronze·Silver·Gold는 Unity Catalog에 저장", 17, 550)
    d.card(70, 380, 240, 180, "원천 → Bronze", "02 원천 파일 14개 생성\nSAP · FPIMS · PVSS\n03 파일 그대로 적재", "storage.svg")
    d.arrow([(310, 470), (360, 470)])
    d.text(316, 437, "정제", 15, 40)
    d.card(360, 380, 260, 180, "Silver / 정제", "04 날짜·단위 형식 맞춤\n중복·공란·미등록 코드 격리\n센서 이상값 격리", "storage.svg")
    d.arrow([(490, 560), (490, 630)])
    d.text(505, 582, "업무 계산", 16, 110)
    d.card(360, 630, 260, 250, "Gold / 계산",
           "05 실제 소요량·시작 재고\n05 4분기 날짜별 재고\n10 긴급 오더·대응안 4개\nGold를 OneLake에 저장",
           "databricks.svg")
    d.card(70, 630, 240, 130, "Genie", "06 테이블·열 설명 작성\n자연어 질문 → SQL", "databricks.svg")
    d.arrow([(360, 695), (310, 695)])
    d.text(75, 782, "① 현재 계산", 18, 270, True)
    d.text(75, 812, "소요량 = 계획 × 실제 소요량\n마감 = 전일 + 입고 ± 이송 − 소요", 16, 270)
    d.text(75, 870, "② 판단 기준 (대응안마다)", 18, 270, True)
    d.text(75, 900, "· 모든 Bunker 매일 안전재고 이상\n· 입고 후 재고 ≤ Bunker 용량\n· 모든 판매오더 납기 준수\n· 이송량 ≤ 경로 하루 한도", 16, 270)

    # Microsoft Fabric
    d.rect(720, 222, 690, 790, GRAY, True)
    d.icon("fabric.svg", 740, 242)
    d.text(802, 248, "Microsoft Fabric | 현황 파악·대응안 제안", 23, 590, True)
    d.text(750, 304, "Gold로 현황을 파악하고, Agent가 대응안을 제안하고 질문에 답합니다", 17, 640)
    d.arrow([(620, 700), (680, 700), (680, 460), (750, 460)])
    d.text(644, 712, "관리 ID\n저장", 15, 70)
    d.card(750, 360, 270, 200, "OneLake Gold",
           "Lakehouse lh_chipbalance_p001\ngold 스키마 Delta 테이블\nSQL analytics endpoint로 확인\nGold 저장은 Databricks만",
           "lakehouse.svg")
    d.card(750, 590, 270, 140, "Ontology", "라인 · Bunker · 원료 · 제품\n생산계획 · 일별 재고 · 대응안", "ontology.svg")
    d.card(750, 800, 270, 180, "Notebook · 승인 기록", "승인하면 실행\n승인한 대응안 저장\ndbo.chip_decision_log", "notebook.svg")
    d.card(1060, 345, 330, 100, "Semantic model", "Direct Lake · 관계 · 측정값", "semantic-model.svg")
    d.arrow([(1225, 445), (1225, 470)])
    d.card(1060, 470, 330, 135, "Power BI 보고서", "원료 수급 현황 · 긴급 오더 비교\n대응안 검토", "power-bi.svg")
    d.card(1060, 630, 330, 135, "Data agent", "Ontology를 근거로 질문에 답변\n읽기 전용", "data-agent.svg")
    d.card(1060, 790, 330, 140, "Operations agent", "③ Ontology를 5분마다 확인\n위험 이벤트에 맞는 대응안 제안",
           "operations-agent.svg")
    d.arrow([(1020, 395), (1060, 395)])
    d.arrow([(885, 560), (885, 590)])
    d.arrow([(1020, 697), (1060, 697)])
    d.arrow([(1020, 720), (1040, 720), (1040, 845), (1060, 845)])
    d.arrow([(1060, 905), (1020, 905)])
    d.text(1024, 912, "Yes", 14, 34)

    # Microsoft 365
    d.rect(1450, 222, 310, 790, GRAY, True)
    d.text(1470, 248, "Microsoft 365", 23, 270, True)
    d.text(1470, 304, "담당자가 Teams에서 승인하고\nCopilot 채팅으로 질문합니다", 17, 280)
    d.card(1470, 630, 270, 135, "Copilot 채팅", "Microsoft 365 Copilot에서\nData agent에 질문", "copilot.svg")
    d.card(1470, 790, 270, 180, "Microsoft Teams", "④ 채팅으로 제안 수신\n보고서 수치와 대조 후\nYes / No 승인", "teams.svg")
    d.arrow([(1470, 675), (1390, 675)])
    d.text(1414, 643, "질문", 15, 34)
    d.arrow([(1390, 725), (1470, 725)])
    d.text(1414, 733, "답변", 15, 34)
    d.arrow([(1390, 830), (1470, 830)])
    d.text(1414, 798, "제안", 15, 34)
    d.arrow([(1470, 905), (1390, 905)])
    d.text(1414, 912, "승인", 15, 34)

    # Operational extension
    d.rect(40, 1045, 1720, 250, GRAY, True)
    d.text(65, 1058, "운영에 적용할 때 연결", 20, 400, True)
    d.card(70, 1105, 540, 160, "원천 시스템 연계", "SAP · FPIMS · PVSS 추출 파일을\n정해진 시각에 Volume raw로 전송", dashed=True)
    d.rect(700, 1090, 1045, 190, GRAY, True)
    d.text(720, 1100, "Power Platform", 18, 300, True)
    d.card(720, 1140, 480, 125, "Power Apps", "승인 이력 조회 화면 (선택)\n승인은 Teams에서 끝나며 앱이 없어도 됩니다",
           "power-apps.svg", dashed=True)
    d.card(1240, 1140, 485, 125, "Power Automate", "승인한 조치를 업무 시스템에 연결\n예: 구매 요청 작성 · 공급사 메일",
           "power-automate.svg", dashed=True)
    d.arrow([(340, 1105), (340, 1014)], True, GRAY)
    d.text(352, 1062, "03 Bronze로 적재", 15, 150)
    d.arrow([(885, 980), (885, 1140)], True, GRAY)
    d.text(897, 1104, "승인 이력", 15, 120)
    d.arrow([(1300, 930), (1300, 1140)], True, GRAY)
    d.text(1312, 1104, "승인 후 조치", 15, 150)
    d.arrow([(65, 1330), (130, 1330)])
    d.text(145, 1315, "실선: 실습에서 만들고 실행하는 흐름", 17, 420)
    d.arrow([(620, 1330), (685, 1330)], True, GRAY)
    d.text(700, 1315, "점선: 운영에 적용할 때 연결", 17, 420)
    d.save()
    return d


def render_png(d):
    edge = next((str(p) for p in EDGE_PATHS if p.exists()), None) or shutil.which("msedge")
    if not edge:
        return False
    png = ASSETS / f"{d.name}.png"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={profile}", f"--window-size={d.width},{d.height}",
                        f"--screenshot={png}", (ASSETS / f"{d.name}.svg").as_uri()],
                       check=True, capture_output=True, timeout=120)
    return png.exists()


if __name__ == "__main__":
    diagram = architecture()
    if render_png(diagram):
        print("Built assets/architecture.svg, .excalidraw and .png.")
    else:
        print("Built assets/architecture.svg and .excalidraw. Microsoft Edge not found: "
              "render the SVG to assets/architecture.png at 1800x1360 in a browser.")
