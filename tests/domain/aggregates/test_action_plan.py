"""ActionPlan Aggregate 테스트."""

import pytest
from datetime import datetime

from domain.aggregates.action_plan import ActionItem, ActionPlan, ActionResult


class TestActionItemCreation:
    """ActionItem 생성 테스트."""
    
    def test_create_minimal(self):
        """최소 정보로 생성."""
        item = ActionItem(
            action_id=1,
            file_id=10,
            action="DELETE"
        )
        
        assert item.action_id == 1
        assert item.file_id == 10
        assert item.action == "DELETE"
        assert item.target_path is None
        assert item.depends_on == ()
        assert item.risk == "MEDIUM"
        assert item.reason_id is None
    
    def test_create_with_dependencies(self):
        """의존성과 함께 생성."""
        item = ActionItem(
            action_id=2,
            file_id=11,
            action="MOVE",
            target_path="/new/path.txt",
            depends_on=(1,),
            risk="HIGH",
            reason_id=5
        )
        
        assert item.target_path == "/new/path.txt"
        assert item.depends_on == (1,)
        assert item.risk == "HIGH"
        assert item.reason_id == 5


class TestActionItemValidation:
    """ActionItem 검증 테스트."""
    
    def test_invalid_action(self):
        """잘못된 action이면 실패."""
        with pytest.raises(ValueError, match="action must be one of"):
            ActionItem(
                action_id=1,
                file_id=10,
                action="INVALID"
            )
    
    def test_invalid_risk(self):
        """잘못된 risk이면 실패."""
        with pytest.raises(ValueError, match="risk must be one of"):
            ActionItem(
                action_id=1,
                file_id=10,
                action="DELETE",
                risk="CRITICAL"
            )


class TestActionItemProperties:
    """ActionItem 속성 테스트."""
    
    def test_is_delete(self):
        """삭제 액션 확인."""
        item = ActionItem(action_id=1, file_id=10, action="DELETE")
        assert item.is_delete is True
        assert item.is_move is False
    
    def test_is_move(self):
        """이동 액션 확인."""
        item = ActionItem(action_id=1, file_id=10, action="MOVE")
        assert item.is_move is True
        assert item.is_delete is False
    
    def test_is_low_risk(self):
        """저위험 확인."""
        item = ActionItem(action_id=1, file_id=10, action="DELETE", risk="LOW")
        assert item.is_low_risk is True
        assert item.is_high_risk is False
    
    def test_is_high_risk(self):
        """고위험 확인."""
        item = ActionItem(action_id=1, file_id=10, action="DELETE", risk="HIGH")
        assert item.is_high_risk is True
        assert item.is_low_risk is False
    
    def test_has_dependencies_true(self):
        """의존성 있음."""
        item = ActionItem(
            action_id=2,
            file_id=11,
            action="DELETE",
            depends_on=(1,)
        )
        assert item.has_dependencies is True
    
    def test_has_dependencies_false(self):
        """의존성 없음."""
        item = ActionItem(action_id=1, file_id=10, action="DELETE")
        assert item.has_dependencies is False


class TestActionPlanCreation:
    """ActionPlan 생성 테스트."""
    
    def test_create_minimal(self):
        """최소 정보로 생성."""
        plan = ActionPlan(
            plan_id=1,
            created_from="DUPLICATE"
        )
        
        assert plan.plan_id == 1
        assert plan.created_from == "DUPLICATE"
        assert plan.items == ()
        assert plan.summary == {}
        assert isinstance(plan.created_at, datetime)
    
    def test_create_with_items(self):
        """아이템과 함께 생성."""
        items = (
            ActionItem(action_id=1, file_id=10, action="DELETE"),
            ActionItem(action_id=2, file_id=11, action="DELETE"),
        )
        plan = ActionPlan(
            plan_id=1,
            created_from="DUPLICATE",
            items=items,
            summary={"bytes_savable": 1024000, "files_to_delete": 2}
        )
        
        assert plan.items == items
        assert plan.summary["bytes_savable"] == 1024000


