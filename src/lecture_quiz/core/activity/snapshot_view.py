"""依角色裁切活動快照（contracts/sync-websocket.md「訊息格式」）。

學生版只含本組資料，不含其他組的名稱、組數或進度（FR-030）；老師版含全部組別。
組別加入憑證待 US2 補上（⚠ Q-06）。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Literal

from lecture_quiz.core.activity.models import Activity, Stage

Role = Literal["teacher", "student"]
JsonDict = dict[str, object]


def _empty() -> MappingProxyType[str, object]:
    return MappingProxyType({})


def _iso(value: datetime | None, *, millis: bool = False) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="milliseconds") if millis else value.isoformat()


@dataclass(frozen=True)
class ActivitySnapshot:
    """推送與查詢用的快照。

    Attributes:
        role: `teacher` 或 `student`。
        common: 兩種角色共用的欄位（已是 JSON 格式）。
        extra: 依角色加上的欄位（老師：`groups`、`questionNumbers`；學生：`ownGroup`）。
    """

    role: Role
    common: Mapping[str, object]
    extra: Mapping[str, object] = field(default_factory=_empty)

    @property
    def version(self) -> int:
        """快照的狀態版本。"""
        value = self.common["version"]
        assert isinstance(value, int)
        return value

    def to_json(self) -> JsonDict:
        """轉成可直接 JSON 序列化的 dict。

        Returns:
            `{"type": "snapshot", "role": ..., ...}`。
        """
        return {"type": "snapshot", "role": self.role, **self.common, **self.extra}


class SnapshotView:
    """把 `Activity` 轉成依角色裁切的快照；純函式。"""

    @staticmethod
    def _common(activity: Activity) -> JsonDict:
        current = activity.current_round
        is_open = activity.stage is Stage.ROUND_OPEN and current is not None
        return {
            "code": activity.code,
            "version": activity.version,
            "changedAt": _iso(activity.changed_at, millis=True),
            "stage": activity.stage.value,
            "roundNumber": current.number if current else None,
            "openQuestions": list(current.rules.question_numbers)
            if is_open and current
            else [],
            "deadline": _iso(current.rules.deadline) if is_open and current else None,
            "fairMode": current.rules.fair_mode if current else False,
            "unsolvedQuestions": list(activity.unsolved_questions)
            if activity.stage is Stage.ENDED
            else [],
        }

    @staticmethod
    def for_teacher(activity: Activity) -> ActivitySnapshot:
        """老師版快照：含全部組別與題號。

        Args:
            activity: 活動。

        Returns:
            老師版 `ActivitySnapshot`。
        """
        device_counts: dict[str, int] = {}
        for device in activity.devices.values():
            device_counts[device.group_name] = (
                device_counts.get(device.group_name, 0) + 1
            )
        groups = [
            {
                "name": g.name,
                "successCount": g.success_count,
                "hasSubmissions": g.has_submissions,
                "deviceCount": device_counts.get(g.name, 0),
            }
            for g in activity.groups.values()
        ]
        extra: JsonDict = {
            "maxGroups": activity.max_groups,
            "groups": groups,
            "questionNumbers": list(activity.question_numbers),
        }
        return ActivitySnapshot("teacher", SnapshotView._common(activity), extra)

    @staticmethod
    def for_group(activity: Activity, group_name: str) -> ActivitySnapshot:
        """學生版快照：只含本組資料。

        Args:
            activity: 活動。
            group_name: 請求者所屬的組別（由後端依裝置身分判定）。

        Returns:
            學生版 `ActivitySnapshot`；組別不存在時 `ownGroup` 為 `None`。
        """
        group = activity.groups.get(group_name)
        own = (
            {"name": group.name, "successCount": group.success_count} if group else None
        )
        return ActivitySnapshot(
            "student", SnapshotView._common(activity), {"ownGroup": own}
        )
