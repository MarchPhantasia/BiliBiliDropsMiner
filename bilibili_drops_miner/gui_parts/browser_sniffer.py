from __future__ import annotations

import json
import logging
import shutil
import tempfile
import threading
import time
from collections.abc import Callable, Iterable
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from bilibili_drops_miner.gui_parts.browser_utils import (
    browser_label,
    browser_try_order,
    extract_room_id_from_live_url,
    find_browser,
    find_browser_binary,
)
from bilibili_drops_miner.gui_parts.extension_builder import (
    write_chrome_extension,
    write_edge_extension,
)
from bilibili_drops_miner.utils import extract_bili_live_task_groups_from_state

SniffPayloadKind = Literal["cookies", "page", "network"]
NetworkCallback = Callable[[Any], None]
CookiesCallback = Callable[[list[dict[str, Any]]], None]
PageUrlCallback = Callable[[int], None]
PageHtmlCallback = Callable[[str, str], bool]
PageStateCallback = Callable[[dict[str, Any], str], bool]
TaskGroupsCallback = Callable[[list[dict[str, object]], str], bool]
ErrorCallback = Callable[[str, str], None]

LOGIN_COOKIE_NAMES = {
    "SESSDATA",
    "bili_jct",
    "DedeUserID",
    "DedeUserID__ckMd5",
    "buvid3",
    "b_nut",
    "sid",
}


def normalize_tab_task_groups(payload: Any) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    raw_groups = payload.get("groups")
    tab_count = payload.get("tab_count")
    if not isinstance(raw_groups, list) or not isinstance(tab_count, int):
        return []

    groups: list[dict[str, object]] = []
    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            continue
        label = str(raw_group.get("label") or "").strip()
        raw_task_ids = raw_group.get("task_ids")
        if not label or not isinstance(raw_task_ids, list):
            continue
        task_ids = list(
            dict.fromkeys(
                str(task_id).strip()
                for task_id in raw_task_ids
                if str(task_id).strip()
            )
        )
        if task_ids:
            groups.append(
                {
                    "label": label,
                    "task_ids": task_ids,
                    "active": bool(raw_group.get("active")),
                }
            )

    return groups if tab_count > 0 and len(groups) == tab_count else []


def task_ids_from_performance_logs(entries: list[dict[str, Any]]) -> list[str]:
    latest_task_ids: list[str] = []
    for entry in entries:
        try:
            message = json.loads(str(entry.get("message") or ""))["message"]
            if message.get("method") != "Network.requestWillBeSent":
                continue
            request = (message.get("params") or {}).get("request") or {}
            url = str(request.get("url") or "")
            if "/x/task/totalv2" not in url:
                continue
            value = parse_qs(urlparse(url).query).get("task_ids", [""])[0]
            task_ids = [task_id.strip() for task_id in value.split(",")]
            latest_task_ids = [task_id for task_id in task_ids if task_id]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return latest_task_ids


