import requests
import time

base_url = 'http://127.0.0.1:5173'

print('[1] Resetting...')
r = requests.post(f'{base_url}/api/simulation/reset')
assert r.status_code == 200, r.text
print('Reset OK.')

print('[2] Starting simulation...')
r = requests.post(f'{base_url}/api/simulation/start')
assert r.status_code == 200, r.text
print('Start OK.')

print('[3] Injecting surge...')
r = requests.post(f'{base_url}/api/simulation/surge')
assert r.status_code == 200, r.text
print('Surge injected.')

print('[4] Waiting for 2 simulation ticks (7 seconds)...')
time.sleep(7)

state = requests.get(f'{base_url}/api/state').json()
print('Current Tick:', state['simulation']['tick'])
h_a = next(h for h in state['hospitals'] if h['id'] == 'H-A')
h_b = next(h for h in state['hospitals'] if h['id'] == 'H-B')
pred_a = next(p for p in state['predictions'] if p['hospital_id'] == 'H-A')
print(f"H-A Stock: {h_a['current_stock']}, Status: {pred_a['status']}, Shortage: {pred_a['time_to_shortage_hours']}h")
print(f"H-B Stock: {h_b['current_stock']}")

recs = [r for r in state['recommendations'] if r['status'] == 'pending']
print('Pending recommendations found:', len(recs))
assert len(recs) > 0, 'No recommendation generated!'
rec = recs[0]
print(f"Recommendation: {rec['from_hospital']} -> {rec['to_hospital']}, qty: {rec['quantity']}")
print(f"Justification: {rec['justification']}")

print(f"[5] Approving recommendation {rec['id']}...")
appr = requests.post(f"{base_url}/api/recommendations/{rec['id']}/approve")
assert appr.status_code == 200, appr.text
state_after = appr.json()['state']
h_a_after = next(h for h in state_after['hospitals'] if h['id'] == 'H-A')
h_b_after = next(h for h in state_after['hospitals'] if h['id'] == 'H-B')
print(f"H-A Stock After: {h_a_after['current_stock']}")
print(f"H-B Stock After: {h_b_after['current_stock']}")
print(f"Shortage hours prevented: {state_after['metrics']['shortage_hours_prevented']}")

print('[6] Testing Replay Endpoint...')
replay = requests.get(f'{base_url}/api/replay').json()
print(f"Replay: Prevented {replay['shortage_hours_prevented']}h, Transferred: {replay['units_transferred']}")

print('[7] Resetting again to verify clean recovery...')
requests.post(f'{base_url}/api/simulation/reset')
state_clean = requests.get(f'{base_url}/api/state').json()
assert state_clean['simulation']['surge_active'] is False
assert len(state_clean['recommendations']) == 0
print('\n=============================================')
print('LIVE HTTP END-TO-END DEMO TEST PASSED 100%!')
print('=============================================')
