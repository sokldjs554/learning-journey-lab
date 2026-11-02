"""Write deterministic, explicitly synthetic subscription evidence."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from journey.subscription_bridge import analyze, fixture


def main():
    data=fixture();result=analyze(data)
    for name,value in [('data/synthetic/subscription_bridge.json',data),('reports/subscription-bridge.json',result)]:
        path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['provenance','mature_cycles','renewed_cycles']},ensure_ascii=False))


if __name__=='__main__':main()
