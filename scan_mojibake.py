# -*- coding: utf-8 -*-
import os, re

# All mojibake patterns
patterns = [
    'ÃƒÂ¶', 'ÃƒÂ¼', 'ÃƒÂ§', 'ÃƒÂ±', 'ÃƒÂ ', 'ÃƒÂ¨', 'ÃƒÂ©', 'ÃƒÂª',
    'kàƒÂ¶pràƒÂ¼', 'saàƒÂ¸lar', 'deà„Å¸', 'tàƒÂ¼rk',
    'Ã†Å¸', 'Ã…Å¸', 'Ã‡', 'Ã–', 'Ãœ', 'Ã†', 'Ã±', 'Ã§', 'Ã¶', 'Ã¼',
    'àƒÂ ', 'à„Å¸',
]

scores = []
root = r'c:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner'

for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ['venv', 'venv_test', '__pycache__', '.git', 'chroma_db']]
    
    for f in files:
        if not f.endswith(('.py', '.js', '.ts', '.html', '.json', '.md')):
            continue
            
        path = os.path.join(dirpath, f)
        try:
            with open(path, 'rb') as fh:
                content = fh.read()
            text = content.decode('utf-8', errors='replace')
            
            count = sum(text.count(p) for p in patterns)
            if count > 0:
                scores.append((count, path))
        except:
            pass

scores.sort(key=lambda x: -x[0])
print('Files with mojibake:')
for count, path in scores[:50]:
    print(f'{count:4}: {path}')
