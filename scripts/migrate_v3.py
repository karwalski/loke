#!/usr/bin/env python3
import glob, re, os

base = '/Users/matthew.watt/loke/loke'
dirs = [
    'packages/core/src/**/*.tk',
    'packages/cli/src/*.tk',
    'packages/shared/src/*.tk',
    'packages/mcp-toke/src/*.tk',
    'packages/mcp-broker/src/*.tk',
    'src/**/*.tk'
]
count = 0
for pattern in dirs:
    for f in glob.glob(os.path.join(base, pattern), recursive=True):
        with open(f, 'r') as fh:
            content = fh.read()
        original = content
        content = content.replace('pub f=', 'f=')
        content = content.replace('pub m.', 'm.')
        content = content.replace('pub let ', 'let ')
        content = re.sub(r'^[ \t]*//.*\n', '', content, flags=re.MULTILINE)
        if content != original:
            with open(f, 'w') as fh:
                fh.write(content)
            count += 1
print(f'Modified {count} files')
