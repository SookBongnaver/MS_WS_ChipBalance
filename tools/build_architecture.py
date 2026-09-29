"""Build the Workshop architecture diagram (SVG + editable Excalidraw) from official icons.

Run: python tools/build_architecture.py
Then render assets/architecture.svg to assets/architecture.png at 1800x1385 in a browser.
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
    d = Diagram("architecture", 1800, 1385)
    d.text(45, 26, "원료 Chip Balance와 긴급 오더 대응 | Azure Databricks + Microsoft Fabric", 30, 1700, True)
    d.text(45, 78, "Databricks에서 원본을 정제·계산해 Gold를 OneLake에 저장하고, "
                   "Fabric에서 현황을 파악한 뒤 Operations agent의 제안을 담당자가 Teams에서 승인합니다", 20, 1700)

    steps = [("① 현재 계산", "Databricks 04·05 계산 · Power BI 현황"),
             ("② 판단 기준", "Databricks 05 · 대응안별 기준 충족 여부"),
             ("③ Agent 제안", "Operations agent · Teams로 제안"),
             ("④ 사람 승인", "Teams에서 Yes/No · 승인 내역 저장")]
    xs = [45, 480, 915, 1350]
    for i, (title, detail) in enumerate(steps):
        x, w = xs[i], (380 if i < 3 else 405)
        d.rect(x, 122, w, 74)
        d.text(x + 18, 130, title, 19, w - 30, True)
        d.text(x + 18, 162, detail, 16, w - 30)
        if i < 3:
            d.arrow([(x + w, 159), (xs[i + 1], 159)])

    d.rect(40, 222, 680, 830, GRAY, True)
    d.icon("databricks.svg", 60, 242)
    d.text(122, 248, "Azure Databricks | 데이터 정제·계산", 23, 600, True)
    d.text(70, 304, "Classic compute · Notebook 01~05 · Spark / Delta\n원본·Bronze·Silver는 Unity Catalog에 저장", 17, 640)
    d.card(70, 380, 270, 180, "원본 → Bronze", "02 원본 데이터 6종 생성\n03 원본 그대로 적재\nchip_bronze_* 6개", "storage.svg")
    d.arrow([(340, 470), (400, 470)])
    d.text(352, 437, "정제", 15, 50)
    d.card(400, 380, 300, 180, "Silver / 정제", "형식 맞춤 · 중복 제거\n수량 없는 입고는 격리\nchip_silver_* 6개 + 격리 1개", "storage.svg")
    d.arrow([(550, 560), (550, 630)])
    d.text(565, 582, "업무 계산", 16, 130)
    d.card(400, 630, 300, 250, "Gold / 계산",
           "04 날짜별 소요량·예상 재고\n05 긴급 오더 재계산·비교\n05 대응안 3개와 판단 기준\nGold 9개를 OneLake에 저장",
           "databricks.svg")
    d.text(75, 632, "① 현재 계산 · ② 판단 기준", 19, 320, True)
    d.text(75, 674, "소요량 = 생산량 × 소요량 기준\n마감 재고 = 전일 + 입고 − 소요량", 16, 320)
    d.text(75, 748, "판단 기준 (대응안마다)", 17, 320, True)
    d.text(75, 780, "· 매일 마감 재고 ≥ 안전재고 200kg\n· 입고 직후 재고 ≤ 용량 3,000kg", 16, 320)
    d.text(70, 930, "Bronze·Silver: Unity Catalog lab_factory.lab_p001\nOneLake 저장 인증 정보는 secret scope에 보관", 16, 640)

    d.rect(800, 222, 960, 830, GRAY, True)
    d.icon("fabric.svg", 820, 242)
    d.text(882, 248, "Microsoft Fabric | 현황 파악·의사결정 지원", 23, 860, True)
    d.text(830, 304, "Gold를 읽어 현황을 파악하고, Agent 제안을 담당자가 Teams에서 승인합니다", 17, 900)
    d.card(840, 360, 290, 240, "OneLake Gold",
           "Lakehouse lh_factory_p001\ngold 스키마 Delta 테이블 9개\nSQL analytics endpoint로 확인\nGold 저장은 Databricks만",
           "lakehouse.svg")
    d.arrow([(700, 700), (770, 700), (770, 560), (840, 560)])
    d.text(706, 708, "직접 저장", 15, 70)
    d.text(845, 640, "SQL · Power BI · Ontology ·\nOperations agent가\n같은 Gold를 읽습니다", 16, 280)
    d.card(840, 815, 290, 175, "Notebook · 승인 기록", "승인한 대응안을 저장\ndbo.chip_decision_log\n발주는 기존 절차로 진행",
           "notebook.svg")

    d.card(1190, 345, 250, 130, "Semantic model", "Direct Lake\n관계 · 측정값", "semantic-model.svg")
    d.arrow([(1440, 410), (1485, 410)])
    d.card(1485, 345, 250, 130, "Power BI 보고서", "① 현황 파악\n수급 · 비교 · 대응안", "power-bi.svg")
    d.card(1190, 500, 545, 115, "Ontology (preview) · Graph",
           "원료 · Bunker · 생산계획 · 일별 재고 · 시나리오 · 대응안의 관계")
    d.card(1190, 640, 545, 150, "Operations agent · ③ Agent 제안",
           "Fabric IQ · Ontology를 5분마다 확인\n판단 기준을 만족한 대응안을 요약해 Teams로 제안",
           "operations-agent.svg")
    d.card(1190, 815, 545, 175, "Teams · ④ 사람 승인",
           "Fabric Operations Agent 앱으로 제안 수신\n담당자가 보고서 수치와 대조해 Yes/No\nYes이면 승인 기록 Notebook 실행",
           "users.svg")
    d.arrow([(1130, 410), (1190, 410)])
    d.arrow([(1130, 557), (1190, 557)])
    d.arrow([(1462, 615), (1462, 640)])
    d.arrow([(1462, 790), (1462, 815)])
    d.arrow([(1190, 902), (1130, 902)])
    d.text(1142, 870, "Yes", 15, 40)

    d.rect(40, 1085, 1720, 225, GRAY, True)
    d.text(65, 1100, "운영에 적용할 때 연결", 20, 1000, True)
    d.card(70, 1150, 490, 135, "원천 시스템", "FPIMS · PVSS · SAP 추출 데이터\n02의 원본 데이터 대신 Bronze로 적재", dashed=True)
    d.card(620, 1150, 520, 135, "Power Automate", "승인한 조치를 업무 시스템에 연결\n예: 구매 요청 작성 · 공급사 메일",
           "power-automate.svg", dashed=True)
    d.card(1190, 1150, 545, 135, "Power Apps", "대응안 승인·이력 화면\nPower BI 보고서에 Power Apps visual로 삽입",
           "power-apps.svg", dashed=True)
    d.arrow([(1300, 990), (1300, 1068), (880, 1068), (880, 1150)], True, GRAY)
    d.text(892, 1112, "승인한 조치", 15, 150)
    d.arrow([(1600, 990), (1600, 1150)], True, GRAY)
    d.text(1612, 1100, "승인 화면을 앱으로", 15, 200)

    d.arrow([(65, 1345), (130, 1345)])
    d.text(145, 1330, "실선: 실습에서 만들고 실행하는 흐름", 17, 420)
    d.arrow([(620, 1345), (685, 1345)], True, GRAY)
    d.text(700, 1330, "점선: 운영에 적용할 때 연결", 17, 420)
    d.save()


if __name__ == "__main__":
    architecture()
    print("Built assets/architecture.svg and assets/architecture.excalidraw. Render the SVG to PNG next.")
