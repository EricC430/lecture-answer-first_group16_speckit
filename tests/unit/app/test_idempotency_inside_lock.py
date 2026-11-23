"""去重查表與記錄必須在鎖內（FR-033；PR #15 第二、三次審查）。

`_execute` 的臨界區內目前沒有 `await`，以 `asyncio.gather` 送出同一個 key 的並行請求
不會交錯，無法分辨查表放在鎖內或鎖外。因此直接檢查不變式：每次呼叫
`recall`／`remember`（建立活動時為 `recall_create`／`remember_create`）時，
對應的鎖都必須是持有狀態。把查表或記錄搬到鎖外時，本測試會失敗。
"""

import asyncio

from lecture_quiz.app.activity.registry import ActivityRegistry
from lecture_quiz.app.activity.service import ActivityService
from tests.conftest import FakeClock, ManualScheduler


class NullPublisher:
    async def publish(self, activity):
        pass

    async def disconnect_device(self, code, token_hash, reason):
        pass


class LockCheckingRegistry(ActivityRegistry):
    """每次查表或記錄去重結果時，確認對應的鎖正被持有。"""

    def __init__(self):
        super().__init__()
        self.checked: list[str] = []

    def _assert_locked(self, code, name):
        assert self.lock(code).locked(), f"{name} 在鎖外被呼叫"
        self.checked.append(name)

    def recall(self, code, key):
        self._assert_locked(code, "recall")
        return super().recall(code, key)

    def remember(self, code, key, response):
        self._assert_locked(code, "remember")
        super().remember(code, key, response)

    def recall_create(self, idempotency_key):
        assert self.create_lock.locked(), "recall_create 在鎖外被呼叫"
        self.checked.append("recall_create")
        return super().recall_create(idempotency_key)

    def remember_create(self, idempotency_key, result):
        assert self.create_lock.locked(), "remember_create 在鎖外被呼叫"
        self.checked.append("remember_create")
        super().remember_create(idempotency_key, result)


def test_dedupe_lookup_and_record_happen_inside_lock():
    async def scenario():
        registry = LockCheckingRegistry()
        service = ActivityService(
            registry, FakeClock(), ManualScheduler(), NullPublisher()
        )
        created = await service.create(4, None, "create-key")
        again = await service.create(4, None, "create-key")
        assert again == created
        code = created.value.code
        teacher = service.resolve_requester(code, created.value.teacher_token)
        await service.replace_questions(code, teacher, (1, 2))
        joined = await asyncio.gather(
            *(service.join(code, 1, None, None, "join-key") for _ in range(3))
        )
        assert all(j == joined[0] for j in joined)
        opened = await asyncio.gather(
            *(
                service.open_round(code, teacher, None, False, None, "open-key")
                for _ in range(3)
            )
        )
        assert all(o == opened[0] for o in opened)
        await service.close_round(code, teacher, "close-key")
        await service.close_round(code, teacher, "close-key")
        return registry.checked

    checked = asyncio.run(scenario())
    for name in ("recall_create", "remember_create", "recall", "remember"):
        assert name in checked
