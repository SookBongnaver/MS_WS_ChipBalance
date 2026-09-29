"""Build the Workshop architecture diagram (SVG + editable Excalidraw) from official icons.

Run: python tools/build_architecture.py
Then render assets/architecture.svg to assets/architecture.png at 1800x1350 in a browser.
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
    d = Diagram("architecture", 1800, 1350)
    d.text(45, 26, "원료 Chip Balance Workshop 구성 | Azure Databricks + Microsoft Fabric", 30, 1700, True)
    d.text(45, 78, "Databricks에서 원본을 정제·계산해 Gold를 OneLake에 저장하고, "
                   "Fabric에서 Gold로 현황을 파악하고 Agent 제안을 받아 담당자가 결정합니다", 20, 1700)

    steps = [("① 현재 계산", "Databricks 계산 · Power BI 현황"),
             ("② 판단 기준", "Databricks 05 · 대응안별 기준 충족"),
             ("③ Agent 제안", "Fabric Data agent · Gold 근거"),
             ("④ 사람 승인", "담당자 결정 · 발주·메일 없음")]
    xs, box_w = [45, 480, 915, 1350], 380
    for i, (title, detail) in enumerate(steps):
        x = xs[i]
        w = box_w if i < 3 else 405
        d.rect(x, 122, w, 74)
        d.text(x + 18, 130, title, 19, w - 30, True)
        d.text(x + 18, 162, detail, 16, w - 30)
        if i < 3:
            d.arrow([(x + w, 159), (xs[i + 1], 159)])

    d.rect(40, 222, 680, 790, GRAY, True)
    d.icon("databricks.svg", 60, 242)
    d.text(122, 248, "Azure Databricks | 데이터 정제·계산", 23, 600, True)
    d.text(70, 304, "Classic compute · Notebook 01~05 · Spark / Delta\n원본·Bronze·Silver는 Unity Catalog에 저장", 17, 640)
    d.card(70, 380, 270, 180, "원본 → Bronze", "02 교육용 원본 JSON 6종\n03 원본 그대로 적재\nchip_bronze_* 6개", "storage.svg")
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
    d.text(70, 918, "Bronze·Silver: Unity Catalog lab_factory.lab_p001\nOneLake 쓰기 인증 정보는 secret scope에 보관", 16, 640)

    d.rect(800, 222, 960, 790, GRAY, True)
    d.icon("fabric.svg", 820, 242)
    d.text(882, 248, "Microsoft Fabric | 현황 파악·의사결정 지원", 23, 860, True)
    d.text(830, 304, "Databricks가 저장한 Gold를 읽어서 사용 · Fabric에서 데이터를 만들거나 고치지 않음", 17, 920)
    d.card(840, 500, 280, 260, "OneLake Gold",
           "Lakehouse lh_factory_p001\ngold 스키마 Delta 테이블 9개\nSQL analytics endpoint로 확인\n쓰기: Databricks · 읽기: Fabric",
           "lakehouse.svg")
    d.arrow([(700, 690), (840, 690)])
    d.text(727, 656, "직접 저장", 15, 70)
    d.text(840, 790, "Fabric 항목은 모두 같은 Gold를 읽습니다\nSQL · Power BI · Ontology · Data agent", 16, 330)

    d.card(1190, 330, 250, 135, "Semantic model", "Direct Lake\n관계 · 측정값", "semantic-model.svg")
    d.arrow([(1440, 397), (1485, 397)])
    d.card(1485, 330, 250, 135, "Power BI 보고서", "원료 수급 · 긴급 오더\n비교 · 대응안 검토", "power-bi.svg")
    d.card(1190, 495, 545, 130, "Ontology (preview) · Graph",
           "원료 · Bunker · 생산계획 · 일별 재고 · 시나리오 · 대응안\n관계를 정의하고 Graph로 부족 지점과 대응안을 탐색")
    d.card(1190, 655, 545, 130, "Fabric Data agent · ③ Agent 제안",
           "Gold 대응안·비교·요약 테이블 3개로 답변 · 읽기 전용\n기준을 충족한 안 중 추가 구매량이 적은 안을 먼저 제안",
           "data-agent.svg")
    d.card(1190, 820, 545, 165, "담당자 · ④ 사람 승인",
           "보고서 수치와 Agent 답변을 대조해 결정\n공급사 납기·비용 등 데이터 밖 조건 확인\n이 Workshop은 결정만 기록 · 발주·메일 없음",
           "users.svg")
    d.arrow([(1120, 525), (1155, 525), (1155, 397), (1190, 397)])
    d.arrow([(1120, 560), (1190, 560)])
    d.arrow([(1120, 720), (1190, 720)])
    d.arrow([(1462, 785), (1462, 820)])

    d.rect(40, 1045, 1720, 245, GRAY, True)
    d.text(65, 1060, "업무에 적용할 때 연결 | 이 Workshop에서는 만들거나 실행하지 않습니다", 20, 1600, True)
    d.card(70, 1110, 500, 150, "Power Automate", "승인된 조치 실행\n예: 구매 요청 초안 작성 · 담당자 알림",
           "power-automate.svg", dashed=True)
    d.card(620, 1110, 520, 150, "Power Apps", "대응안 승인 화면 · 승인 결과 기록\nPower BI 보고서에 Power Apps visual로 삽입",
           "power-apps.svg", dashed=True)
    d.card(1190, 1110, 545, 150, "Operations agent · Fabric IQ",
           "Ontology(preview)·Eventhouse 조건을 5분마다 확인\n조건 충족 시 Teams로 조치 제안 → 담당자 Yes/No\n승인한 조치만 실행 (Fabric 항목 · Power Automate)",
           "operations-agent.svg", dashed=True)
    d.arrow([(1735, 575), (1750, 575), (1750, 1185), (1735, 1185)], True, GRAY)
    d.arrow([(1462, 1110), (1462, 985)], True, GRAY)
    d.text(1476, 1016, "Teams로 제안·승인 요청", 15, 240)
    d.arrow([(1190, 935), (880, 935), (880, 1110)], True, GRAY)
    d.text(892, 950, "승인 화면에서 결정", 15, 200)
    d.arrow([(620, 1185), (570, 1185)], True, GRAY)

    d.arrow([(65, 1318), (130, 1318)])
    d.text(145, 1303, "실선: 이 Workshop에서 실행하는 흐름", 17, 420)
    d.arrow([(620, 1318), (685, 1318)], True, GRAY)
    d.text(700, 1303, "점선: 업무에 적용할 때 연결", 17, 420)
    d.text(1330, 1303, "2026-09-29 개념도 · 실제 제품 화면 아님", 16, 420)
    d.save()


if __name__ == "__main__":
    architecture()
    print("Built assets/architecture.svg and assets/architecture.excalidraw. Render the SVG to PNG next.")
