from __future__ import annotations


BUTTON_STYLES: dict[str, str] = {
    "primary": (
        "QPushButton{background:#fafafa;color:#09090b;border:1px solid #fafafa;"
        "border-radius:6px;padding:7px 14px;min-height:18px;font-weight:600;}"
        "QPushButton:hover{background:#e4e4e7;border-color:#e4e4e7;}"
        "QPushButton:pressed{background:#d4d4d8;border-color:#d4d4d8;}"
        "QPushButton:focus{border-color:#ffffff;}"
        "QPushButton:disabled{background:#3f3f46;color:#71717a;border-color:#3f3f46;}"
    ),
    "outline": (
        "QPushButton{background:#09090b;color:#fafafa;border:1px solid #52525b;"
        "border-radius:6px;padding:7px 14px;min-height:18px;font-weight:600;}"
        "QPushButton:hover{background:#27272a;border-color:#a1a1aa;}"
        "QPushButton:pressed{background:#18181b;border-color:#fafafa;}"
        "QPushButton:focus{border-color:#fafafa;}"
        "QPushButton:disabled{color:#52525b;border-color:#27272a;}"
    ),
    "secondary": (
        "QPushButton{background:#27272a;color:#fafafa;border:1px solid #3f3f46;"
        "border-radius:6px;padding:7px 14px;min-height:18px;font-weight:500;}"
        "QPushButton:hover{background:#3f3f46;border-color:#52525b;}"
        "QPushButton:pressed{background:#18181b;}"
        "QPushButton:focus{border-color:#a1a1aa;}"
        "QPushButton:disabled{color:#71717a;background:#18181b;border-color:#27272a;}"
    ),
    "ghost": (
        "QPushButton{background:transparent;color:#d4d4d8;border:1px solid transparent;"
        "border-radius:6px;padding:6px 10px;min-height:18px;font-weight:500;}"
        "QPushButton:hover{background:#27272a;color:#ffffff;}"
        "QPushButton:pressed{background:#18181b;}"
        "QPushButton:focus{border-color:#52525b;}"
    ),
}


CARD_STYLE = (
    "QFrame#card{background:#111113;border:1px solid #27272a;border-radius:8px;}"
)
