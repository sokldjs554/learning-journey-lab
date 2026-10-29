"""Synthetic developer fixtures: never human productivity observations."""
import copy
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/import_practice.py'
SHA = '675dfa6fa3126da0ba74b5a4b4c4222afff4d950297703f3314788f9135a30db'
ROWS = [dict(rule_id='event_exact_repeat',count=787170,severity='review',status='open',reviewed=True),dict(rule_id='registration_missing_date',count=45,severity='review',status='open',reviewed=True),dict(rule_id='event_unknown_site',count=0,severity='block',status='clear',reviewed=True)]

def fixture():
    rounds = []
    for i, mode in enumerate('ABABBAAB'):
        measured = i >= 2
        rounds.append(dict(mode=mode,phase='measured' if measured else 'practice',outputs=copy.deepcopy(ROWS),omissions=0,errors=0,unreviewed=0,valid=True,machine_generation_ms=0.2 if mode=='B' else 0,timing=dict(started_at=f'2026-10-29T12:00:{i*2:02}.000Z',finished_at=f'2026-10-29T12:00:{i*2+1:02}.000Z',segments=[dict(kind='active',start_ms=0,end_ms=700),dict(kind='manual_pause',start_ms=700,end_ms=1000)],elapsed_ms=1000,task_interval_ms=700,excluded_ms=300) if measured else None))
    return dict(schema_version=1,protocol='three-rule-transfer-v1',snapshot_sha256=SHA,origin='developer_synthetic',environment=dict(user_agent='test',viewport='390x844',context_notes='Synthetic test only'),report_load_ms=1,rounds=rounds)

class ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SCRIPT.exists():
            spec=importlib.util.spec_from_file_location('import_practice',SCRIPT)
            cls.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.module)

    def test_validator_exists(self):
        self.assertTrue(SCRIPT.exists(),'Offline validator not implemented')

    def validate(self,p):
        if not SCRIPT.exists(): self.skipTest('validator not implemented')
        return self.module.validate(p)

    def test_synthetic_validated_but_not_human(self):
        self.assertEqual(self.validate(fixture())['human_measurement'],False)
        self.assertFalse(self.validate(fixture())['comparison_ready'])
        self.assertTrue(self.validate(fixture())['all_measured_rounds_valid'])

    def test_self_report_origin_requires_valid_rounds(self):
        # Synthetic fixture exercising the self-report branch, not a participant record.
        p=fixture();p['origin']='human_self_reported'
        self.assertTrue(self.validate(p)['comparison_ready'])
        p['rounds'][2]['outputs'][0]['count']=1;p['rounds'][2].update(errors=1,valid=False)
        self.assertFalse(self.validate(p)['comparison_ready'])

    def test_tampering_rejected(self):
        changes=[('snapshot',lambda p:p.update(snapshot_sha256='0'*64)),('wrong count',lambda p:p['rounds'][2]['outputs'][0].update(count=1)),('missing count',lambda p:p['rounds'][2]['outputs'][0].pop('count')),('unchecked review',lambda p:p['rounds'][2]['outputs'][0].update(reviewed=False)),('negative time',lambda p:p['rounds'][2]['timing'].update(elapsed_ms=-1)),('overlap',lambda p:p['rounds'][2]['timing']['segments'][1].update(start_ms=600)),('wrong sum',lambda p:p['rounds'][2]['timing'].update(task_interval_ms=800)),('bad order',lambda p:p['rounds'][2].update(mode='B')),('not six',lambda p:p['rounds'].pop()),('missing origin',lambda p:p.pop('origin')),('bool count',lambda p:p['rounds'][2]['outputs'][2].update(count=False)),('NaN',lambda p:p['rounds'][2]['timing'].update(elapsed_ms=float('nan'))),('wall drift',lambda p:p['rounds'][2]['timing'].update(finished_at='2026-10-29T12:30:00.000Z')),('reversed chronology',lambda p:p['rounds'][3].update(timing=copy.deepcopy(p['rounds'][2]['timing'])))]
        for name, change in changes:
            with self.subTest(name=name):
                p=fixture();change(p)
                if not SCRIPT.exists(): self.skipTest('validator not implemented')
                with self.assertRaises(ValueError):self.validate(p)

    def test_honestly_reported_error_retained_as_invalid(self):
        p=fixture();p['rounds'][2]['outputs'][0]['count']=1;p['rounds'][2].update(errors=1,valid=False)
        result=self.validate(p)
        self.assertEqual(result['valid_measured_rounds'],5)
        self.assertFalse(result['comparison_ready'])

    def test_omissions_and_unreviewed_are_separate(self):
        p=fixture();p['rounds'][2]['outputs'][0].update(count=None,reviewed=False);p['rounds'][2].update(omissions=1,unreviewed=1,valid=False)
        self.assertFalse(self.validate(p)['all_measured_rounds_valid'])

if __name__=='__main__':unittest.main()
