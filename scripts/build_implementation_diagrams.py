"""Build implementation-linked UML review figures and exact source excerpts."""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
from pathlib import Path
import subprocess
import textwrap
import xml.etree.ElementTree as ET

from scripts.build_product_first_activity import Activity, FONT, INK


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/presentation/diagrams/implementation"


def source_function(path: str, qualified_name: str) -> tuple[str, int]:
    text = (ROOT / path).read_text()
    node = ast.parse(text)
    for name in qualified_name.split("."):
        node = next(child for child in node.body if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name)
    return textwrap.dedent("\n".join(text.splitlines()[node.lineno-1:node.end_lineno])), node.lineno


def page(name: str, title: str, scope: str, width: int, height: int) -> Activity:
    d = Activity()
    diagram = d.document.find("diagram")
    diagram.set("id", name)
    diagram.set("name", title)
    model = diagram.find("mxGraphModel")
    model.set("pageWidth", str(width))
    model.set("pageHeight", str(height))
    d.box("canvas", 0, 0, width, height, "", "strokeColor=none;fillColor=#FFFFFF;")
    d.text("title", 50, 25, width-100, 62, title, 34, True)
    d.text("scope", 50, 99, width-100, 52, scope, 22)
    return d


def initial(d: Activity, ident: str, x: float, y: float) -> None:
    d.box(ident, x, y, 24, 24, "", f"ellipse;fillColor={INK};")


def final(d: Activity, ident: str, x: float, y: float) -> None:
    d.box(ident, x, y, 28, 28, "", "ellipse;")
    d.box(ident+"-inner", x+6, y+6, 16, 16, "", f"ellipse;fillColor={INK};")


def worker_cycle() -> Activity:
    d = page("02-worker-cycle-ja", "自律支援ワーカーの実行サイクル", "UMLアクティビティ図 ＋ 実コード ｜ scripts/autonomous_tutoring_worker.py", 1600, 1060)
    initial(d, "start", 303, 181)
    d.box("merge", 301, 243, 28, 28, "", "rhombus;")
    d.action("observe", "1", 105, 310, 420, 86, "学習目標・支援の機会を作成\nobserve_events()")
    d.action("governed", "1", 105, 435, 420, 110, "期限の来た自律ジョブを実行\nGovernedAutonomyService\n.process_due()", True)
    d.action("scheduled", "1", 105, 585, 420, 110, "教授の予約配信などを処理\nProactiveOutreachService\n.process_due()")
    d.box("once", 289, 738, 52, 52, "", "rhombus;")
    d.action("sleep", "1", 65, 842, 240, 80, "次の巡回まで待つ\ntime.sleep()")
    final(d, "end", 446, 880)
    d.edge("e1", "start", "merge", (315, 205), (315, 243))
    d.edge("e2", "merge", "observe", (315, 271), (315, 310))
    d.edge("e3", "observe", "governed", (315, 396), (315, 435))
    d.edge("e4", "governed", "scheduled", (315, 545), (315, 585))
    d.edge("e5", "scheduled", "once", (315, 695), (315, 738))
    d.edge("repeat", "once", "sleep", (315, 790), (185, 842), ((315, 814), (185, 814)))
    d.edge("one-shot", "once", "end", (341, 764), (460, 880), ((460, 764),))
    d.edge("loop", "sleep", "merge", (65, 882), (301, 257), ((35, 882), (35, 257)))
    d.text("repeat-guard", 67, 785, 238, 32, "[--once なし]", 20)
    d.text("one-guard", 372, 717, 230, 32, "[--once 指定]", 20)
    d.text("code-heading", 655, 185, 890, 50, "実コード：_process_once() の処理順", 26, True)
    excerpt, _ = source_function("scripts/autonomous_tutoring_worker.py", "_process_once")
    body = textwrap.dedent("\n".join(excerpt.splitlines()[1:]))
    code_html = '<pre style="margin:0;white-space:pre;font-family:Menlo,monospace;font-size:18px;line-height:1.45">' + html.escape(body) + '</pre>'
    d.box("code", 655, 255, 890, 235, code_html, "html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;spacing=0;fontFamily=Menlo;fontSize=18;", font=18)
    d.text("job-detail-title", 655, 535, 890, 45, "自律ジョブ内で実際に行うこと", 26, True)
    d.text("job-detail", 655, 605, 890, 240,
        "期限切れを処理し、再実行予約を支援の機会に変換する。\n対象の機会を一時的に占有し、教材と権限を読み込む。\n行動の判定・内容生成・検証を行う。\nメッセージの配信後、ジョブ結果と次回予約を保存する。", 23)
    d.text("precondition", 655, 876, 890, 84, "実行条件：staging構成、ワーカー有効化。\n起動中は、ブラウザ操作とは別のプロセスで巡回する。", 21)
    d.text("foot", 50, 986, 1500, 43, "既定は1回の処理終了後に30秒待機。処理時間も加わるため、厳密な30秒周期ではない。", 22)
    return d


def lifeline(d: Activity, ident: str, x: int, label: str, bottom: int) -> None:
    d.box(ident, x-190, 192, 380, bottom-192, label,
        "shape=umlLifeline;perimeter=lifelinePerimeter;participant=rectangle;size=100;fontSize=22;")


def message(d: Activity, ident: str, source: str, target: str, sx: int, tx: int, y: int, label: str, reply: bool = False) -> None:
    d.edge(ident, source, target, (sx, y), (tx, y))
    cell = d.root.find(f"mxCell[@id='{ident}']")
    cell.set("value", label)
    cell.set("style", cell.get("style") + f"html=0;fontFamily=Menlo;fontSize=21;fontColor={INK};labelBackgroundColor=#FFFFFF;" + ("dashed=1;endArrow=open;endFill=0;" if reply else "endArrow=block;endFill=1;"))
    ET.SubElement(cell.find("mxGeometry"), "mxPoint", x="0", y="-19", attrib={"as": "offset"})