def collect_task_groups_from_tabs(
    driver: Any,
    *,
    timeout_per_tab: float = 4.0,
) -> list[dict[str, object]]:
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.by import By

    selector = '[data-cy="EvaTabs_tabItem"]'
    tab_specs: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for index, element in enumerate(driver.find_elements(By.CSS_SELECTOR, selector)):
        if not element.is_displayed():
            continue
        label = str(element.text or "").strip()
        data_id = str(element.get_attribute("data-id") or "")
        key = data_id, label
        if not label or key in seen:
            continue
        seen.add(key)
        tab_specs.append(
            {
                "index": index,
                "data_id": data_id,
                "label": label,
                "active": element.get_attribute("data-activated") == "true",
            }
        )

    if not tab_specs:
        return []

    initial_active_task_ids = task_ids_from_performance_logs(
        driver.get_log("performance")
    )
    ordered_specs = [spec for spec in tab_specs if not spec["active"]]
    ordered_specs.extend(spec for spec in tab_specs if spec["active"])
    captured_groups: list[dict[str, object]] = []

    for spec in ordered_specs:
        current_element = None
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            if not element.is_displayed():
                continue
            data_id = str(element.get_attribute("data-id") or "")
            label = str(element.text or "").strip()
            if data_id == spec["data_id"] and label == spec["label"]:
                current_element = element
                break
        if current_element is None:
            continue

        driver.get_log("performance")
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", current_element
        )
        try:
            current_element.click()
        except Exception:
            ActionChains(driver).move_to_element(current_element).click().perform()

        deadline = time.monotonic() + timeout_per_tab
        task_ids: list[str] = []
        while time.monotonic() < deadline:
            task_ids = task_ids_from_performance_logs(
                driver.get_log("performance")
            )
            if task_ids:
                break
            time.sleep(0.1)
        if not task_ids and spec["active"]:
            task_ids = initial_active_task_ids
        if task_ids:
            captured_groups.append(
                {
                    "index": spec["index"],
                    "label": spec["label"],
                    "task_ids": task_ids,
                    "active": spec["active"],
                }
            )

    captured_groups.sort(key=lambda group: int(group["index"]))
    payload = {
        "tab_count": len(tab_specs),
        "groups": [
            {key: value for key, value in group.items() if key != "index"}
            for group in captured_groups
        ],
    }
    return normalize_tab_task_groups(payload)


def classify_sniff_payload(data: dict[str, Any]) -> tuple[SniffPayloadKind, Any]:
    if data.get("type") == "__bili_cookies__":
        return "cookies", data["cookies"]
    if data.get("type") == "__bili_page__":
        return "page", data
    return "network", data


