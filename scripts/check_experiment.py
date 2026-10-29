"""Reproducible synthetic engineering checks and hypothetical recruitment scenarios."""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from math import ceil, sqrt
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from journey.experiment_readiness import evaluate, recruitment_days


def build(report_path):
    source = json.loads(Path(report_path).read_text())['experiment']
    scenarios = []
    for sample in source['samples']:
        p, delta = sample['baseline'], sample['mde']
        q, bar = p + delta, p + delta / 2
        z = NormalDist()
        independently_calculated = ceil(((z.inv_cdf(.975) * sqrt(2 * bar * (1 - bar))
            + z.inv_cdf(.8) * sqrt(p * (1 - p) + q * (1 - q))) / delta) ** 2)
        if independently_calculated != sample['per_arm']:
            raise ValueError('Existing sample size disagrees with independent stdlib calculation')
        for inflow in (50, 100, 500):
            scenarios.append(sample | {'hypothetical_daily_eligible': inflow}
                | recruitment_days(sample['per_arm'], inflow, 1))
    t0 = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    assignments = [dict(assignment_id=f'a{i}', user_id=f'u{i}', experiment_id='resume-v1',
                       variant='control' if i < 10 else 'treatment', assigned_at=t0)
                   for i in range(20)]
    events = [dict(event_id=f'e{i}', assignment_id=a['assignment_id'], user_id=a['user_id'],
                   experiment_id='resume-v1', variant=a['variant'], kind='learning',
                   occurred_at=t0+timedelta(days=7), ingested_at=t0+timedelta(days=7,hours=1))
              for i, a in enumerate(assignments) if i in (0,1,2,10,11,12)]
    config = dict(experiment_id='resume-v1', enrollment_start=t0,
                  enrollment_end=t0+timedelta(days=7), as_of=t0+timedelta(days=22),
                  watermark=t0+timedelta(days=21), late_buffer=timedelta(days=1),
                  target_per_arm=10, checkpoint='final', srm_alpha=.001,
                  guardrail_max_increase={'playback_error':.01, 'refund':.01})
    clean = evaluate(assignments=assignments, events=events, **config)
    bad = evaluate(assignments=assignments+[assignments[0]|{'assignment_id':'cross', 'variant':'treatment'}],
                   events=events, **config)
    late = evaluate(assignments=assignments,events=[events[0]|{'ingested_at':t0+timedelta(days=10)}],**config)
    assert clean['status'] == 'ready_for_review' and clean['difference'] == 0
    assert bad['arms'] is None and bad['difference'] is None
    assert late['difference'] is None and 'late_arrival' in late['reasons']
    return dict(type='synthetic_engineering_validation_not_live_experiment',
                actual_participants=0, actual_service_effect=None,
                actual_service_baseline=None, actual_daily_eligible=None,
                hypothetical_thresholds={'srm_alpha':.001, 'guardrail_max_increase':.01, 'late_buffer_days':1},
                window='elapsed UTC [T0+7d, T0+14d)',
                synthetic_cases={'clean':clean,'cross_variant':bad,'late_arrival':late},
                sample_size_crosscheck='all existing rows match independent NormalDist calculation',
                recruitment_scenarios=scenarios)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, default=ROOT/'reports/report.json')
    parser.add_argument('--output', type=Path, default=ROOT/'reports/experiment-readiness.json')
    args = parser.parse_args()
    result = build(args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print('Synthetic contract checks passed; 18 hypothetical scenarios; real experiments: 0.')
