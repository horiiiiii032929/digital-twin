"""Attach the local demonstration to the slide's native media poster."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'reports/generated/slide-build'
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','p14':'http://schemas.microsoft.com/office/powerpoint/2010/main'}
def sub(parent,tag,**attrs):return E.SubElement(parent,'{'+NS[tag.split(':')[0]]+'}'+tag.split(':')[1],attrs)
def run():
 with ZipFile(BUILD/'candidate-base.pptx') as z: parts={n:z.read(n) for n in z.namelist()}
 content=json.loads((BUILD/'deck-content.json').read_text())
 number=next(s['number'] for s in content['slides'] if s['kind']=='video')
 slide_path=f'ppt/slides/slide{number}.xml'
 slide=E.fromstring(parts[slide_path])
 pics=slide.findall('.//p:pic',NS)
 assert len(pics) == 1, 'Demo slide must contain exactly one poster image'
 pic=pics[0]
 nv=pic.find('p:nvPicPr',NS); cnv=nv.find('p:cNvPr',NS); spid=cnv.get('id')
 sub(cnv,'a:hlinkClick',action='ppaction://media')
 app=nv.find('p:nvPr',NS)
 sub(app,'a:videoFile',**{'{'+NS['r']+'}link':'rIdDemoVideo'})
 ext=sub(sub(app,'p:extLst'),'p:ext',uri='{DAA4B4D4-6D71-4841-9C94-3DE7FCFBAD2D}')
 sub(ext,'p14:media',**{'{'+NS['r']+'}embed':'rIdDemoMedia'})
 timing=sub(slide,'p:timing'); root=sub(sub(sub(timing,'p:tnLst'),'p:par'),'p:cTn',id='1',dur='indefinite',restart='never',nodeType='tmRoot')
 media=sub(sub(sub(root,'p:childTnLst'),'p:video'),'p:cMediaNode',vol='80000')
 ct=sub(media,'p:cTn',id='2',fill='hold',display='0');sub(sub(ct,'p:stCondLst'),'p:cond',delay='indefinite')
 sub(sub(media,'p:tgtEl'),'p:spTgt',spid=spid)
 parts[slide_path]=E.tostring(slide,xml_declaration=True,encoding='UTF-8',standalone=True)
 relpath=f'ppt/slides/_rels/slide{number}.xml.rels';rels=E.fromstring(parts[relpath]);rns='http://schemas.openxmlformats.org/package/2006/relationships'
 for ident,typ in [('rIdDemoVideo',NS['r']+'/video'),('rIdDemoMedia','http://schemas.microsoft.com/office/2007/relationships/media')]:
  E.SubElement(rels,'{'+rns+'}Relationship',Id=ident,Type=typ,Target='../media/course-demo.mp4')
 parts[relpath]=E.tostring(rels,xml_declaration=True,encoding='UTF-8',standalone=True)
 ct=E.fromstring(parts['[Content_Types].xml']);ctns='http://schemas.openxmlformats.org/package/2006/content-types'
 if not any(x.get('Extension')=='mp4' for x in ct):E.SubElement(ct,'{'+ctns+'}Default',Extension='mp4',ContentType='video/mp4')
 parts['[Content_Types].xml']=E.tostring(ct,xml_declaration=True,encoding='UTF-8',standalone=True)
 video=(ROOT/'reports/generated/autonomous-film/digital-twin-30-day-demo.mp4').read_bytes();parts['ppt/media/course-demo.mp4']=video
 with ZipFile(BUILD/'candidate.pptx','w',ZIP_DEFLATED) as z:
  for n,b in parts.items():z.writestr(n,b)
 (BUILD/'embedded-media.json').write_text(json.dumps({'slide':number,'sha256':hashlib.sha256(video).hexdigest(),'bytes':len(video),'playback':'native click-to-play'},indent=2))
if __name__=='__main__':run()
