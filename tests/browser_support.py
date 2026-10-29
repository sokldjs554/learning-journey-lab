"""Optional, narrowly scoped CA pin for managed QA proxies; never blanket TLS bypass."""
import os,re

def browser_args():
    args=['--no-sandbox']
    pin=os.environ.get('BROWSER_CA_SPKI')
    if pin:
        if not re.fullmatch(r'[A-Za-z0-9+/]{43}=',pin):raise ValueError('Invalid SHA256 SPKI pin')
        args.append('--ignore-certificate-errors-spki-list='+pin)
    return args
