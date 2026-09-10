"""Build the Japanese product-story review diagram as editable draw.io XML."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/presentation/diagrams/product-first"
INK = "#20364F"
BLUE = "#285E8E"
FONT = "Hiragino Sans"


class Activity:
    """Small XML author for one activity with genuine responsibility partitions."""

    def __init__(self) -> None:
        self.document = ET.Element("mxfile", host="app.diagrams.net")
        page = ET.SubElement(self.document, "diagram", id="product-first-ja", name="質問前の初回支援")
        model = ET.SubElement(page, "mxGraphModel", page="1", pageWidth="1600", pageHeight="1000", background="#FFFFFF")
        self.root = ET.SubElement(model, "root")
        ET.SubElement(self.root, "mxCell", id="0")
        ET.SubElement(self.root, "mxCell", id="1", parent="0")
        self.bounds: dict[str, tuple[float, float, float, float]] = {"1": (0, 0, 1600, 1000)}

    def box(self, ident: str, x: float, y: float, w: float, h: float, label: str,
            style: str = "", parent: str = "1", font: int = 24) -> str:
        px, py, _, _ = self.bounds[parent]
        cell = ET.SubElement(self.root, "mxCell", id=ident, parent=parent, vertex="1", value=label,
            style=f"html=0;whiteSpace=wrap;fontFamily={FONT};fontSize={font};fontColor={INK};strokeColor={INK};strokeWidth=1.6;fillColor=#FFFFFF;align=center;verticalAlign=middle;spacing=10;" + style)
        ET.SubElement(cell, "mxGeometry", x=str(x-px), y=str(y-py), width=str(w), height=str(h), attrib={"as": "geometry"})
        self.bounds[ident] = (x, y, w, h)
        return ident

    def text(self, ident: str, x: float, y: float, w: float, h: float, label: str,
             font: int = 22, bold: bool = False) -> str:
        return self.box(ident, x, y, w, h, label,
            f"strokeColor=none;fillColor=none;align=left;spacing=0;fontStyle={int(bold)};", font=font)

    def action(self, ident: str, lane: str, x: float, y: float, w: float, h: float,
               label: str, highlight: bool = False) -> str:
        style = "rounded=1;arcSize=16;"
        if highlight:
            style += f"fillColor=#EEF4FA;strokeColor={BLUE};fontStyle=1;"
        return self.box(ident, x, y, w, h, label, style, lane)

    def edge(self, ident: str, source: str, target: str, start: tuple[float, float],
             end: tuple[float, float], points: tuple[tuple[float, float], ...] = ()) -> None:
        sx, sy, sw, sh = self.bounds[source]
        tx, ty, tw, th = self.bounds[target]
        style = (
            f"edgeStyle=none;rounded=0;endArrow=open;endFill=0;strokeColor={INK};strokeWidth=1.8;"
            f"exitX={(start[0]-sx)/sw};exitY={(start[1]-sy)/sh};"
            f"entryX={(end[0]-tx)/tw};entryY={(end[1]-ty)/th};"
        )
        cell = ET.SubElement(self.root, "mxCell", id=ident, parent="1", edge="1", source=source, target=target, style=style)
        geom = ET.SubElement(cell, "mxGeometry", relative="1", attrib={"as": "geometry"})
        if points:
            arr = ET.SubElement(geom, "Array", attrib={"as": "points"})
            for x, y in points:
                ET.SubElement(arr, "mxPoint", x=str(x), y=str(y))

    def final(self, ident: str, x: float, y: float) -> str:
        self.box(ident, x, y, 28, 28, "", "ellipse;", "system")
        self.box(ident + "-centre", x+6, y+6, 16, 16, "", f"ellipse;fillColor={INK};", "system")
        return ident


def build() -> Path:
    d = Activity()
    d.box("canvas", 0, 0, 1600, 1000, "", "strokeColor=none;fillColor=#FFFFFF;")
    d.text("title", 50, 28, 1500, 52, "質問前に始まる学習支援", 36, True)
    d.text("scope", 50, 94, 1500, 36, "UMLアクティビティ図 ｜ 1人の学生：初回の自動復習と、その問いへの応答", 22)
    for ident, x, w, name in [("professor", 50, 400, "教授"), ("system", 450, 650, "システム"), ("student", 1100, 450, "学生")]:
        d.box(ident, x, 155, w, 790, name,
            f"swimlane;horizontal=1;startSize=50;collapsible=0;recursiveResize=0;swimlaneFillColor=#FFFFFF;fillColor=#F0F3F6;fontStyle=1;fontSize=26;fontFamily={FONT};", font=26)

    d.box("start", 239, 220, 22, 22, "", f"ellipse;fillColor={INK};", "professor")
    d.action("publish", "professor", 85, 270, 330, 86, "教材・目標・指導方針を\n設定して公開する")
    d.action("join", "student", 1130, 270, 390, 86, "授業を開き\n受信を許可する")
    d.action("save-conversation", "system", 650, 365, 375, 64, "学生の会話を作成・保存\ncreate_conversation()")
    d.action("save-goal", "system", 650, 459, 375, 64, "学習目標を作成・保存\nobserve_events()")
    d.text("api-owner", 460, 378, 180, 46, "APIの処理", 20)
    d.text("worker-owner", 460, 468, 180, 46, "ワーカーの巡回", 20)
    d.action("due", "system", 650, 490, 375, 78, "復習時期を検出する\n目標作成から24時間以降")
    d.action("choose", "system", 650, 598, 375, 78, "権限・教材・頻度を確認し\n許可された支援を選ぶ")
    d.box("decision", 813.5, 704, 48, 48, "", "rhombus;", "system")
    d.action("skip", "system", 480, 789, 230, 64, "今回は\n配信しない")
    d.action("deliver", "system", 775, 789, 285, 64, "支援メッセージを\n受信箱に保存する", True)
    d.action("reply", "student", 1130, 789, 390, 64, "届いた問いを読み\nチャットで回答する", True)
    # The response is a later user action, not a worker waiting synchronously.
    # Its record sits on a separate row; the diagram abstracts API/worker internals.
    d.action("record", "system", 775, 885, 285, 60, "対話と評価可能な\n回答を記録する")
    # Extend partitions so both outcomes finish within the same responsibility.
    for lane in ("professor", "system", "student"):
        d.root.find(f"mxCell[@id='{lane}']/mxGeometry").set("height", "880")
    d.final("skip-final", 581, 900)
    d.final("record-final", 903.5, 987)
    d.root.find("mxCell[@id='canvas']/mxGeometry").set("height", "1100")
    d.document.find("diagram/mxGraphModel").set("pageHeight", "1100")

    d.edge("flow-01", "start", "publish", (250, 242), (250, 270))
    d.edge("flow-02", "publish", "join", (415, 313), (1130, 313))
    d.edge("flow-03", "join", "save-conversation", (1325, 356), (1025, 397), ((1325, 397),))
    d.edge("flow-03b", "save-conversation", "save-goal", (837.5, 429), (837.5, 459))
    d.edge("flow-04", "save-goal", "due", (837.5, 523), (837.5, 490))
    d.edge("flow-05", "due", "choose", (837.5, 568), (837.5, 598))
    d.edge("flow-06", "choose", "decision", (837.5, 676), (837.5, 704))
    d.edge("flow-no", "decision", "skip", (813.5, 728), (595, 789), ((595, 728),))
    d.edge("flow-yes", "decision", "deliver", (837.5, 752), (917.5, 789), ((837.5, 771), (917.5, 771)))
    d.edge("flow-07", "deliver", "reply", (1060, 821), (1130, 821))
    d.edge("flow-08", "reply", "record", (1325, 853), (1060, 915), ((1325, 915),))
    d.edge("flow-09", "skip", "skip-final", (595, 853), (595, 900))
    d.edge("flow-10", "record", "record-final", (917.5, 945), (917.5, 987))
    d.text("guard-no", 610, 695, 195, 32, "[配信不可]", 21)
    d.text("guard-yes", 882, 730, 185, 32, "[配信可]", 21)
    d.text("available", 605, 276, 370, 30, "公開済みの授業を利用できる", 21)
    d.box("no-question", 1140, 492, 380, 106, "この時点で、学生は\nまだ質問していない。", "shape=note;size=18;fillColor=#F7F9FB;align=left;spacing=18;", "student", 24)
    d.box("scope-note", 85, 433, 330, 195, "開始の仕組み\n\nこの図：復習時期を自動検出\n\n別経路：教授が日時を指定して予約", "shape=note;size=18;align=left;spacing=18;", "professor", 22)
    d.box("preconditions", 85, 710, 330, 205, "実行の条件\n\n受講登録・教材公開・自律支援・受信同意が有効。\n\n条件を満たさない場合は送らない。", "shape=note;size=18;align=left;spacing=18;", "professor", 22)
    d.text("end-note", 110, 1050, 1380, 34, "終端は、このシナリオの終了を表す。学習目標の完了や、システム全体の停止を意味しない。", 21)

    # Associate guards with their control-flow edges, so labels move with arrows.
    for label_id, edge_id, offset_x, offset_y in [("guard-no", "flow-no", 0, -22), ("guard-yes", "flow-yes", 104, -5)]:
        label = d.root.find(f"mxCell[@id='{label_id}']")
        edge = d.root.find(f"mxCell[@id='{edge_id}']")
        edge.set("value", label.get("value"))
        edge.set("style", edge.get("style") + f"html=0;fontFamily={FONT};fontSize=21;fontColor={INK};labelBackgroundColor=#FFFFFF;")
        geom = edge.find("mxGeometry")
        ET.SubElement(geom, "mxPoint", x=str(offset_x), y=str(offset_y), attrib={"as": "offset"})
        d.root.remove(label)

    # Make room for separate request-time conversation and worker-time goal creation.
    for cell in d.root.findall("mxCell[@vertex='1']"):
        ident = cell.get("id")
        if ident in d.bounds and d.bounds[ident][1] >= 490:
            geom = cell.find("mxGeometry")
            geom.set("y", str(float(geom.get("y")) + 60))
    for point in d.root.findall("mxCell[@edge='1']/mxGeometry/Array/mxPoint"):
        if float(point.get("y")) >= 490:
            point.set("y", str(float(point.get("y")) + 60))
    for lane in ("professor", "system", "student"):
        d.root.find(f"mxCell[@id='{lane}']/mxGeometry").set("height", "940")
    d.root.find("mxCell[@id='canvas']/mxGeometry").set("height", "1160")
    d.document.find("diagram/mxGraphModel").set("pageHeight", "1160")

    # Prefix identifiers to avoid collisions with draw.io's JavaScript object keys.
    for cell in d.root.findall("mxCell"):
        for attribute in ("id", "parent", "source", "target"):
            value = cell.get(attribute)
            if value and value not in {"0", "1"}:
                cell.set(attribute, "pf-" + value)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "01-agent-initiated-activity-ja.drawio"
    ET.indent(d.document)
    ET.ElementTree(d.document).write(target, encoding="utf-8", xml_declaration=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    source = build()
    if args.export:
        for fmt in ("png", "svg", "pdf"):
            result = subprocess.run([
                "/Applications/draw.io.app/Contents/MacOS/draw.io", "--export",
                "--format", fmt, "--scale", "1.5", "--embed-diagram",
                "--output", str(source.with_suffix("." + fmt)), str(source),
            ], check=True, capture_output=True, text=True)
            output = source.with_suffix("." + fmt)
            if "Export failed" in result.stdout + result.stderr or not output.is_file():
                raise RuntimeError(f"draw.io did not export {fmt}: {result.stdout} {result.stderr}")
    print(source)


if __name__ == "__main__":
    main()
