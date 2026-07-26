from __future__ import annotations

import unittest
from unittest.mock import patch

from bilibili_drops_miner.client_parts.models import TaskProgress
from bilibili_drops_miner.gui_parts.task_controller import TaskController


class _Recorder:
    def __init__(self) -> None:
        self.cookie = "SESSDATA=fake"
        self.room_ids = [23612045]
        self.task_ids = ["task-a"]
        self.warnings: list[tuple[str, str]] = []
        self.texts: list[str] = []
        self.watch_time_texts: list[str] = []
        self.completions: list[tuple[str, bool]] = []

    def build_controller(self) -> TaskController:
        return TaskController(
            get_cookie=lambda: self.cookie,
            get_room_ids=lambda: list(self.room_ids),
            get_task_ids=lambda: list(self.task_ids),
            show_warning=lambda title, msg: self.warnings.append((title, msg)),
            set_task_progress_text=self.texts.append,
            set_live_watch_time_text=self.watch_time_texts.append,
            complete_task_refresh=self._complete_task_refresh,
            post_ui_task=self._post_ui_task,
        )

    def _complete_task_refresh(self, result_text: str, rerun: bool) -> None:
        self.completions.append((result_text, rerun))
        self.texts.append(result_text)

    def _post_ui_task(self, callback, *args, **kwargs) -> None:
        callback(*args, **kwargs)


class _FakeThread:
    instances: list[_FakeThread] = []

    def __init__(self, *, target, daemon: bool, name: str) -> None:
        self.target = target
        self.daemon = daemon
        self.name = name
        self.started = False
        self.__class__.instances.append(self)

    def start(self) -> None:
        self.started = True


class _FakeClient:
    def __init__(self, cookie: str) -> None:
        self.cookie = cookie
        self.closed = False

    async def get_task_progress(self, task_ids: list[str]) -> list[TaskProgress]:
        return [
            TaskProgress(
                task_id=task_ids[0],
                task_name="观看直播60分钟",
                status=1,
                cur_value=30,
                limit_value=60,
            )
        ]

    async def close(self) -> None:
        self.closed = True


class TaskControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        _FakeThread.instances.clear()

    def test_refresh_warns_when_manual_without_cookie(self) -> None:
        recorder = _Recorder()
        recorder.cookie = ""

        recorder.build_controller().refresh(manual=True)

        self.assertEqual(recorder.warnings, [("提示", "请先填写 Cookie")])
        self.assertEqual(recorder.texts, [])

    def test_refresh_sets_empty_task_text_without_task_ids(self) -> None:
        recorder = _Recorder()
        recorder.task_ids = []

        recorder.build_controller().refresh()

        self.assertEqual(recorder.warnings, [])
        self.assertEqual(recorder.texts, ["无任务数据（未填写任务 ID）"])

    def test_refresh_queues_second_request_while_inflight(self) -> None:
        recorder = _Recorder()
        controller = recorder.build_controller()

        with (
            patch(
                "bilibili_drops_miner.gui_parts.task_controller.threading.Thread",
                _FakeThread,
            ),
            patch(
                "bilibili_drops_miner.gui_parts.task_controller.BilibiliClient",
                _FakeClient,
            ),
        ):
            controller.refresh()
            controller.refresh()

            self.assertEqual(len(_FakeThread.instances), 1)
            self.assertEqual(_FakeThread.instances[0].name, "gui-task-refresh")
            self.assertEqual(
                recorder.texts,
                ["正在刷新任务进度...", "已有刷新进行中，已排队下一次刷新..."],
            )

            _FakeThread.instances[0].target()

        self.assertEqual(len(recorder.completions), 1)
        result_text, rerun = recorder.completions[0]
        self.assertTrue(rerun)
        self.assertIn("观看直播", result_text)

    def test_claim_rewards_reports_when_already_inflight(self) -> None:
        recorder = _Recorder()
        controller = recorder.build_controller()

        with patch(
            "bilibili_drops_miner.gui_parts.task_controller.threading.Thread",
            _FakeThread,
        ):
            controller.claim_rewards()
            controller.claim_rewards()

        self.assertEqual(len(_FakeThread.instances), 1)
        self.assertEqual(_FakeThread.instances[0].name, "gui-reward-claim")
        self.assertEqual(
            recorder.texts,
            ["正在领取全部可领取奖励...", "已有领奖任务进行中，请稍候..."],
        )


if __name__ == "__main__":
    unittest.main()
