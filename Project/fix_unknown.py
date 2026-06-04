import json

# Fix habitat_controller.py
with open('habitat_controller.py', 'r', encoding='utf-8') as f:
    hc_code = f.read()
hc_code = hc_code.replace('return "None (Last State: UNKNOWN)"', 'return "[Last Progress State: None]\\n1. None\\n2. None"')
with open('habitat_controller.py', 'w', encoding='utf-8') as f:
    f.write(hc_code)

# Fix templates/index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()
html_code = html_code.replace('[Last Progress State: UNKNOWN]', '[Last Progress State: None]')
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)

# Fix scenarios.json
with open('scenarios.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for key in data['scenario1']:
    if isinstance(data['scenario1'][key], str):
        data['scenario1'][key] = data['scenario1'][key].replace('[Last Progress State: UNKNOWN]', '[Last Progress State: None]')

with open('scenarios.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)

print('Successfully replaced UNKNOWN with None.')
