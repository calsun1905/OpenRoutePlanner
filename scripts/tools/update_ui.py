import re
import os

# Script scripts/tools/ içinde; proje kökü OpenRoutePlanner
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, '..', '..'))

# 1. Update index.html
tmp_path = os.path.join(_project_root, 'tmp_buttons.html')
with open(tmp_path, 'r', encoding='utf-8') as f:
    buttons_html = f.read()

html_path = os.path.join(_project_root, 'frontend', 'index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Replace everything inside <div class="poi-grid"> ... </div>
import re
new_html = re.sub(
    r'(<div class="poi-grid">).*?(</div>\s*<button class="btn btn-ghost" id="btnClearPois")',
    fr'\1\n{buttons_html}\n            \2',
    html_content,
    flags=re.DOTALL
)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

# 2. Update style.css
css_path = os.path.join(_project_root, 'frontend', 'css', 'style.css')
with open(css_path, 'r', encoding='utf-8') as f:
    css_content = f.read()

new_css = css_content.replace(
    '.poi-grid {\n    display: grid;\n    grid-template-columns: repeat(6, 1fr);\n    gap: 6px;\n}',
    '.poi-grid {\n    display: grid;\n    grid-template-columns: repeat(3, 1fr);\n    gap: 6px;\n    max-height: 250px;\n    overflow-y: auto;\n    padding-right: 4px;\n}\n\n.poi-grid::-webkit-scrollbar {\n    width: 4px;\n}\n.poi-grid::-webkit-scrollbar-thumb {\n    background: var(--text-muted);\n    border-radius: 4px;\n}'
)

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(new_css)

print("index.html and style.css updated successfully.")
