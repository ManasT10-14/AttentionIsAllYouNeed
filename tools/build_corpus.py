"""Deterministic, segmenter-compatible PDFs; never reads evaluator labels."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from contracts import CONTRACTS

ROOT=Path(__file__).resolve().parents[1]
CORPUS=ROOT/'corpus'
PDFS=CORPUS/'inputs/contracts'
PARTIES=[('P01','Aurora Systems Private Limited'),('P02','Nimbus Harbor Private Limited'),('P03','Cedar Market Private Limited'),('P04','Forge Vale Private Limited'),('P05','Harbor Works Private Limited'),('P06','Willow Estates Private Limited'),('P07','Lumen Stack Private Limited'),('P08','Quill Data Private Limited')]


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')


def clause_records(contract):
    records=[]
    for n,(label,text) in enumerate(contract['clauses'],1):
        records.append(dict(section=str(n),clause_id=f'{n}.1',heading=label,text=text))
    if contract.get('amendment'):
        for n,(_,label,text) in enumerate(contract['amendment'],1):
            records.append(dict(section='19',clause_id=f'19.{n}',heading='EMBEDDED AMENDMENT' if n==1 else None,text=label+'. '+text))
    return records


def render(contract, directory=PDFS):
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/(contract['id']+'.pdf')
    body=ParagraphStyle('body',fontName='Helvetica',fontSize=10,leading=14.5,spaceAfter=12,textColor=colors.HexColor('#253443'))
    heading=ParagraphStyle('heading',parent=body,fontName='Helvetica-Bold',fontSize=10.5,leading=15,spaceAfter=5)
    cover=ParagraphStyle('cover',parent=body,fontName='Helvetica',fontSize=9.5,leading=15,spaceAfter=0)
    doc=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=46,rightMargin=46,topMargin=42,bottomMargin=54,
        title=contract['title'],author='Aurora Systems Private Limited',invariant=1)
    names=dict(PARTIES)
    metadata=[('CONTRACT TITLE',contract['title']),('CONTRACT ID',contract['id']),('CONTRACT TYPE',contract['type']),
        ('EFFECTIVE DATE',contract['effective_date']),('PARTY A',names[contract['parties'][0]]+' (the "Company")'),
        ('PARTY B',names[contract['parties'][1]]+' (the "Counterparty")'),('GOVERNING LAW',contract['governing_law'])]
    story=[Paragraph(escape(k+': '+v),cover) for k,v in metadata]+[Spacer(1,24)]
    for record in clause_records(contract):
        parts=[]
        if record['heading']:
            parts.append(Paragraph(escape(record['section']+' '+record['heading']),heading))
        parts.append(Paragraph(escape(record['clause_id']+' '+record['text']),body))
        story.append(KeepTogether(parts))
    if contract['id']=='C01':
        story.append(KeepTogether([Paragraph('SCHEDULE A - FEES',heading),
            Paragraph('Row 1 | SVC-ATLAS hosting | INR 200,000 per month | Due on day 5 at 17:00 UTC',body),
            Paragraph('Row 2 | Qualifying incident credit | INR 10,000 | Monthly cap INR 20,000',body)]))

    def footer(canvas,document):
        canvas.saveState();width,_=A4
        canvas.setStrokeColor(colors.HexColor('#d1dbe2'));canvas.line(46,40,width-46,40)
        canvas.setFillColor(colors.HexColor('#657181'));canvas.setFont('Helvetica',8)
        canvas.drawString(46,26,contract['id'])
        canvas.drawRightString(width-46,26,'Page '+str(document.page))
        canvas.restoreState()
    # Emit the footer after the body so PDF text extraction starts with the cover block.
    doc.afterPage=lambda: footer(doc.canv,doc)
    doc.build(story)
    return path


def build(pilot=False):
    PDFS.mkdir(parents=True,exist_ok=True)
    selected=[c for c in CONTRACTS if not pilot or c['id'] in ['C01','C02','C05']]
    entries=[]
    for c in selected:
        path=render(c)
        entries.append(dict(contract_id=c['id'],file='inputs/contracts/'+path.name,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),contract_type=c['type'],
            initial=c['id']!='C08',party_ids=c['parties']))
    context='\n'.join([
        'COMPANY NAME: Aurora Systems Private Limited',
        'INDUSTRY: B2B SaaS and controller supply',
        'HQ / JURISDICTIONS: Bengaluru, India; operates in IN, EU',
        'FISCAL YEAR START: 04-01',
        'BASE CURRENCY: INR',
        'RISK APPETITE: low',
        'APPROVAL THRESHOLD: INR 10,00,000',
        'KEY CONTACTS: aurora-legal@aurora.example, cfo@aurora.example',
        'STRATEGIC PRIORITIES: Reduce vendor lock-in; preserve APP-ATLAS continuity; expand EU services.',
        'CRITICAL DEPENDENCIES: Nimbus SVC-ATLAS hosts APP-ATLAS; Forge supplies AX-7 controllers; staffed UNIT-5 supports Cedar APP-ATLAS commitments.',
    ])+'\n'
    (CORPUS/'inputs/company_context.md').write_text(context,encoding='utf-8')
    write_json(CORPUS/'inputs/company_context.json',dict(company_id='P01',company_name=PARTIES[0][1],
        industry='B2B SaaS and controller supply',jurisdictions=['IN','EU'],headquarters='Bengaluru, India',
        fiscal_year_start='04-01',base_currency='INR',risk_appetite='low',approval_threshold_inr='1000000',
        key_contacts=['aurora-legal@aurora.example','cfo@aurora.example'],
        strategic_priorities=['Reduce vendor lock-in','Preserve APP-ATLAS continuity','Expand EU services'],
        critical_dependencies=['Nimbus SVC-ATLAS','Forge AX-7','UNIT-5 staffed support'],
        timezone='UTC',baseline_clock='2027-01-15T09:00:00Z',
        parties=[dict(party_id=i,legal_name=n) for i,n in PARTIES],
        initial_records='Only records explicitly supplied in a scenario exist; earlier term balances are outside this dataset.'))
    write_json(CORPUS/'manifest.json',dict(schema_version='2.0',corpus_id='odin-eight-v2',stage='pilot' if pilot else 'full',
        root='corpus',context='inputs/company_context.md',structured_context='inputs/company_context.json',contracts=entries,
        initial_contract_ids=[c['contract_id'] for c in entries if c['initial']],held_back_contract_ids=[] if pilot else ['C08'],
        input_policy='Only selected PDFs, company context and released observations; never ingest oracle/ or future schedules.',
        scenario_index='inputs/scenarios/index.json',email_fixture_index='inputs/emails/index.json'))
    print(f'Built {len(selected)} contract PDFs.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true')
    build(parser.parse_args().pilot)
