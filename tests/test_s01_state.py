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