class TestActionPlanValidation:
    """ActionPlan 검증 테스트."""
    
    def test_invalid_created_from(self):
        """잘못된 created_from이면 실패."""
        with pytest.raises(ValueError, match="created_from must be one of"):
            ActionPlan(
                plan_id=1,
                created_from="INVALID"
            )
    
    def test_duplicate_action_ids(self):
        """action_id 중복이면 실패."""
        items = (
            ActionItem(action_id=1, file_id=10, action="DELETE"),
            ActionItem(action_id=1, file_id=11, action="DELETE"),  # 중복
        )
        with pytest.raises(ValueError, match="Duplicate action_ids"):
            ActionPlan(
                plan_id=1,
                created_from="DUPLICATE",
                items=items
            )


class TestActionPlanProperties:
    """ActionPlan 속성 테스트."""
    
    def test_item_count(self):
        """아이템 수."""
        items = (
            ActionItem(action_id=1, file_id=10, action="DELETE"),
            ActionItem(action_id=2, file_id=11, action="DELETE"),
        )
        plan = ActionPlan(
            plan_id=1,
            created_from="DUPLICATE",
            items=items
        )
        
        assert plan.item_count == 2
    
    def test_is_empty_true(self):
        """빈 플랜."""
        plan = ActionPlan(plan_id=1, created_from="DUPLICATE")
        assert plan.is_empty is True
    
    def test_is_empty_false(self):
        """아이템이 있는 플랜."""
        items = (ActionItem(action_id=1, file_id=10, action="DELETE"),)
        plan = ActionPlan(
            plan_id=1,
            created_from="DUPLICATE",
            items=items
        )
        assert plan.is_empty is False


