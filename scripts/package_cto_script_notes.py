"""Apply Artifact Tool-authored note bodies while preserving every other PPTX part."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import json

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/generated/cto-notes-build'
SOURCE = ROOT / 'reports/presentation/deck/digital-twin-presentation-cto-refined.pptx'
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main', 'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}

with ZipFile(SOURCE) as z:
    parts = {name:z.read(name) for name in z.namelist()}
expected = json.loads((BUILD / 'expected-notes.json').read_text())
with ZipFile(BUILD / 'authored-notes.pptx') as z:
    for i in range(1,32):
        name = f'ppt/notesSlides/notesSlide{i}.xml'
        original = E.fromstring(parts[name])
        authored = E.fromstring(z.read(name))
        def body(root):
            shapes = root.xpath('.//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]', namespaces=NS)
            assert len(shapes)==1, (i, 'Expected one notes body')
            return shapes[0]
        old = body(original)
        new = body(authored).find('p:txBody',NS)
        old.replace(old.find('p:txBody',NS),deepcopy(new))
        paragraphs = [''.join(p.itertext()) for p in new.findall('a:p',NS)]
        actual = '\n'.join(paragraphs)
        assert actual==expected[i-1], (i,'Narration mismatch')
        parts[name] = E.tostring(original,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(BUILD/'candidate.pptx','w',ZIP_DEFLATED) as z:
    for name,data in parts.items():z.writestr(name,data)
with ZipFile(SOURCE) as a, ZipFile(BUILD/'candidate.pptx') as b:
    assert set(a.namelist())==set(b.namelist())
    changed = [name for name in a.namelist() if a.read(name)!=b.read(name)]
    assert set(changed)=={f'ppt/notesSlides/notesSlide{i}.xml' for i in range(1,32)}
(BUILD/'preservation-check.json').write_text(json.dumps({'changed_parts':changed,'all_other_parts_byte_identical':True,'notes_match_script':True},indent=2))
print('31 notes updated. All other PPTX parts are byte-identical to the source.')
