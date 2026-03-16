def read_state():
    with open('.gsd/STATE.md', 'r', encoding='utf-8') as f:
        return f.read()


def test_state_contains_milestone_and_slice():
    s = read_state()
    assert 'Active Milestone' in s, 'STATE.md içinde "Active Milestone" başlığı yok'
    assert 'M001' in s, 'STATE.md içinde "M001" bulunamadı'
    assert 'Active Slice' in s, 'STATE.md içinde "Active Slice" başlığı yok'
    assert 'S01' in s, 'STATE.md içinde "S01" bulunamadı'


def test_state_has_next_action_paragraph():
    s = read_state()
    assert 'Next Action' in s, 'STATE.md içinde "Next Action" başlığı yok'
    assert 'S01-PLAN.md' in s, 'Next Action içinde S01-PLAN.md referansı bulunamadı'


def test_state_md_has_required_fields():
    """STATE.md içinde zorunlu başlıkların (Active Milestone/Slice/Task/Blockers/Next Action) bulunduğunu doğrula"""
    text = read_state()

    required = ['Active Milestone:', 'Active Slice:', 'Active Task:', 'Blockers:', 'Next Action:']
    missing = [r for r in required if r not in text]
    assert not missing, f"Missing required STATE fields: {missing}"


def test_blockers_format():
    """Blockers başlığı altındaki içeriğin en az bir satır içerdiğini doğrula (boş liste kabul edilir)"""
    path = '.gsd/STATE.md'
    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f]

    # find index of Blockers:
    idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Blockers:'):
            idx = i
            break
    assert idx is not None, 'Blockers: başlığı bulunamadı'

    # next non-empty line after Blockers: should start with '-' or be empty
    next_lines = [l for l in lines[idx+1: idx+4]]
    # it's ok if blockers list is empty or has dash items
    if any(l.strip().startswith('-') for l in next_lines):
        assert True
    else:
        # allow explicit 'none' as a marker
        assert any('none' in l for l in next_lines), 'Blockers list malformed or missing items (use "- none" if none)'
