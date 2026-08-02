from __future__ import annotations

import sys

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from bilibili_drops_miner.gui_parts.styles import CARD_STYLE, BUTTON_STYLES


@dataclass(slots=True)
class MainWindowCallbacks:
    auto_fetch_cookie: Callable[..., None]
    auto_fetch_room_id: Callable[..., None]
    auto_fetch_task_ids: Callable[..., None]
    start: Callable[..., None]
    stop: Callable[..., None]
    load_config: Callable[..., None]
    save_config: Callable[..., None]
    clear_logs: Callable[..., None]
    claim_rewards: Callable[..., None]
    refresh_tasks: Callable[..., None]
    toggle_log: Callable[..., None]


@dataclass(slots=True)
class MainWindowWidgets:
    cookie_edit: QLineEdit
    rooms_edit: QLineEdit
    task_ids_edit: QLineEdit
    notify_urls_edit: QLineEdit
    threads_edit: QLineEdit
    reconnect_edit: QLineEdit
    task_interval_edit: QLineEdit
    verbose_check: QCheckBox
    disable_task_notify_check: QCheckBox
    progress_bar: QProgressBar
    task_text: QPlainTextEdit
    log_text: QPlainTextEdit
    log_card: QFrame
    log_toggle_btn: QPushButton
    claim_rewards_btn: QPushButton


def build_main_window_layout(
    window: QMainWindow,
    callbacks: MainWindowCallbacks,
) -> MainWindowWidgets:
    central = QWidget(window)
    central.setObjectName("appRoot")
    window.setCentralWidget(central)
    root_layout = QVBoxLayout(central)
    root_layout.setContentsMargins(24, 20, 24, 18)
    root_layout.setSpacing(12)

    title = QLabel("Bilibili 直播掉宝助手")
    title.setObjectName("appTitle")
    root_layout.addWidget(title)

    # ---- Config card ----
    config_card = QFrame()
    config_card.setObjectName("card")
    config_card.setStyleSheet(CARD_STYLE)
    config_layout = QVBoxLayout(config_card)
    config_layout.setContentsMargins(18, 14, 18, 14)
    config_layout.setSpacing(8)

    config_title = QLabel("运行配置")
    config_title.setObjectName("sectionTitle")
    config_layout.addWidget(config_title)

    cookie_edit = _make_line_edit("必填: SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx")
    rooms_edit = _make_line_edit("必填: 直播间号，多个用逗号分隔")
    rooms_edit.setText("23612045")
    task_ids_edit = _make_line_edit("可留空: F12 从 totalv2 请求中提取 task_ids")
    notify_urls_edit = _make_line_edit("可留空: 通知 URL，如 gotify://host/token")

    form_layout = QGridLayout()
    form_layout.setHorizontalSpacing(10)
    form_layout.setVerticalSpacing(6)
    form_layout.setColumnMinimumWidth(0, 72)
    form_layout.setColumnStretch(1, 1)
    _add_labeled_row(
        form_layout,
        0,
        "Cookie",
        cookie_edit,
        ("自动获取", "secondary", callbacks.auto_fetch_cookie),
    )
    _add_labeled_row(
        form_layout,
        1,
        "房间号",
        rooms_edit,
        ("自动获取", "secondary", callbacks.auto_fetch_room_id),
    )
    _add_labeled_row(
        form_layout,
        2,
        "任务 ID",
        task_ids_edit,
        ("自动获取", "secondary", callbacks.auto_fetch_task_ids),
    )
    _add_labeled_row(form_layout, 3, "通知 URL", notify_urls_edit)
    config_layout.addLayout(form_layout)

    threads_edit = _make_small_edit("1", minimum=1, maximum=128)
    reconnect_edit = _make_small_edit("8", minimum=1, maximum=3600)
    task_interval_edit = _make_small_edit("30", minimum=10, maximum=86400)
    verbose_check = QCheckBox("详细日志")
    disable_task_notify_check = QCheckBox("禁用任务完成通知")

    options_layout = QGridLayout()
    options_layout.setHorizontalSpacing(14)
    options_layout.setVerticalSpacing(6)
    for column, (text, widget) in enumerate(
        (
            ("线程数", threads_edit),
            ("重连延迟（秒）", reconnect_edit),
            ("任务查询间隔（秒）", task_interval_edit),
        )
    ):
        label = _make_field_label(text, widget)
        options_layout.addWidget(label, 0, column)
        options_layout.addWidget(widget, 1, column)
        options_layout.setColumnStretch(column, 1)
    options_layout.addWidget(verbose_check, 0, 3)
    options_layout.addWidget(disable_task_notify_check, 1, 3)
    options_layout.setColumnStretch(3, 2)
    config_layout.addLayout(options_layout)

    btn_row = QHBoxLayout()
    btn_row.setSpacing(8)
    btn_row.addWidget(_make_button("启动", "primary", callbacks.start))
    btn_row.addWidget(_make_button("停止", "outline", callbacks.stop))
    btn_row.addStretch(1)
    btn_row.addWidget(_make_button("加载配置", "secondary", callbacks.load_config))
    btn_row.addWidget(_make_button("保存配置", "secondary", callbacks.save_config))
    config_layout.addLayout(btn_row)

    progress_bar = QProgressBar()
    progress_bar.setTextVisible(False)
    progress_bar.setFixedHeight(4)
    progress_bar.setRange(0, 1)  # stopped state
    progress_bar.setValue(0)
    config_layout.addWidget(progress_bar)

    root_layout.addWidget(config_card)

    # ---- Task progress card ----
    task_card = QFrame()
    task_card.setObjectName("card")
    task_card.setStyleSheet(CARD_STYLE)
    task_layout = QVBoxLayout(task_card)
    task_layout.setContentsMargins(18, 12, 18, 12)
    task_layout.setSpacing(8)

    task_header = QHBoxLayout()
    task_title = QLabel("任务进度")
    task_title.setObjectName("sectionTitle")
    task_header.addWidget(task_title)
    task_header.addStretch(1)
    claim_rewards_btn = _make_button("领取奖励", "primary", callbacks.claim_rewards)
    task_header.addWidget(claim_rewards_btn)
    task_header.addWidget(
        _make_button("手动刷新", "secondary", callbacks.refresh_tasks)
    )
    task_layout.addLayout(task_header)

    task_text = QPlainTextEdit()
    task_text.setReadOnly(True)
    fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    if sys.platform == "darwin":
        fixed_font.setFamily("Menlo")
    elif sys.platform == "win32":
        fixed_font.setFamily("Consolas")
    fixed_font.setPointSize(10)
    task_text.setFont(fixed_font)
    task_text.setLineWrapMode(QPlainTextEdit.NoWrap)
    task_text.setMinimumHeight(96)
    task_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    task_text.setPlainText("点击“手动刷新”查看任务进度")
    task_layout.addWidget(task_text)

    root_layout.addWidget(task_card, 1)

    # ---- Log card (collapsible, default collapsed) ----
    log_card = QFrame()
    log_card.setObjectName("card")
    log_card.setStyleSheet(CARD_STYLE)
    log_layout = QVBoxLayout(log_card)
    log_layout.setContentsMargins(14, 6, 14, 10)
    log_layout.setSpacing(6)

    log_header = QHBoxLayout()
    log_header.setSpacing(8)
    log_toggle_btn = QPushButton("▶ 运行日志")
    log_title_font = QFont()
    log_title_font.setPointSize(11)
    log_title_font.setBold(True)
    log_toggle_btn.setFont(log_title_font)
    log_toggle_btn.setFlat(True)
    log_toggle_btn.setCursor(Qt.PointingHandCursor)
    log_toggle_btn.setStyleSheet(BUTTON_STYLES["ghost"] + "QPushButton{text-align:left;}")
    log_toggle_btn.clicked.connect(callbacks.toggle_log)
    log_header.addWidget(log_toggle_btn)
    log_header.addStretch(1)
    log_header.addWidget(_make_button("清空日志", "ghost", callbacks.clear_logs))
    log_layout.addLayout(log_header)

    log_text = QPlainTextEdit()
    log_text.setReadOnly(True)
    log_text.setFont(fixed_font)
    log_text.setMaximumBlockCount(5000)
    log_text.setMinimumHeight(96)
    log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    log_text.setVisible(False)
    log_layout.addWidget(log_text)

    root_layout.addWidget(log_card)

    return MainWindowWidgets(
        cookie_edit=cookie_edit,
        rooms_edit=rooms_edit,
        task_ids_edit=task_ids_edit,
        notify_urls_edit=notify_urls_edit,
        threads_edit=threads_edit,
        reconnect_edit=reconnect_edit,
        task_interval_edit=task_interval_edit,
        verbose_check=verbose_check,
        disable_task_notify_check=disable_task_notify_check,
        progress_bar=progress_bar,
        task_text=task_text,
        log_text=log_text,
        log_card=log_card,
        log_toggle_btn=log_toggle_btn,
        claim_rewards_btn=claim_rewards_btn,
    )