def select_login_cookies(cookies: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    has_sessdata = any(cookie.get("name") == "SESSDATA" for cookie in cookies)
    has_dedeuid = any(cookie.get("name") == "DedeUserID" for cookie in cookies)
    if not (has_sessdata and has_dedeuid):
        return None
    return [cookie for cookie in cookies if cookie.get("name") in LOGIN_COOKIE_NAMES]


def is_sniff_finished(
    enabled_done_pairs: Iterable[tuple[bool, bool]],
    *,
    finish_on_any: bool,
) -> bool:
    done_states = [done for enabled, done in enabled_done_pairs if enabled]
    if not done_states:
        return False
    return any(done_states) if finish_on_any else all(done_states)


def start_browser_sniff(
    url_keyword: str | None,
    hint: str,
    *,
    on_error: ErrorCallback,
    on_network_match: NetworkCallback | None = None,
    on_cookies: CookiesCallback | None = None,
    on_page_url: PageUrlCallback | None = None,
    on_page_html: PageHtmlCallback | None = None,
    on_page_state: PageStateCallback | None = None,
    on_task_groups: TaskGroupsCallback | None = None,
    browser_preference: str | None = None,
    finish_on_any: bool = False,
    initial_url: str = "https://www.bilibili.com/",
    logger: logging.Logger | None = None,
) -> threading.Thread:
    logger = logger or logging.getLogger(__name__)

    def _do() -> None:
        server = None
        server_thread = None
        ext_dir = None
        driver = None
        browser_type = None
        cdp_session = None
        try:
            from selenium import webdriver

            need_net = bool(url_keyword and on_network_match)
            need_cookie = on_cookies is not None
            need_url = on_page_url is not None
            need_html = on_page_html is not None
            need_state = on_page_state is not None
            need_task_groups = on_task_groups is not None
            need_page = need_url or need_html

            net_captured: list[Any] = []
            cookie_captured: list[list[dict[str, Any]]] = []
            page_captured: list[dict[str, Any]] = []

            class _Handler(BaseHTTPRequestHandler):
                def do_POST(self) -> None:
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length)
                    try:
                        data = json.loads(body)
                        kind, payload = classify_sniff_payload(data)
                        if kind == "cookies":
                            cookie_captured.append(payload)
                        elif kind == "page":
                            page_captured.append(payload)
                        else:
                            net_captured.append(payload)
                    except Exception:
                        pass
                    self.send_response(204)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()

                def do_OPTIONS(self) -> None:
                    self.send_response(204)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Methods", "POST")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type")
                    self.end_headers()

                def log_message(self, *_args: Any) -> None:
                    pass

            server = HTTPServer(("127.0.0.1", 0), _Handler)
            port = server.server_address[1]
            server_thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
                name="bili-sniff-server",
            )
            server_thread.start()

            ext_dir = tempfile.mkdtemp(prefix="bili_sniff_")

            last_exc = None
            for browser in browser_try_order(browser_preference):
                if not find_browser(browser):
                    logger.info("未检测到 %s，跳过", browser)
                    continue
                try:
                    if browser == "edge":
                        write_edge_extension(
                            ext_dir,
                            port=port,
                            url_keyword=url_keyword,
                            need_net=need_net,
                            need_cookie=need_cookie,
                            need_page=need_page,
                        )
                        opts = webdriver.EdgeOptions()
                        opts.set_capability(
                            "goog:loggingPrefs", {"performance": "ALL"}
                        )
                        browser_binary = find_browser_binary("edge")
                        if browser_binary:
                            opts.binary_location = browser_binary
                        opts.add_argument(f"--load-extension={ext_dir}")
                        driver = webdriver.Edge(options=opts)
                        browser_type = "edge"
                    else:
                        write_chrome_extension(
                            ext_dir,
                            port=server.server_address[1],
                            url_keyword=url_keyword,
                            need_net=need_net,
                            need_cookie=need_cookie,
                            need_page=need_page,
                        )
                        opts = webdriver.ChromeOptions()
                        opts.set_capability(
                            "goog:loggingPrefs", {"performance": "ALL"}
                        )
                        browser_binary = find_browser_binary("chrome")
                        if browser_binary:
                            opts.binary_location = browser_binary
                        opts.enable_bidi = True
                        opts.enable_webextensions = True
                        opts.add_argument("--remote-allow-origins=*")
                        driver = webdriver.Chrome(options=opts)
                        browser_type = "chrome"
                        try:
                            driver.webextension.install(path=ext_dir)
                        except Exception as exc:
                            logger.error("安裝 extension 失败: %s", exc)

                    break
                except Exception as exc:
                    last_exc = exc
                    driver = None
                    browser_type = None
                    logger.warning("浏览器 %s 启动失败: %s", browser, exc)

            if driver is None:
                raise RuntimeError(
                    "未找到可用浏览器（Edge/Chrome），请确认已安装并配置好 WebDriver。"
                    f"\n最后错误: {last_exc}"
                )

            driver.get(initial_url)
            logger.info("%s（浏览器: %s）", hint, browser_label(browser_type or ""))

            cookie_done = False
            net_done = False
            url_done = False
            html_done = False
            state_done = False
            task_groups_done = False
            html_attempts = 0
            state_attempts = 0
            task_group_attempts = 0
            last_cookie_count = 0
            for _ in range(120):
                if need_cookie and not cookie_done and cookie_captured:
                    current_cookies = cookie_captured[-1]
                    filtered_cookies = select_login_cookies(current_cookies)
                    if filtered_cookies is not None and on_cookies is not None:
                        on_cookies(filtered_cookies)
                        cookie_done = True
                        logger.info("已检测到登入 Cookie")
                    elif len(cookie_captured) > last_cookie_count:
                        last_cookie_count = len(cookie_captured)

                if (need_url and not url_done) or (need_html and not html_done):
                    html_attempted = False
                    latest_page = None
                    while page_captured:
                        latest_page = page_captured.pop(0)
                    if latest_page:
                        cur_url = str(latest_page.get("url") or "")
                        room_id = extract_room_id_from_live_url(cur_url)

                        if (
                            room_id is not None
                            and need_url
                            and not url_done
                            and on_page_url is not None
                        ):
                            try:
                                on_page_url(room_id)
                                url_done = True
                            except Exception:
                                logger.exception("on_page_url 回调失败")

                        if (
                            room_id is not None
                            and need_html
                            and not html_done
                            and on_page_html is not None
                        ):
                            try:
                                page_html = str(latest_page.get("html") or "")
                                html_attempted = True
                                html_done = bool(on_page_html(page_html, cur_url))
                            except Exception:
                                logger.exception("页面源码回调失败")
                    if html_attempted and not html_done:
                        html_attempts += 1

                if (
                    need_task_groups
                    and not task_groups_done
                    and on_task_groups is not None
                    and task_group_attempts < 3
                ):
                    try:
                        cur_url = str(driver.current_url or "")
                        room_id = extract_room_id_from_live_url(cur_url)
                        if room_id is not None:
                            task_groups = collect_task_groups_from_tabs(driver)
                            task_group_attempts += 1
                            if task_groups:
                                task_groups_done = bool(
                                    on_task_groups(task_groups, cur_url)
                                )
                    except Exception:
                        task_group_attempts += 1
                        logger.exception("页面任务标签回调失败")

                if (
                    need_state
                    and not state_done
                    and on_page_state is not None
                    and (not need_task_groups or task_group_attempts >= 3)
                ):
                    try:
                        cur_url = str(driver.current_url or "")
                        room_id = extract_room_id_from_live_url(cur_url)
                        if room_id is not None:
                            page_state = driver.execute_script(
                                "return window.__initialState || null;"
                            )
                            if isinstance(page_state, dict):
                                state_done = bool(on_page_state(page_state, cur_url))
                            state_attempts += 1
                    except Exception:
                        state_attempts += 1
                        logger.exception("页面状态回调失败")

                if (
                    need_task_groups
                    and not task_groups_done
                    and task_group_attempts >= 3
                    and on_task_groups is not None
                ):
                    try:
                        cur_url = str(driver.current_url or "")
                        page_state = driver.execute_script(
                            "return window.__initialState || null;"
                        )
                        if isinstance(page_state, dict):
                            fallback_groups = (
                                extract_bili_live_task_groups_from_state(page_state)
                            )
                            if fallback_groups:
                                task_groups_done = bool(
                                    on_task_groups(fallback_groups, cur_url)
                                )
                    except Exception:
                        logger.exception("页面任务分组兜底解析失败")

                network_ready = (
                    (not need_html and not need_state and not need_task_groups)
                    or not finish_on_any
                    or html_done
                    or state_done
                    or task_groups_done
                    or max(html_attempts, state_attempts, task_group_attempts) >= 3
                )
                if (
                    need_net
                    and not net_done
                    and net_captured
                    and network_ready
                    and on_network_match is not None
                ):
                    payload = net_captured.pop(0) if finish_on_any else net_captured[0]
                    try:
                        on_network_match(payload)
                        net_done = True
                    except Exception:
                        if finish_on_any:
                            logger.exception("网络响应回调失败，继续等待其他获取方式")
                        else:
                            raise

                if is_sniff_finished(
                    (
                        (need_cookie, cookie_done),
                        (need_net, net_done),
                        (need_url, url_done),
                        (need_html, html_done),
                        (need_state, state_done),
                        (need_task_groups, task_groups_done),
                    ),
                    finish_on_any=finish_on_any,
                ):
                    break

                time.sleep(1)

        except ImportError as exc:
            on_error("依赖缺失", f"缺少依赖库，请安装后重试: {exc}\n\n")
        except Exception as exc:
            logger.exception("自动获取失败")
            on_error("错误", f"自动获取失败: {exc}")
        finally:
            if server:
                try:
                    server.shutdown()
                except Exception:
                    pass
                try:
                    server.server_close()
                except Exception:
                    pass
            if server_thread and server_thread.is_alive():
                try:
                    server_thread.join(timeout=2)
                except Exception:
                    pass
            if cdp_session:
                try:
                    cdp_session.close()
                except Exception:
                    pass
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            if ext_dir:
                shutil.rmtree(ext_dir, ignore_errors=True)

    thread = threading.Thread(target=_do, daemon=True)
    thread.start()
    return thread
