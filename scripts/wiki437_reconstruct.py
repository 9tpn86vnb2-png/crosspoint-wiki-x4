#!/usr/bin/env python3
from pathlib import Path
import subprocess

WORKFLOW = Path('.github/workflows/wiki-x4-beta436.yml')
NAMES = [
    'Reconstruct reviewed Wiki 4.3.1',
    'Reconstruct verified Wiki 4.3.3',
    'Reconstruct verified Wiki 4.3.4',
    'Reconstruct verified Wiki 4.3.5',
    'Apply and test Wiki 4.3.6 structured tables',
]

def run_block(name: str, text: str) -> None:
    marker = f'      - name: {name}\n        run: |\n'
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f'missing workflow block: {name}')
    start += len(marker)
    end = text.find('\n      - ', start)
    if end < 0:
        end = len(text)
    block = text[start:end]
    lines = block.splitlines()
    script = '\n'.join(line[10:] if line.startswith('          ') else line for line in lines) + '\n'
    print(f'== {name} ==', flush=True)
    subprocess.run(['bash', '-lc', script], check=True)

def main() -> None:
    text = WORKFLOW.read_text()
    for name in NAMES:
        run_block(name, text)
    print('Reconstructed verified Wiki 4.3.6 source.', flush=True)

if __name__ == '__main__':
    main()
