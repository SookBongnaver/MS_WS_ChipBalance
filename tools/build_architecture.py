"""Build the Workshop architecture diagram (SVG + editable Excalidraw) from official icons.

Run: python tools/build_architecture.py
Then render assets/architecture.svg to assets/architecture.png at 1800x1360 in a browser.
"""
import base64
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BLUE = "#0078D4"
GRAY = "#64748B"


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
    d.text(45, 78, "Azure Databricks에서 정제·계산한 Gold를 Microsoft Fabric에서 활용하고, "
                   "Operations agent의 제안을 담당자가 Microsoft Teams에서 승인합니다", 20, 1700)

    steps = [("① 현재 계산", "Databricks 04·05 계산 · Power BI 현황"),
             ("② 판단 기준", "Databricks 05 · 대응안별 기준 충족 여부"),
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
    d.text(70, 304, "Classic compute · Notebook 01~05 · Spark / Delta\n원천·Bronze·Silver는 Unity Catalog에 저장", 17, 550)
    d.card(70, 380, 240, 180, "원천 → Bronze", "02 원천 파일 14개 업로드\nSAP · FPIMS · PVSS\n03 원천 그대로 적재", "storage.svg")
    d.arrow([(310, 470), (360, 470)])
    d.text(316, 437, "정제", 15, 40)
    d.card(360, 380, 260, 180, "Silver / 정제", "날짜·단위 형식 맞춤 · 중복 제거\n수량 누락·센서 이상값 격리\n정제 테이블 + 격리 테이블", "storage.svg")
    d.arrow([(490, 560), (490, 630)])
    d.text(505, 582, "업무 계산", 16, 110)
    d.card(360, 630, 260, 250, "Gold / 계산",
           "04 실제 소요량·시작 재고\n04 4분기 날짜별 재고\n05 긴급 오더·대응안 4개\nGold 17개 OneLake 저장",
           "databricks.svg")
    d.text(75, 632, "① 현재 계산 · ② 판단 기준", 19, 270, True)
    d.text(75, 674, "소요량 = 계획 × 실제 소요량 기준\n마감 = 전일 + 입고 ± 이송 − 소요", 16, 270)
    d.text(75, 748, "판단 기준 (대응안마다)", 17, 270, True)
    d.text(75, 780, "· 모든 Bunker 매일 안전재고 이상\n· 입고 후 재고 ≤ Bunker 용량\n· 모든 판매오더 납기 준수\n· 이송량 ≤ 경로 하루 한도", 16, 270)
    d.text(70, 930, "Bronze·Silver: Unity Catalog lab_factory.chipbalance_p001\nOneLake 저장: 관리 ID (Unity Catalog service credential)", 16, 550)

    # Microsoft Fabric
    d.rect(720, 222, 690, 790, GRAY, True)
    d.icon("fabric.svg", 740, 242)
    d.text(802, 248, "Microsoft Fabric | 현황 파악·대응안 제안", 23, 590, True)
    d.text(750, 304, "Gold를 읽어 현황을 파악하고, Operations agent가 대응안을 제안합니다", 17, 640)
    d.arrow([(620, 700), (680, 700), (680, 480), (750, 480)])
    d.text(646, 708, "직접 저장", 15, 70)
    d.card(750, 360, 270, 240, "OneLake Gold",
           "Lakehouse lh_chipbalance_p001\ngold 스키마 Delta 테이블 17개\nSQL analytics endpoint로 확인\nGold 저장은 Databricks만",
           "lakehouse.svg")
    d.text(755, 640, "SQL · Power BI · Ontology가\n같은 Gold를 읽습니다", 16, 260)
    d.card(750, 800, 270, 180, "Notebook · 승인 기록", "승인 후 자동 실행\n승인한 대응안 저장\ndbo.chip_decision_log", "notebook.svg")
    d.card(1060, 345, 330, 100, "Semantic model", "Direct Lake · 관계 · 측정값", "semantic-model.svg")
    d.arrow([(1225, 445), (1225, 470)])
    d.card(1060, 470, 330, 135, "Power BI 보고서", "① 원료 수급 · 긴급 오더 비교\n대응안 검토", "power-bi.svg")
    d.card(1060, 630, 330, 135, "Ontology (preview) · Graph", "라인 · Bunker · 원료 · 제품 · 생산계획\n일별 재고 · 대응안의 관계")
    d.arrow([(1225, 765), (1225, 790)])
    d.card(1060, 790, 330, 140, "Operations agent", "③ Ontology를 5분마다 확인\n위험 이벤트에 맞는 대응안을 제안",
           "operations-agent.svg")
    d.arrow([(1020, 395), (1060, 395)])
    d.arrow([(1020, 570), (1040, 570), (1040, 697), (1060, 697)])
    d.arrow([(1060, 880), (1020, 880)])

    # Microsoft 365
    d.rect(1450, 222, 310, 790, GRAY, True)
    d.text(1470, 248, "Microsoft 365", 23, 270, True)
    d.text(1470, 304, "담당자가 Teams에서\n제안을 확인하고 승인합니다", 17, 280)
    d.card(1470, 790, 270, 180, "Microsoft Teams",
           "④ Fabric Operations Agent\n앱으로 제안 수신\n보고서 수치와 대조 후\nYes / No 선택", "users.svg")
    d.arrow([(1390, 830), (1470, 830)])
    d.text(1416, 798, "제안", 15, 34)
    d.arrow([(1470, 905), (1390, 905)])
    d.text(1416, 912, "승인", 15, 34)

    # Operational extension
    d.rect(40, 1045, 1720, 250, GRAY, True)
    d.text(65, 1058, "운영에 적용할 때 연결", 20, 400, True)
    d.card(70, 1105, 540, 160, "원천 시스템 연계", "SAP · FPIMS · PVSS 정기 추출\n파일 업로드 대신 Bronze로 자동 적재", dashed=True)
    d.rect(700, 1090, 1045, 190, GRAY, True)
    d.text(720, 1100, "Power Platform", 18, 300, True)
    d.card(720, 1140, 480, 125, "Power Automate", "승인한 조치를 업무 시스템에 연결\n예: 구매 요청 작성 · 공급사 메일",
           "power-automate.svg", dashed=True)
    d.card(1240, 1140, 485, 125, "Power Apps", "대응안 승인·이력 화면\nPower BI 보고서에 Power Apps visual로 삽입",
           "power-apps.svg", dashed=True)
    d.arrow([(340, 1105), (340, 1014)], True, GRAY)
    d.text(352, 1062, "Bronze로 적재", 15, 150)
    d.arrow([(1300, 930), (1300, 1030), (960, 1030), (960, 1140)], True, GRAY)
    d.text(972, 1106, "승인한 조치", 15, 150)
    d.arrow([(1605, 970), (1605, 1140)], True, GRAY)
    d.text(1468, 1106, "승인 화면을 앱으로", 15, 135)

    d.arrow([(65, 1330), (130, 1330)])
    d.text(145, 1315, "실선: 실습에서 만들고 실행하는 흐름", 17, 420)
    d.arrow([(620, 1330), (685, 1330)], True, GRAY)
    d.text(700, 1315, "점선: 운영에 적용할 때 연결", 17, 420)
    d.save()

if __name__ == "__main__":
    architecture()
    print("Built assets/architecture.svg and assets/architecture.excalidraw. Render the SVG to PNG next.")
