"""Create reviewed distribution boundaries; never publish or send files."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'corpus'
OUT=ROOT.parent/'deliverables'


def archive(name, files, extras=None):
    path=OUT/name
    with ZipFile(path,'w',compression=ZIP_DEFLATED) as z:
        for relative in sorted(files):
            p=C/relative
            info=ZipInfo(relative,date_time=(2027,1,15,0,0,0))
            info.compress_type=ZIP_DEFLATED
            z.writestr(info,p.read_bytes())
        for relative,data in sorted((extras or {}).items()):
            info=ZipInfo(relative,date_time=(2027,1,15,0,0,0));info.compress_type=ZIP_DEFLATED
            z.writestr(info,data)
    return path


def build():
    OUT.mkdir(exist_ok=True)
    paths=[]
    inputs=[p.relative_to(C).as_posix() for p in (C/'inputs').rglob('*') if p.is_file()]
    paths.append(archive('odin-runner-inputs-v2.zip',['manifest.json']+inputs))
    manifest=json.loads((C/'manifest.json').read_text(encoding='utf-8'))
    initial=deepcopy(manifest)
    initial['stage']='manual_initial_upload'
    initial['contracts']=[c for c in initial['contracts'] if c['initial']]
    initial.pop('scenario_index')
    initial.pop('email_fixture_index')
    initial['input_policy']='Only these fourteen PDF paths and company context. C08 is distributed separately for live arrival.'
    paths.append(archive('odin-initial-upload-v2.zip',
        ['inputs/company_context.md','inputs/company_context.json']+[c['file'] for c in initial['contracts']],
        {'manifest.json':json.dumps(initial,indent=2)+'\n'}))
    paths.append(archive('odin-live-arrival-v2.zip',['inputs/contracts/C08.pdf','inputs/events/ARR-01.json','inputs/emails/ARR-01/UPLOAD1.eml','inputs/emails/ARR-01/UPLOAD1.txt']))
    evaluator=[p.relative_to(C).as_posix() for folder in ['oracle','runtime_specs'] for p in (C/folder).rglob('*') if p.is_file()]
    paths.append(archive('odin-evaluator-only-v2.zip',evaluator+['VALIDATION.md']))
    golden=[p.relative_to(C).as_posix() for p in (C/'oracle/golden').rglob('*') if p.is_file()]
    paths.append(archive('odin-agent-golden-dataset.zip',golden))
    (OUT/'agent_goldens.jsonl').write_bytes((C/'oracle/golden/agent_goldens.jsonl').read_bytes())
    # Verify the distribution boundaries rather than trusting file selection alone.
    for path in paths[:3]:
        with ZipFile(path) as z:
            assert z.testzip() is None
            assert not any(x.startswith(('oracle/','tools/','runtime_specs/')) for x in z.namelist())
    with ZipFile(paths[1]) as z:
        assert len([n for n in z.namelist() if n.endswith('.pdf')])==14
        assert 'inputs/contracts/C08.pdf' not in z.namelist()
        assert not any(n.startswith(('inputs/events/','inputs/scenarios/','inputs/emails/')) for n in z.namelist())
    with ZipFile(paths[2]) as z:
        assert [n for n in z.namelist() if n.endswith('.pdf')]==['inputs/contracts/C08.pdf']
    for path in paths[3:]:
        with ZipFile(path) as z:
            assert z.testzip() is None
            assert not any(n.startswith('inputs/') for n in z.namelist())
    checksum=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths+[OUT/'agent_goldens.jsonl'])
    (OUT/'SHA256SUMS.txt').write_text(checksum,encoding='utf-8')
    (OUT/'START_HERE.txt').write_text(
        'ODIN CORPUS V2\n\n'
        'Exactly three companies: Aurora Software, Forge Electronics and Willow Housing.\n'
        'Fifteen contracts: eight Aurora/Forge and seven Aurora/Willow.\n'
        'Different manuscripts, clause structures, openings and tables; fifteen distinct effective dates.\n\n'
        'Manual baseline: odin-initial-upload-v2.zip (fourteen PDFs and company context).\n'
        'Live arrival: odin-live-arrival-v2.zip (C08 and receipt observation).\n'
        'Agent teammate / trusted feed loader: odin-runner-inputs-v2.zip.\n'
        'Evaluation teammate only: odin-evaluator-only-v2.zip. Never ingest it into agents.\n\n'
        'Agent input/output goldens: odin-agent-golden-dataset.zip (evaluator only).\n'
        'Start with oracle/golden/README.md and agent_io_matrix.csv inside that ZIP.\n'
        'Combined JSONL: agent_goldens.jsonl next to this file (384 records).\n'
        'Per-agent and companion JSONL files are also inside the golden dataset ZIP.\n'
        'Six agents, 384 scenario vectors, 15 extraction records and 36 worked examples.\n'
        'Expected outputs are authored assertions, not recorded agent executions.\n\n'
        'Runner assets contain future observations and C08 bytes: release by received_at,\n'
        'and enforce initial_contract_ids. Do not pass whole event schedules to agents.\n'
        '64 scenarios include a full-portfolio demo; reset between alternative runs. All amounts INR, times UTC.\n'
        '94 email fixtures include .eml and copy-ready .txt forms; 16 event types covered.\n'
        'Contract PDFs have Key: Value covers and numeric clauses, without version labels.\n'
        'See portfolio-preview.png for all fifteen document covers.\n'
        'Contract amendment is embedded in C06; exactly fifteen PDFs in the full portfolio.\n'
        'Evaluator-only conflict_matrix.csv and remedy_catalog.json describe planted conflicts and consequences.\n'
        'Source and integration docs: ../AttentionIsAllYouNeed/corpus/README.md and INTERFACE.md.\n'
        'Gmail/OAuth implementation requirements are in runtime_specs/gmail_integration.md.\n'
        'Inputs and citations validated; no Odin pipeline, UI or Gmail connection tested.\n',encoding='utf-8')
    print('\n'.join(str(p) for p in paths))
    print('Archive isolation and CRC checks: PASS')


if __name__=='__main__':
    build()
