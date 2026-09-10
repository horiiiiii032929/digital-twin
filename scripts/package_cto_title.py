"""Replace the title slide with an Artifact Tool-authored cover, preserving notes."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'reports/generated/cto-title-build'
source=ROOT/'reports/presentation/deck/digital-twin-presentation-cto-natural-script.pptx'
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
with ZipFile(source) as z:parts={n:z.read(n) for n in z.namelist()}
with ZipFile(BUILD/'cover.pptx') as z:new=E.fromstring(z.read('ppt/slides/slide1.xml'))
old=E.fromstring(parts['ppt/slides/slide1.xml']);oldtree=old.find('p:cSld/p:spTree',ns);oldtree.getparent().replace(oldtree,new.find('p:cSld/p:spTree',ns))
parts['ppt/slides/slide1.xml']=E.tostring(old,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(BUILD/'candidate.pptx','w',ZIP_DEFLATED) as z:
 for n,v in parts.items():z.writestr(n,v)
print('Replaced title artwork only; narration, sources and other slides preserved.')
