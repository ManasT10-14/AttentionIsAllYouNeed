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
    initial['input_policy']='Only these seven PDF paths and company context. C08 is distributed separately for live arrival.'
    paths.append(archive('odin-initial-upload-v2.zip',
        ['inputs/company_context.md','inputs/company_context.json']+[c['file'] for c in initial['contracts']],
        {'manifest.json':json.dumps(initial,indent=2)+'\n'}))
    paths.append(archive('odin-live-arrival-v2.zip',['inputs/contracts/C08.pdf','inputs/events/ARR-01.json','inputs/emails/ARR-01/UPLOAD1.eml','inputs/emails/ARR-01/UPLOAD1.txt']))
    evaluator=[p.relative_to(C).as_posix() for folder in ['oracle','runtime_specs'] for p in (C/folder).rglob('*') if p.is_file()]
    paths.append(archive('odin-evaluator-only-v2.zip',evaluator+['VALIDATION.md']))
    # Verify the distribution boundaries rather than trusting file selection alone.
    for path in paths[:3]:
        with ZipFile(path) as z:
            assert z.testzip() is None
            assert not any(x.startswith(('oracle/','tools/','runtime_specs/')) for x in z.namelist())
    with ZipFile(paths[1]) as z:
        assert len([n for n in z.namelist() if n.endswith('.pdf')])==7
        assert 'inputs/contracts/C08.pdf' not in z.namelist()
        assert not any(n.startswith(('inputs/events/','inputs/scenarios/','inputs/emails/')) for n in z.namelist())
    with ZipFile(paths[2]) as z:
        assert [n for n in z.namelist() if n.endswith('.pdf')]==['inputs/contracts/C08.pdf']
    with ZipFile(paths[3]) as z:
        assert z.testzip() is None
        assert not any(n.startswith('inputs/') for n in z.namelist())
    checksum=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths)
    (OUT/'SHA256SUMS.txt').write_text(checksum,encoding='utf-8')
    (OUT/'START_HERE.txt').write_text(
        'ODIN CORPUS V2\n\n'
        'Manual baseline: odin-initial-upload-v2.zip (seven PDFs and company context).\n'
        'Live arrival: odin-live-arrival-v2.zip (C08 and receipt observation).\n'
        'Agent teammate / trusted feed loader: odin-runner-inputs-v2.zip.\n'
        'Evaluation teammate only: odin-evaluator-only-v2.zip. Never ingest it into agents.\n\n'
        'Runner assets contain future observations and C08 bytes: release by received_at,\n'
        'and enforce initial_contract_ids. Do not pass whole event schedules to agents.\n'
        '45 scenarios are isolated alternatives; reset before each. All amounts INR, times UTC.\n'
        '64 email fixtures include .eml and copy-ready .txt forms; 16 event types covered.\n'
        'Contract PDFs have Key: Value covers and numeric clauses, without version labels.\n'
        'Contract amendment is embedded in C06; exactly eight PDFs in the full portfolio.\n'
        'Source and integration docs: ../AttentionIsAllYouNeed/corpus/README.md and INTERFACE.md.\n'
        'Gmail/OAuth implementation requirements are in runtime_specs/gmail_integration.md.\n'
        'Inputs and citations validated; no Odin pipeline, UI or Gmail connection tested.\n',encoding='utf-8')
    print('\n'.join(str(p) for p in paths))
    print('Archive isolation and CRC checks: PASS')


if __name__=='__main__':
    build()