def _make_line_edit(placeholder: str) -> QLineEdit:
    widget = QLineEdit()
    widget.setPlaceholderText(placeholder)
    widget.setClearButtonEnabled(True)
    return widget


def _make_small_edit(default: str, *, minimum: int, maximum: int) -> QLineEdit:
    widget = QLineEdit()
    widget.setText(default)
    widget.setValidator(QIntValidator(minimum, maximum, widget))
    widget.setMinimumWidth(96)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return widget


def _make_button(text: str, color: str, slot: Callable[..., None]) -> QPushButton:
    button = QPushButton(text)
    button.setStyleSheet(BUTTON_STYLES.get(color, BUTTON_STYLES["secondary"]))
    button.setCursor(Qt.PointingHandCursor)
    button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    button.clicked.connect(slot)
    return button


def _make_field_label(text: str, editor: QLineEdit) -> QLabel:
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    label.setBuddy(editor)
    return label


def _add_labeled_row(
    layout: QGridLayout,
    row: int,
    label: str,
    editor: QLineEdit,
    extra_button: tuple[str, str, Callable[..., None]] | None = None,
) -> None:
    lab = _make_field_label(label, editor)
    layout.addWidget(lab, row, 0)
    editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(editor, row, 1)
    if extra_button is not None:
        text, color, slot = extra_button
        button = _make_button(text, color, slot)
        button.setMinimumWidth(100)
        layout.addWidget(button, row, 2)
