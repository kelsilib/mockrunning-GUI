import time
import json
from pathlib import Path
import requests

events=[]
last=None
removed=False
started=time.monotonic()
while time.monotonic()-started<100:
    status=requests.get('http://127.0.0.1:18766/api/status',timeout=10).json()
    desktop=status['desktop']
    signature=(tuple(sorted(row['udid'] for row in desktop['usb_devices'])),desktop['usb_error'])
    if signature!=last:
        entry={'time':time.strftime('%Y-%m-%dT%H:%M:%S'),'count':len(desktop['usb_devices']),
               'paired': [row.get('paired') for row in desktop['usb_devices']],
               'developer_mode': [row.get('developer_mode') for row in desktop['usb_devices']],
               'connected_to_location_service': status['connected'],'error':desktop['usb_error']}
        events.append(entry)
        print(json.dumps(entry,ensure_ascii=False),flush=True)
        last=signature
    if not desktop['usb_devices'] and not desktop['usb_error']:
        removed=True
    if removed and desktop['usb_devices']:
        break
    time.sleep(1)
result={'physical_unplug_seen':removed,'physical_reinsert_seen':removed and bool(desktop['usb_devices']),
        'location_commands_sent':False,'events':events}
output = Path(__file__).parent.parent / 'artifacts/usb-physical-test.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
