"""保证案例测试与 docs/分阶段实现与测试计划.md 的案例编号不会脱节。"""

from pathlib import Path

from tests.case_registry import CASES

PLAN = Path(__file__).resolve().parents[2] / "docs" / "分阶段实现与测试计划.md"


def _marked_case_ids(request):
    found = set()
    for item in request.session.items:
        mark = item.get_closest_marker("case")
        if mark and mark.args:
            found.add(mark.args[0])
    return found


def test_every_registered_case_has_at_least_one_test(request):
    """登记表中的每个案例都必须至少有一个带 case 标记的测试。"""
    marked = _marked_case_ids(request)
    assert set(CASES) <= marked, f"缺少案例测试：{sorted(set(CASES) - marked)}"
    assert marked <= set(CASES), f"存在未登记的案例编号：{sorted(marked - set(CASES))}"


def test_plan_document_lists_every_registered_case():
    """测试计划文档必须列出登记表中的每个案例编号。"""
    text = PLAN.read_text(encoding="utf-8")
    missing = [case_id for case_id in CASES if case_id not in text]
    assert missing == []
