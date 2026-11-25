"""服務層組出的寫入內容（US3）：位置取自 002、答案逐字。"""

import dataclasses

from lecture_quiz.core.guided_notes_import.models import CellRef


def confirm(env):
    snapshot_id = env.run(
        env.service.preview, env.code, env.requester()
    ).value.snapshot.snapshot_id
    return env.run(env.service.confirm_write, env.code, env.requester(), snapshot_id)


def test_cells_are_blank_targets_with_verbatim_answers(make_env):
    """Scenario: US3-AS1、US3-AS4：(位置, 答案原文) 逐格相同，不 strip、不正規化。"""
    env = make_env()
    tricky = "  =1+1\n第二行  "
    rnd, group, answers = env.world.winners[3]
    env.world.submissions.submissions = tuple(
        dataclasses.replace(s, answers=(tricky, *s.answers[1:]))
        if (s.round_number, s.question_number, s.group_number) == (rnd, 3, group)
        else s
        for s in env.world.submissions.submissions
    )
    assert confirm(env).ok
    cells = dict(env.writer.write_calls[0])
    target = next(b.target for b in env.world.record.blanks if b.question_number == 3)
    assert cells[target] == tricky


def test_targets_come_from_import_record_only_and_losers_have_none(make_env):
    """Scenario: US3-AS1、AS5：位置全來自 002 的 Blank.target；沒成功的題沒有目標格。"""
    env = make_env()
    assert confirm(env).ok
    cells = env.writer.write_calls[0]
    targets = {ref for ref, _ in cells}
    allowed = {
        b.target
        for b in env.world.record.blanks
        if b.question_number in env.world.winners
    }
    assert targets == allowed
    unsolved = {
        b.target
        for b in env.world.record.blanks
        if b.question_number not in env.world.winners
    }
    assert not (targets & unsolved)
    assert all(isinstance(ref, CellRef) for ref in targets)
