"""Developer automated REAL OULAD integration; never a human timing study."""
import argparse
import builtins
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import full_operations as ops


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',type=Path,required=True)
    parser.add_argument('--study',type=Path,required=True,help='new disposable folder; existing study is never overwritten')
    args=parser.parse_args();study=args.study.resolve()
    ops.initialize(study,args.raw_dir,'developer_synthetic','retry-input-v2')
    fields={}
    for path in sorted((study/'calibration/stages').glob('*.json')):
        stage=path.stem.split('-',1)[1]
        fields[stage]=ops.fields_for(stage,json.loads(path.read_text()))
    original_input=builtins.input
    try:
        for condition in 'AB':
            state={'stage':None,'command_error':False,'value_error':False,'confirmation_error':False}
            def answer(prompt):
                if 'start 입력' in prompt:return 'start'
                if prompt.startswith('다음 단계 '):
                    state['stage']=prompt.split()[2]
                    if not state['command_error']:
                        state['command_error']=True;return 'rnu'
                    return 'run'
                if prompt.startswith('기록 '):
                    if not state['value_error']:
                        state['value_error']=True;return 'intentional-invalid-value'
                    return str(fields[state['stage']][prompt.split()[1]])
                if 'reviewed 입력' in prompt:
                    if not state['confirmation_error']:
                        state['confirmation_error']=True;return 'intentional-invalid-confirmation'
                    return 'reviewed'
                raise RuntimeError('Unexpected developer-test prompt: '+prompt)
            builtins.input=answer
            ops.run_round(study)
    finally:builtins.input=original_input
    audit=ops.audit_study(study);rows=ops.records(study)
    assert len(rows)==2 and all(r['status']=='complete' for r in rows)
    assert audit['completed_measured']==0 and audit['input_corrections']==4
    assert [len(r['input_corrections']) for r in rows]==[3,1]
    config=json.loads((study/'protocol.json').read_text())
    result={'provenance':'developer_automated_real_OULAD_not_human',
            'input_policy':'retry-input-v2','human_measured_rounds':0,
            'reference_report_sha256':ops.EXPECTED_REPORT,
            'review_fields':config['review_fields_total'],'stages_per_condition':len(ops.STAGES),
            'conditions':[{k:r[k] for k in ['condition','status','invalid_inputs']}|{'corrections':len(r['input_corrections'])} for r in rows],
            'identical_outputs':rows[0]['output_sha256']==rows[1]['output_sha256'],
            'audit':audit['audit'],'all_stage_hashes_match_calibration':True,
            'code_sha256':config['fingerprint']['code_sha256'],
            'interpretation':'Automated inputs test corrections and equality only; no human time saving or comprehension claim.'}
    ops.write_json(ROOT/'reports/operations-v2-validation.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='code_sha256'},ensure_ascii=False))


if __name__=='__main__':main()
