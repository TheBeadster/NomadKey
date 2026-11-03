"""Optional bounded generator for the ACTUAL nomadnetwork.node destination.

Not invoked during implementation. Agree prefix and compute budget before running.
"""
import argparse,os,re
import RNS
p=argparse.ArgumentParser(); p.add_argument('--prefix',required=True); p.add_argument('--max-attempts',required=True,type=int); p.add_argument('--output',required=True)
a=p.parse_args()
if not re.fullmatch('[0-9a-fA-F]{8}',a.prefix) or not 1<=a.max_attempts<=10000000: p.error('8 hex prefix and explicit 1..10000000 attempt budget required')
if os.path.exists(a.output): p.error('Refusing to overwrite an identity')
for count in range(a.max_attempts):
    identity=RNS.Identity(); destination=RNS.Destination.hash(identity,'nomadnetwork','node').hex()
    if destination.startswith(a.prefix.lower()):
        identity.to_file(a.output); os.chmod(a.output,0o600)
        print(destination[:8]+' '+destination[8:-4]+' '+destination[-4:]); break
else: print('Budget exhausted; no identity saved.')