class TestActionPlanMethods:
    """ActionPlan 메서드 테스트."""
    
    def test_get_item_by_id_found(self):
        """ID로 아이템 찾기 (있음)."""
        items = (
            ActionItem(action_id=1, file_id=10, action="DELETE"),
            ActionItem(action_id=2, file_id=11, action="MOVE"),
        )
        plan = ActionPlan(plan_id=1, created_from="DUPLICATE", items=items)
        
        item = plan.get_item_by_id(2)
        assert item is not None
        assert item.action_id == 2
        assert item.action == "MOVE"
    
    def test_get_item_by_id_not_found(self):
        """ID로 아이템 찾기 (없음)."""
        items = (ActionItem(action_id=1, file_id=10, action="DELETE"),)
        plan = ActionPlan(plan_id=1, created_from="DUPLICATE", items=items)
        
        item = plan.get_item_by_id(99)
        assert item is None
    
    def test_get_items_by_action(self):
        """액션 타입으로 필터링."""
        items = (
            ActionItem(action_id=1, file_id=10, action="DELETE"),
            ActionItem(action_id=2, file_id=11, action="MOVE"),
            ActionItem(action_id=3, file_id=12, action="DELETE"),
        )
        plan = ActionPlan(plan_id=1, created_from="DUPLICATE", items=items)
        
        delete_items = plan.get_items_by_action("DELETE")
        assert len(delete_items) == 2
        assert all(item.action == "DELETE" for item in delete_items)
    
    def test_get_high_risk_items(self):
        """고위험 아이템 필터링."""
        items = (
            ActionItem(action_id=1, file_id=10, action="DELETE", risk="LOW"),
            ActionItem(action_id=2, file_id=11, action="DELETE", risk="HIGH"),
            ActionItem(action_id=3, file_id=12, action="MOVE", risk="HIGH"),
        )
        plan = ActionPlan(plan_id=1, created_from="DUPLICATE", items=items)
        
        high_risk = plan.get_high_risk_items()
        assert len(high_risk) == 2
        assert all(item.is_high_risk for item in high_risk)
    
    def test_get_delete_count(self):
        """삭제 액션 수."""
        items = (
            ActionItem(action_id=1, file_id=10, action="DELETE"),
            ActionItem(action_id=2, file_id=11, action="MOVE"),
            ActionItem(action_id=3, file_id=12, action="DELETE"),
        )
        plan = ActionPlan(plan_id=1, created_from="DUPLICATE", items=items)
        
        assert plan.get_delete_count() == 2
    
    def test_get_bytes_savable(self):
        """절감 가능 용량."""
        plan = ActionPlan(
            plan_id=1,
            created_from="DUPLICATE",
            summary={"bytes_savable": 1024000}
        )
        
        assert plan.get_bytes_savable() == 1024000
    
    def test_get_bytes_savable_not_present(self):
        """절감 가능 용량 (없으면 0)."""
        plan = ActionPlan(plan_id=1, created_from="DUPLICATE")
        assert plan.get_bytes_savable() == 0
    
    def test_with_added_item(self):
        """아이템 추가."""
        item1 = ActionItem(action_id=1, file_id=10, action="DELETE")
        plan = ActionPlan(
            plan_id=1,
            created_from="DUPLICATE",
            items=(item1,)
        )
        
        item2 = ActionItem(action_id=2, file_id=11, action="MOVE")
        new_plan = plan.with_added_item(item2)
        
        # 원본 불변
        assert plan.item_count == 1
        # 새 플랜
        assert new_plan.item_count == 2
        assert new_plan.get_item_by_id(2) is not None
    
    def test_with_added_item_duplicate_id(self):
        """중복 ID 추가 시 실패."""
        item1 = ActionItem(action_id=1, file_id=10, action="DELETE")
        plan = ActionPlan(
            plan_id=1,
            created_from="DUPLICATE",
            items=(item1,)
        )
        
        item2 = ActionItem(action_id=1, file_id=11, action="MOVE")
        with pytest.raises(ValueError, match="already exists"):
            plan.with_added_item(item2)
    
    def test_with_updated_summary(self):
        """요약 업데이트."""
        plan = ActionPlan(
            plan_id=1,
            created_from="DUPLICATE",
            summary={"bytes_savable": 1024000}
        )
        
        new_summary = {"bytes_savable": 2048000, "files_to_delete": 10}
        new_plan = plan.with_updated_summary(new_summary)
        
        # 원본 불변
        assert plan.summary["bytes_savable"] == 1024000
        # 새 플랜
        assert new_plan.summary["bytes_savable"] == 2048000
        assert new_plan.summary["files_to_delete"] == 10


class TestActionResultCreation:
    """ActionResult 생성 테스트."""
    
    def test_create_success(self):
        """성공 결과 생성."""
        result = ActionResult(
            action_id=1,
            ok=True,
            before_path="/old/path.txt"
        )
        
        assert result.action_id == 1
        assert result.ok is True
        assert result.error is None
        assert result.before_path == "/old/path.txt"
        assert result.after_path is None
        assert isinstance(result.timestamp, datetime)
    
    def test_create_failure(self):
        """실패 결과 생성."""
        result = ActionResult(
            action_id=1,
            ok=False,
            error="Permission denied"
        )
        
        assert result.ok is False
        assert result.error == "Permission denied"


class TestActionResultProperties:
    """ActionResult 속성 테스트."""
    
    def test_is_success(self):
        """성공 확인."""
        result = ActionResult(action_id=1, ok=True)
        assert result.is_success is True
        assert result.is_failure is False
    
    def test_is_failure(self):
        """실패 확인."""
        result = ActionResult(action_id=1, ok=False)
        assert result.is_failure is True
        assert result.is_success is False
    
    def test_has_error_true(self):
        """에러 있음."""
        result = ActionResult(action_id=1, ok=False, error="Error message")
        assert result.has_error is True
    
    def test_has_error_false(self):
        """에러 없음."""
        result = ActionResult(action_id=1, ok=True)
        assert result.has_error is False
