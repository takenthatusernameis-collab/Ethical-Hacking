import re
with open('README.md') as f:
    content = f.read()

# Find all bullet points that start with **- **...: \`<cmd>\` command
matches = re.findall(r'^-\s+\*\*[^:]+:\s+`([a-z0-9]+)`\s+command', content, re.MULTILINE)
for m in sorted(matches):
    print(m)
print('---')
print(len(matches), 'commands found')

# Also get CLI commands
import subprocess
result = subprocess.run(['python', '-m', 'ethscan', '--help'], capture_output=True, text=True)
cli_commands = []
in_commands = False
for line in result.stdout.split('\n'):
    if 'Commands:' in line:
        in_commands = True
        continue
    if in_commands and line.strip() and not line.startswith(' '):
        break
    if in_commands and line.strip():
        cmd = line.strip().split()[0]
        cli_commands.append(cmd)

print('CLI commands:', sorted(cli_commands))
print(len(cli_commands), 'CLI commands')

readme_commands = set(matches)
cli_commands_set = set(cli_commands)

print('In README but not CLI:', readme_commands - cli_commands_set)
print('In CLI but not README:', cli_commands_set - readme_commands)