"""Deterministic, segmenter-compatible PDFs; never reads evaluator labels."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter, legal
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, KeepTogether, Table, TableStyle, HRFlowable
from contracts import CONTRACTS

ROOT=Path(__file__).resolve().parents[1]
CORPUS=ROOT/'corpus'
PDFS=CORPUS/'inputs/contracts'
PARTIES=[('P01','Aurora Software Private Limited'),('P02','Forge Electronics Private Limited'),('P03','Willow Housing Private Limited')]
SECTORS={'P01':'software','P02':'electronics','P03':'housing'}

# These are publisher layouts, not variants of the contractual terms.
LAYOUTS={
    'C01':dict(name='Technology services standard form',brand='FORGE ELECTRONICS',label='CLOUD SERVICES AGREEMENT',font='Helvetica',bold='Helvetica-Bold',size=10,leading=14.5,margins=(50,50),top=128,space=11,accent='#173c59',paper=A4,cover='shaded',heads='band'),
    'C02':dict(name='Corporate customer agreement',brand='AURORA SOFTWARE',label='CUSTOMER SERVICES',font='Times-Roman',bold='Times-Bold',size=10.7,leading=15,margins=(64,56),top=112,space=12,accent='#244b70',paper=A4,cover='plain',heads='rule'),
    'C03':dict(name='Procurement terms form',brand='FORGE ELECTRONICS',label='PROCUREMENT / SUPPLY TERMS',font='Helvetica',bold='Helvetica-Bold',size=9.8,leading=13.8,margins=(42,42),top=110,space=10,accent='#2c3b32',paper=A4,cover='boxed',heads='rule'),
    'C04':dict(name='Commercial supply agreement',brand='WILLOW HOUSING',label='CONTROLLER SUPPLY AGREEMENT',font='Helvetica',bold='Helvetica-Bold',size=10.2,leading=14.6,margins=(54,48),top=112,space=11,accent='#252a30',paper=letter,cover='plain',heads='band'),
    'C05':dict(name='Traditional legal lease',brand='WILLOW HOUSING',label='OFFICE LEASE',font='Times-Roman',bold='Times-Bold',size=11,leading=16,margins=(70,62),top=108,space=14,accent='#352c27',paper=legal,cover='plain',heads='plain'),
    'C06':dict(name='Software subscription terms',brand='FORGE ELECTRONICS',label='FIRMWARE DEVELOPMENT LICENSE',font='Helvetica',bold='Helvetica-Bold',size=9.9,leading=14.1,margins=(54,54),top=126,space=10,accent='#17655f',paper=A4,cover='shaded',heads='rule'),
    'C07':dict(name='Data governance agreement',brand='AURORA SOFTWARE',label='PROCESSING & CONFIDENTIALITY',font='Helvetica',bold='Helvetica-Bold',size=10.1,leading=14.6,margins=(58,58),top=112,space=12,accent='#475463',paper=A4,cover='boxed',heads='band'),
    'C08':dict(name='Partnership and procurement deed',brand='WILLOW HOUSING',label='SMART BUILDING PARTNERSHIP',font='Times-Roman',bold='Times-Bold',size=10.7,leading=15.5,margins=(72,60),top=118,space=14,accent='#74384b',paper=A4,cover='plain',heads='rule'),
}
SIGNATORIES={'P01':'Mira Sen','P02':'Anil Das','P03':'Kavya Paul'}
for cid,base,name,label in [
    ('C09','C03','Equipment hire deed','EQUIPMENT HIRE DEED'),
    ('C10','C02','Resident portal order form','RESIDENT PORTAL ORDER'),
    ('C11','C08','Milestone statement of work','INTEGRATION STATEMENT OF WORK'),
    ('C12','C04','Facilities work authorisation','EMERGENCY MAINTENANCE ORDER'),
    ('C13','C05','Mutual engineering undertaking','ENGINEERING CONFIDENTIALITY'),
    ('C14','C07','Recovery service schedule','RECOVERY SERVICE SCHEDULE'),
    ('C15','C06','Manufacturer warranty undertaking','AX-7 WARRANTY UNDERTAKING')]:
    LAYOUTS[cid]=dict(LAYOUTS[base],name=name,label=label,
        brand='FORGE ELECTRONICS' if cid in ['C09','C15'] else 'AURORA SOFTWARE' if cid in ['C10','C11','C13','C14'] else 'WILLOW HOUSING')


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')


def clause_records(contract):
    records=[]
    if 'articles' in contract:
        for section,heading,clauses in contract['articles']:
            for i,(number,text) in enumerate(clauses):
                records.append(dict(section=section,clause_id=number,heading=heading if i==0 else None,text=text))
        return records
    for n,(label,text) in enumerate(contract['clauses'],1):
        records.append(dict(section=str(n),clause_id=f'{n}.1',heading=label,text=text))
    if contract.get('amendment'):
        for n,(_,label,text) in enumerate(contract['amendment'],1):
            records.append(dict(section='19',clause_id=f'19.{n}',heading='EMBEDDED AMENDMENT' if n==1 else None,text=label+'. '+text))
    return records


def prose(text):
    # Keep a number with its preceding word so wrapping cannot create a false clause start.
    return re.sub(r'(\S)\s+(?=\d)',r'\1&nbsp;',escape(text))


def render(contract, directory=PDFS):
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/(contract['id']+'.pdf')
    profile=LAYOUTS[contract['id']]
    accent=colors.HexColor(profile['accent'])
    left,right=profile['margins'];width,height=profile['paper'];available=width-left-right-12
    body=ParagraphStyle('body',fontName=profile['font'],fontSize=profile['size'],leading=profile['leading'],spaceAfter=profile['space'],alignment=TA_JUSTIFY if profile['font']=='Times-Roman' else TA_LEFT,textColor=colors.HexColor('#20252a'))
    heading=ParagraphStyle('heading',parent=body,fontName=profile['bold'],fontSize=profile['size']+.4,leading=profile['leading'],spaceAfter=7,textColor=accent,alignment=TA_LEFT,
        backColor=colors.HexColor('#edf0f2') if profile['heads']=='band' else None,
        borderPadding=4 if profile['heads']=='band' else 0,
        spaceBefore=4)
    cover_font='Courier' if contract['id']=='C03' else profile['font']
    cover=ParagraphStyle('cover',parent=body,fontName=cover_font,fontSize=9.1,leading=15,spaceAfter=0,alignment=TA_LEFT)
    small=ParagraphStyle('small',parent=body,fontSize=8.5,leading=12,spaceAfter=0,alignment=TA_LEFT)
    doc=BaseDocTemplate(str(path),pagesize=profile['paper'],leftMargin=left,rightMargin=right,topMargin=profile['top'],bottomMargin=58,
        title=contract['title'],author=dict(PARTIES)[contract['parties'][0]],invariant=1)
    names=dict(PARTIES)
    metadata=[('CONTRACT TITLE',contract['title']),('CONTRACT ID',contract['id']),('CONTRACT TYPE',contract['type']),
        ('EFFECTIVE DATE',contract['effective_date']),('PARTY A',names[contract['parties'][0]]+' (the "Company")'),
        ('PARTY B',names[contract['parties'][1]]+' (the "Counterparty")'),('GOVERNING LAW',contract['governing_law'])]
    story=[Paragraph('<b>'+escape(k)+':</b> '+escape(v),cover) for k,v in metadata]+[Spacer(1,24)]
    if contract.get('preamble'):
        label,text=contract['preamble']
        story.append(KeepTogether([Paragraph(escape(label),heading),Paragraph('<i>'+prose(text)+'</i>',body),Spacer(1,8)]))

    def schedules():
        output=[]
        for schedule in contract.get('schedules',[]):
            rows=[schedule['columns']]+schedule['rows']
            count=len(rows[0]);ratios=[.12,.28,.26,.34] if count==4 else [.15,.45,.40]
            table=Table([[Paragraph(prose(cell),small) for cell in row] for row in rows],colWidths=[available*x for x in ratios],hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce5ec')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#aebcc5')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
            caption=schedule.get('kind','SCHEDULE')+' '+schedule['letter']+' - '+schedule['title']
            output.append(KeepTogether([Paragraph(escape(caption),heading),table,Spacer(1,18)]))
        return output

    if contract.get('tables_position')=='front':story.extend(schedules())
    for record in clause_records(contract):
        parts=[]
        if record['heading']:
            parts.append(Paragraph(escape(record['section']+' '+record['heading']),heading))
            if profile['heads']=='rule':
                parts.append(HRFlowable(width='100%',thickness=.4,color=accent,spaceAfter=7))
        parts.append(Paragraph(record['clause_id']+' '+prose(record['text']),body))
        story.append(KeepTogether(parts))
    if contract.get('tables_position')!='front':story.extend(schedules())

    signature_cells=[]
    for party in contract['parties']:
        text='For and on behalf of<br/><b>'+escape(names[party])+'</b><br/><br/>Signature: ________________________<br/>Name: '+SIGNATORIES[party]+'<br/>Date: ____________________________'
        signature_cells.append(Paragraph(text,small))
    signatures=Table([signature_cells],colWidths=[available/2]*2,hAlign='LEFT')
    signatures.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),16),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    story.append(KeepTogether([Spacer(1,16),Paragraph('AUTHORISED REPRESENTATIVES',heading),signatures]))

    def paper(canvas,document):
        canvas.saveState()
        if contract['id']=='C05':
            canvas.setStrokeColor(colors.HexColor('#a89d92'));canvas.setLineWidth(.5);canvas.rect(38,45,width-76,height-70)
        if contract['id']=='C08':
            canvas.setStrokeColor(accent);canvas.setLineWidth(1.2);canvas.line(40,55,40,height-36)
        if contract['id']=='C06':
            canvas.setFillColor(accent);canvas.rect(0,0,7,height,fill=1,stroke=0)
        if document.page==1:
            if contract['id'] in ['C01','C06']:
                canvas.setFillColor(accent);canvas.rect(0,height-99,width,99,fill=1,stroke=0)
            else:
                canvas.setStrokeColor(accent);canvas.setLineWidth(.6);canvas.line(left,height-91,width-right,height-91)
            if profile['cover']!='plain':
                canvas.setFillColor(colors.HexColor('#f2f5f6') if profile['cover']=='shaded' else colors.white)
                canvas.setStrokeColor(colors.HexColor('#b9c4cb'));canvas.setLineWidth(.5)
                canvas.rect(left-3,height-profile['top']-118,width-left-right+6,122,fill=1,stroke=1 if profile['cover']=='boxed' else 0)
        canvas.restoreState()

    def furniture(canvas,document):
        canvas.saveState()
        if document.page==1:
            canvas.setFillColor(colors.white if contract['id'] in ['C01','C06'] else accent)
            canvas.setFont(profile['bold'],21 if contract['id']!='C03' else 18)
            if contract['id']=='C05': canvas.drawCentredString(width/2,height-55,profile['brand'])
            else: canvas.drawString(left,height-47,profile['brand'])
            canvas.setFont(profile['font'],10)
            if contract['id']=='C05': canvas.drawCentredString(width/2,height-76,profile['label'])
            else: canvas.drawString(left,height-73,profile['label'])
        else:
            canvas.setFont(profile['font'],8);canvas.setFillColor(accent)
            canvas.drawString(left,height-35,profile['brand']+'  /  '+contract['id'])
            canvas.setStrokeColor(colors.HexColor('#b8c0c6'));canvas.setLineWidth(.4);canvas.line(left,height-42,width-right,height-42)
        canvas.setStrokeColor(colors.HexColor('#b8c0c6'));canvas.setLineWidth(.4);canvas.line(left,43,width-right,43)
        canvas.setFillColor(colors.HexColor('#5d6670'));canvas.setFont(profile['font'],8)
        canvas.drawString(left,29,contract['id']+'  |  '+profile['label'].title())
        canvas.drawRightString(width-right,29,'Page '+str(document.page))
        canvas.restoreState()
    # Emit the footer after the body so PDF text extraction starts with the cover block.
    doc.afterPage=lambda: furniture(doc.canv,doc)
    first_frame=Frame(left,58,width-left-right,height-profile['top']-58,id='cover')
    body_frame=Frame(left,58,width-left-right,height-63-58,id='body')
    doc.addPageTemplates([PageTemplate(id='first',frames=[first_frame],onPage=paper,autoNextPageTemplate='body'),PageTemplate(id='body',frames=[body_frame],onPage=paper)])
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
        'COMPANY NAME: Aurora Software Private Limited',
        'INDUSTRY: B2B software and electronics integration',
        'HQ / JURISDICTIONS: Bengaluru, India; operates in IN, EU',
        'FISCAL YEAR START: 04-01',
        'BASE CURRENCY: INR',
        'RISK APPETITE: low',
        'APPROVAL THRESHOLD: INR 10,00,000',
        'KEY CONTACTS: aurora-legal@aurora.example, cfo@aurora.example',
        'STRATEGIC PRIORITIES: Reduce vendor lock-in; deliver INT-AX7; protect housing resident data; preserve application and recovery continuity; review high-value project changes.',
        'CRITICAL DEPENDENCIES: Forge provides hosting, controllers, firmware tools, backup-node hire and warranty support. Willow supplies UNIT-5 and maintenance and receives portal, processing and recovery services. C03 supplies the lot sold under C04; UNIT-5 supports C02; C09 nodes support C14. Compare the actual dates and restrictions in these agreements.',
    ])+'\n'
    (CORPUS/'inputs/company_context.md').write_text(context,encoding='utf-8')
    write_json(CORPUS/'inputs/company_context.json',dict(company_id='P01',company_name=PARTIES[0][1],
        industry='B2B software and electronics integration',jurisdictions=['IN','EU'],headquarters='Bengaluru, India',
        fiscal_year_start='04-01',base_currency='INR',risk_appetite='low',approval_threshold_inr='1000000',
        key_contacts=['aurora-legal@aurora.example','cfo@aurora.example'],
        strategic_priorities=['Reduce vendor lock-in','Deliver INT-AX7','Protect resident data','Maintain service and recovery continuity'],
        critical_dependencies=['SVC-ATLAS hosting','AX-7 supply and warranty','UNIT-5 lease and maintenance','EQ-DR01/EQ-DR02 node hire','Resident portal and DS-HOUSING recovery'],
        contract_registry=[dict(contract_id=c['id'],title=c['title'],party_ids=c['parties'],effective_date=c['effective_date'],document_form=c['form']) for c in CONTRACTS if c['id']!='C08'],
        timezone='UTC',baseline_clock='2027-01-15T09:00:00Z',
        parties=[dict(party_id=i,legal_name=n,sector=SECTORS[i]) for i,n in PARTIES],
        initial_records='Only records explicitly supplied in a scenario exist; earlier term balances are outside this dataset.'))
    write_json(CORPUS/'manifest.json',dict(schema_version='2.0',corpus_id='odin-fifteen',stage='pilot' if pilot else 'full',
        root='corpus',context='inputs/company_context.md',structured_context='inputs/company_context.json',contracts=entries,
        initial_contract_ids=[c['contract_id'] for c in entries if c['initial']],held_back_contract_ids=[] if pilot else ['C08'],
        input_policy='Only selected PDFs, company context and released observations; never ingest oracle/ or future schedules.',
        scenario_index='inputs/scenarios/index.json',email_fixture_index='inputs/emails/index.json'))
    print(f'Built {len(selected)} contract PDFs.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true')
    build(parser.parse_args().pilot)