def delivery_sequence() -> Activity:
    d = page("03-delivery-commit-ja", "配信の保存と、ジョブ結果の保存", "UMLシーケンス図 ｜ _process_claimed() → graph.run() → _deliver() → commit_autonomous_job()", 2100, 1580)
    xs = {"service": 250, "graph": 780, "outreach": 1300, "store": 1820}
    labels = {"service": "GovernedAutonomyService", "graph": "GovernedAutonomous\nTutoringGraph", "outreach": "ProactiveOutreachService", "store": "SQLiteStudentRepository"}
    for ident, x in xs.items():
        lifeline(d, ident, x, labels[ident], 1450)
    def msg(ident, a, b, y, label, reply=False):
        message(d, ident, a, b, xs[a], xs[b], y, label, reply)
    msg("run", "service", "graph", 350, "run(job)")
    msg("graph-result", "graph", "service", 415, "AutonomousJobResult", True)
    d.text("graph-note", 845, 340, 1170, 76, "行動選択・権限確認・生成・検証を完了。\nこの時点では受信箱への保存はまだ行っていない。", 22)
    msg("schedule", "service", "outreach", 492, "schedule_trigger(idempotency_key=K, ...)")
    msg("trigger", "outreach", "service", 557, "trigger: 新規予約 または 同じKの既存予約", True)
    msg("process", "service", "outreach", 637, "process_trigger(trigger.id, now=instant)")
    d.box("alt-frame", 1080, 680, 960, 585, "", "fillColor=none;")
    d.box("alt-label", 1080, 680, 75, 37, "alt", "shape=umlFrame;align=left;fillColor=#FFFFFF;fontSize=22;")
    d.text("pending", 1170, 690, 830, 42, "[予約がpending、配信条件を満たす]", 22)
    msg("materialize", "outreach", "store", 782, "materialize_proactive_message(...)")
    msg("inserted", "store", "outreach", 850, "bool / ProactiveDeliveryConflictError", True)
    d.text("transaction", 1370, 874, 610, 66, "保存時に権限・同意・公開版・頻度を再確認。\n不成立なら保存を拒否する。成立時は引用も同時保存。", 19)
    d.box("separator-1", 1080, 961, 960, 1, "", "strokeColor=none;fillColor=none;")
    d.edge("sep1", "alt-frame", "alt-frame", (1080, 961), (2040, 961))
    c = d.root.find("mxCell[@id='sep1']"); c.set("style", c.get("style") + "endArrow=none;dashed=1;")
    d.text("duplicate-guard", 1170, 976, 830, 42, "[同じ予約から既にメッセージを保存済み]", 22)
    msg("existing", "outreach", "store", 1051, "get_proactive_message_for_trigger(id)")
    msg("existing-result", "store", "outreach", 1115, "existing_message", True)
    d.edge("sep2", "alt-frame", "alt-frame", (1080, 1150), (2040, 1150))
    c = d.root.find("mxCell[@id='sep2']"); c.set("style", c.get("style") + "endArrow=none;dashed=1;")
    d.text("suppression", 1170, 1163, 830, 83, "[まだ時刻前／配信不可]\nnot-due、suppressed、deferred-quiet-hours等を返す。", 22)
    msg("delivery-result", "outreach", "service", 1311, "delivery_result（配信／既存再利用／見送り）", True)
    d.box("crash-note", 75, 1351, 1950, 57, "ここで停止すると、メッセージだけが保存済みになり得る。再試行では同じKと元の配信期間を再利用する。", "shape=note;size=16;align=left;fillColor=#F6F8FB;", font=22)
    msg("commit", "service", "store", 1450, "commit_autonomous_job(result)")
    d.text("commit-note", 650, 1484, 1380, 53, "計画・行動・結果・次回予約などを保存。配信成功時に目標の試行回数を加算する。", 21)
    d.text("scope-note", 50, 1538, 1980, 34, "_deliver()はno-action等では配信処理を呼ばない。図は配信処理に進む場合を展開し、保存・再利用・見送りを示す。", 20)
    return d


def write_page(d: Activity) -> Path:
    name = d.document.find("diagram").get("id")
    for cell in d.root.findall("mxCell"):
        for key in ("id", "parent", "source", "target"):
            value = cell.get(key)
            if value and value not in {"0", "1"}:
                cell.set(key, name+"-"+value)
    path = OUT / (name+".drawio")
    ET.indent(d.document)
    ET.ElementTree(d.document).write(path, encoding="utf-8", xml_declaration=True)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [write_page(worker_cycle()), write_page(delivery_sequence())]
    if args.export:
        for path in paths:
            for fmt in ("png", "svg", "pdf"):
                result = subprocess.run([
                    "/Applications/draw.io.app/Contents/MacOS/draw.io", "--export", "--format", fmt,
                    "--scale", "1.5", "--embed-diagram", "--output", str(path.with_suffix("."+fmt)), str(path),
                ], capture_output=True, text=True, check=True)
                if "Export failed" in result.stdout + result.stderr or not path.with_suffix("."+fmt).is_file():
                    raise RuntimeError(result.stdout + result.stderr)
    sources = ["scripts/autonomous_tutoring_worker.py", "src/digital_twin/student/autonomy_service.py", "src/digital_twin/student/autonomy_runtime.py", "src/digital_twin/student/proactive.py", "src/digital_twin/student/repository.py"]
    manifest = "\n".join(f"{hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}  {path}" for path in sources)
    (OUT / "source-sha256.txt").write_text(manifest+"\n")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
