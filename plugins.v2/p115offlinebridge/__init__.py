from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from app.core.config import settings
from app.core.event import Event, eventmanager
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.schemas.types import EventType, MessageChannel

from .adapters import (
    AdapterType,
    BrowseDirResult,
    CloudDriveGrpcAdapter,
    OfflineAddResult,
    P115StrmHelperAdapter,
    ShareAddResult,
)
from .schemas import OfflineSubmitPayload, OfflineSubmitResult
from .version import VERSION


class P115OfflineBridge(_PluginBase):
    """
    115 离线下载桥接插件。
    默认调用 P115StrmHelper 的既有能力，并支持切换到 CloudDrive2 gRPC。
    """

    plugin_name = "115离线桥接"
    plugin_desc = "复用现有 115 能力提交离线任务，支持接口对象切换、系统通知与可视化目录选择。"
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Frontend/refs/heads/v2/src/assets/images/misc/u115.png"
    plugin_version = VERSION
    plugin_author = "Codex"
    author_url = "https://github.com/openai"
    plugin_config_prefix = "p115offlinebridge_"
    plugin_order = 99
    auth_level = 1

    _enabled = False
    _notify = True
    _adapter: AdapterType = "p115_strmhelper"

    _moviepilot_url = ""
    _moviepilot_api_token = ""
    _request_timeout = 20

    _p115_target_path = ""
    _p115_path_select_mode = "fixed"
    _p115_target_paths = ""
    _auto_recognize_enabled = True
    _auto_recognize_allow_http_torrent = True
    _auto_recognize_share_enabled = True

    _u115_share_url_pattern = re.compile(
        r"^https?://(.*\.)?115[^/]*\.[a-zA-Z]{2,}(?:/|$)", re.IGNORECASE
    )
    _share_code_pattern = re.compile(r"([a-zA-Z0-9]{4})")

    _cd2_host = "localhost"
    _cd2_port = 19798
    _cd2_username = ""
    _cd2_password = ""
    _cd2_target_path = "/"
    _cd2_check_after_secs = 10

    def init_plugin(self, config: dict = None):
        conf = config or {}

        self._enabled = bool(conf.get("enabled", False))
        self._notify = bool(conf.get("notify", True))

        adapter = str(conf.get("adapter") or "p115_strmhelper").strip()
        if adapter not in ("p115_strmhelper", "clouddrive2_grpc"):
            adapter = "p115_strmhelper"
        self._adapter = adapter

        self._moviepilot_url = (
            str(conf.get("moviepilot_url") or self._default_moviepilot_url()).strip().rstrip("/")
        )
        self._moviepilot_api_token = str(
            conf.get("moviepilot_api_token") or settings.API_TOKEN or ""
        ).strip()

        self._request_timeout = self._safe_int(conf.get("request_timeout"), 20)
        if self._request_timeout <= 0:
            self._request_timeout = 20

        self._p115_target_path = str(conf.get("p115_target_path") or "").strip()
        self._p115_path_select_mode = str(
            conf.get("p115_path_select_mode") or "fixed"
        ).strip()
        if self._p115_path_select_mode not in ("fixed", "round_robin", "random"):
            self._p115_path_select_mode = "fixed"
        self._p115_target_paths = str(conf.get("p115_target_paths") or "").strip()
        self._auto_recognize_enabled = bool(conf.get("auto_recognize_enabled", True))
        self._auto_recognize_allow_http_torrent = bool(
            conf.get("auto_recognize_allow_http_torrent", True)
        )
        self._auto_recognize_share_enabled = bool(
            conf.get("auto_recognize_share_enabled", True)
        )

        self._cd2_host = str(conf.get("cd2_host") or "localhost").strip() or "localhost"
        self._cd2_port = self._safe_int(conf.get("cd2_port"), 19798)
        self._cd2_username = str(conf.get("cd2_username") or "").strip()
        self._cd2_password = str(conf.get("cd2_password") or "")
        self._cd2_target_path = str(conf.get("cd2_target_path") or "/").strip() or "/"
        self._cd2_check_after_secs = self._safe_int(
            conf.get("cd2_check_after_secs"), 10
        )
        if self._cd2_check_after_secs < 0:
            self._cd2_check_after_secs = 0

    def _default_moviepilot_url(self) -> str:
        try:
            base = settings.MP_DOMAIN("")
            if isinstance(base, str) and base.strip():
                return base.rstrip("/")
        except Exception:
            pass
        return "http://127.0.0.1:3000"

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return [
            {
                "cmd": "/p115_offline",
                "event": EventType.PluginAction,
                "desc": "提交 115 离线下载任务",
                "category": "",
                "data": {"action": "p115offlinebridge_add"},
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/submit",
                "endpoint": self.submit_api,
                "methods": ["POST"],
                "auth": "apikey",
                "summary": "提交离线任务",
                "description": "提交离线下载任务并返回执行结果",
            },
            {
                "path": "/status",
                "endpoint": self.status_api,
                "methods": ["GET"],
                "auth": "apikey",
                "summary": "查看插件状态",
                "description": "返回当前启用状态和接口配置摘要",
            },
            {
                "path": "/browse_dir",
                "endpoint": self.browse_dir_api,
                "methods": ["GET"],
                "auth": "apikey",
                "summary": "浏览115目录",
                "description": "调用 P115StrmHelper 的 browse_dir 接口浏览网盘目录",
            },
        ]

    @staticmethod
    def get_render_mode() -> Tuple[str, Optional[str]]:
        return "vue", "dist/assets"

    def _default_form_model(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "notify": True,
            "adapter": "p115_strmhelper",
            "moviepilot_url": self._default_moviepilot_url(),
            "moviepilot_api_token": "",
            "request_timeout": 20,
            "p115_target_path": "",
            "p115_path_select_mode": "fixed",
            "p115_target_paths": "",
            "auto_recognize_enabled": True,
            "auto_recognize_share_enabled": True,
            "auto_recognize_allow_http_torrent": True,
            "cd2_host": "localhost",
            "cd2_port": 19798,
            "cd2_username": "",
            "cd2_password": "",
            "cd2_target_path": "/",
            "cd2_check_after_secs": 10,
        }

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        return None, self._default_form_model()

    def get_page(self) -> Optional[List[dict]]:
        return None

    def stop_service(self):
        pass

    @staticmethod
    def _parse_links(links: Optional[List[str]] = None, link_text: Optional[str] = None) -> List[str]:
        values: List[str] = []

        if links:
            values.extend([str(item) for item in links if item is not None])

        if link_text:
            values.append(str(link_text))

        candidates: List[str] = []
        for value in values:
            normalized = (
                value.replace("\r", "\n")
                .replace("，", ",")
                .replace("；", ";")
                .strip()
            )
            if not normalized:
                continue
            for line in normalized.split("\n"):
                parts = line.replace(";", ",").split(",")
                for part in parts:
                    token = part.strip()
                    if token:
                        candidates.append(token)

        unique: List[str] = []
        seen = set()
        for item in candidates:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)

        return unique

    @staticmethod
    def _parse_paths(path_text: str) -> List[str]:
        if not path_text:
            return []
        raw_items = (
            path_text.replace("\r", "\n")
            .replace("，", ",")
            .replace("；", ";")
            .replace(";", ",")
        )
        paths: List[str] = []
        for line in raw_items.split("\n"):
            for token in line.split(","):
                p = token.strip()
                if not p:
                    continue
                if not p.startswith("/"):
                    p = "/" + p
                paths.append(p)

        unique: List[str] = []
        seen = set()
        for item in paths:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)
        return unique

    def _select_p115_target_path(self) -> Optional[str]:
        fixed = self._p115_target_path.strip() if self._p115_target_path else ""
        candidates = self._parse_paths(self._p115_target_paths)
        mode = self._p115_path_select_mode

        if mode == "fixed":
            if fixed:
                return fixed
            return candidates[0] if candidates else None

        if not candidates:
            return fixed or None

        if mode == "random":
            return random.choice(candidates)

        # round_robin
        idx = self._safe_int(self.get_data("p115_path_rr_index"), 0)
        selected = candidates[idx % len(candidates)]
        self.save_data("p115_path_rr_index", (idx + 1) % len(candidates))
        return selected

    def _extract_auto_links(self, text: str) -> List[str]:
        parsed = self._parse_links(link_text=text)
        links: List[str] = []
        for token in parsed:
            lower = token.lower()
            if lower.startswith("magnet:?"):
                links.append(token)
                continue
            if (
                self._auto_recognize_allow_http_torrent
                and (lower.startswith("http://") or lower.startswith("https://"))
                and ".torrent" in lower
            ):
                links.append(token)
        # 去重
        unique: List[str] = []
        seen = set()
        for item in links:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)
        return unique

    def _is_115_share_url(self, token: str) -> bool:
        if not token:
            return False
        try:
            parsed = urlparse(token)
            if parsed.scheme not in ("http", "https"):
                return False
        except Exception:
            return False
        return bool(self._u115_share_url_pattern.match(token))

    def _extract_access_code(self, text: str) -> Optional[str]:
        if not text:
            return None
        patterns = [
            r"(?:访问码|提取码|密码|password)\s*[:：]\s*([a-zA-Z0-9]{4})",
            r"(?:访问码|提取码|密码|password)\s*([a-zA-Z0-9]{4})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    @staticmethod
    def _normalize_115_share_url(url: str, access_code: Optional[str]) -> str:
        parsed = urlparse(url.strip())
        query = parse_qs(parsed.query, keep_blank_values=True)
        has_password = bool(query.get("password"))
        if (not has_password) and access_code:
            query["password"] = [access_code]
            new_query = urlencode(query, doseq=True)
            parsed = parsed._replace(query=new_query)
            return urlunparse(parsed)
        return url.strip()

    def _extract_share_urls(self, text: str) -> List[str]:
        parsed_tokens = self._parse_links(link_text=text)
        access_code = self._extract_access_code(text)
        result: List[str] = []
        for token in parsed_tokens:
            if not self._is_115_share_url(token):
                continue
            result.append(self._normalize_115_share_url(token, access_code))

        unique: List[str] = []
        seen = set()
        for item in result:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)
        return unique

    def _submit_share_links(self, share_urls: List[str]) -> ShareAddResult:
        adapter = P115StrmHelperAdapter(
            moviepilot_url=self._moviepilot_url,
            api_token=self._moviepilot_api_token,
            timeout=self._request_timeout,
        )
        result = adapter.add_share_urls(share_urls)
        if result.success:
            logger.info(
                "【%s】分享转存提交成功: total=%s",
                self.plugin_name,
                result.total,
            )
        else:
            logger.warning(
                "【%s】分享转存提交失败: total=%s success=%s failed=%s message=%s",
                self.plugin_name,
                result.total,
                result.success_count,
                result.failed_count,
                result.message,
            )
        return result

    def _notify_share_submit(
        self,
        result: ShareAddResult,
        channel: MessageChannel = None,
        userid: Optional[str] = None,
        force_notify: Optional[bool] = None,
    ):
        should_notify = self._notify if force_notify is None else bool(force_notify)
        if not should_notify:
            return
        title = f"【{self.plugin_name}】分享转存{'成功' if result.success else '失败'}"
        text = (
            f"接口对象: {result.adapter}\n"
            f"任务总数: {result.total}\n"
            f"成功: {result.success_count}\n"
            f"失败: {result.failed_count}\n"
            f"结果: {result.message}"
        )
        self.post_message(
            channel=channel,
            mtype=NotificationType.Plugin,
            title=title,
            text=text,
            userid=userid,
        )

    def _build_adapter(self, adapter_name: AdapterType):
        if adapter_name == "clouddrive2_grpc":
            return CloudDriveGrpcAdapter(
                host=self._cd2_host,
                port=self._cd2_port,
                username=self._cd2_username,
                password=self._cd2_password,
                timeout=self._request_timeout,
                check_after_secs=self._cd2_check_after_secs,
            )

        return P115StrmHelperAdapter(
            moviepilot_url=self._moviepilot_url,
            api_token=self._moviepilot_api_token,
            timeout=self._request_timeout,
        )

    def _resolve_target_path(self, adapter_name: AdapterType, path: Optional[str]) -> Optional[str]:
        if path and path.strip():
            return path.strip()

        if adapter_name == "clouddrive2_grpc":
            return self._cd2_target_path or "/"

        return self._select_p115_target_path()

    def _submit_links(
        self,
        links: List[str],
        path: Optional[str] = None,
        adapter_name: Optional[str] = None,
    ) -> OfflineAddResult:
        use_adapter = (adapter_name or self._adapter).strip()
        if use_adapter not in ("p115_strmhelper", "clouddrive2_grpc"):
            use_adapter = "p115_strmhelper"

        typed_adapter: AdapterType = use_adapter  # type: ignore[assignment]
        target_path = self._resolve_target_path(typed_adapter, path)
        adapter = self._build_adapter(typed_adapter)
        result = adapter.add_links(links=links, target_path=target_path)

        if result.success:
            logger.info(
                "【%s】提交成功: adapter=%s total=%s target=%s",
                self.plugin_name,
                result.adapter,
                result.total,
                result.target_path,
            )
        else:
            logger.warning(
                "【%s】提交失败: adapter=%s total=%s target=%s message=%s",
                self.plugin_name,
                result.adapter,
                result.total,
                result.target_path,
                result.message,
            )

        return result

    def _notify_submit(
        self,
        result: OfflineAddResult,
        channel: MessageChannel = None,
        userid: Optional[str] = None,
        force_notify: Optional[bool] = None,
    ):
        should_notify = self._notify if force_notify is None else bool(force_notify)
        if not should_notify:
            return

        title = f"【{self.plugin_name}】离线任务提交{'成功' if result.success else '失败'}"
        text = (
            f"接口对象: {result.adapter}\n"
            f"目标目录: {result.target_path or '-'}\n"
            f"任务数量: {result.total}\n"
            f"结果: {result.message}"
        )
        self.post_message(
            channel=channel,
            mtype=NotificationType.Plugin,
            title=title,
            text=text,
            userid=userid,
        )

    def submit_api(self, payload: OfflineSubmitPayload) -> Dict[str, Any]:
        if not self._enabled:
            return {"code": -1, "msg": "插件未启用"}

        links = self._parse_links(links=payload.links, link_text=payload.link_text)
        if not links:
            return {"code": -1, "msg": "未解析到可用链接"}

        result = self._submit_links(
            links=links,
            path=payload.path,
            adapter_name=payload.adapter,
        )

        self._notify_submit(result=result, force_notify=payload.notify)

        data = OfflineSubmitResult(**result.to_dict()).model_dump()
        return {
            "code": 0 if result.success else -1,
            "msg": result.message,
            "data": data,
        }

    def status_api(self) -> Dict[str, Any]:
        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "enabled": self._enabled,
                "notify": self._notify,
                "adapter": self._adapter,
                "moviepilot_url": self._moviepilot_url,
                "p115_target_path": self._p115_target_path,
                "p115_path_select_mode": self._p115_path_select_mode,
                "p115_target_paths": self._p115_target_paths,
                "p115_target_paths_parsed": self._parse_paths(self._p115_target_paths),
                "auto_recognize_enabled": self._auto_recognize_enabled,
                "auto_recognize_share_enabled": self._auto_recognize_share_enabled,
                "auto_recognize_allow_http_torrent": self._auto_recognize_allow_http_torrent,
                "cd2_host": self._cd2_host,
                "cd2_port": self._cd2_port,
                "cd2_target_path": self._cd2_target_path,
            },
        }

    @staticmethod
    def _normalize_browse_path(path: Optional[str]) -> str:
        normalized = str(path or "/").strip() or "/"
        if not normalized.startswith("/"):
            normalized = "/" + normalized
        if len(normalized) > 1:
            normalized = normalized.rstrip("/") or "/"
        return normalized

    def browse_dir_api(self, path: str = "/", is_local: bool = False) -> Dict[str, Any]:
        if bool(is_local):
            return {
                "code": -1,
                "msg": "仅支持 115 网盘目录浏览，请使用 is_local=false",
                "data": {"path": "/", "items": []},
            }

        normalized_path = self._normalize_browse_path(path)
        adapter = P115StrmHelperAdapter(
            moviepilot_url=self._moviepilot_url,
            api_token=self._moviepilot_api_token,
            timeout=self._request_timeout,
        )
        result: BrowseDirResult = adapter.browse_dir(
            path=normalized_path,
            is_local=False,
        )
        if not result.success:
            return {
                "code": -1,
                "msg": result.message,
                "data": {"path": normalized_path, "items": []},
            }

        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "path": result.path or normalized_path,
                "items": [item.to_dict() for item in result.items if item.is_dir],
            },
        }

    @eventmanager.register(EventType.PluginAction)
    def handle_plugin_action(self, event: Event):
        if not self._enabled or not event:
            return

        event_data = event.event_data or {}
        if event_data.get("action") != "p115offlinebridge_add":
            return

        link_text = str(event_data.get("arg_str") or "").strip()
        share_urls = self._extract_share_urls(link_text)
        if share_urls:
            share_result = self._submit_share_links(share_urls=share_urls)
            self._notify_share_submit(
                result=share_result,
                channel=event_data.get("channel"),
                userid=event_data.get("user"),
                force_notify=True,
            )
            return

        links = self._parse_links(link_text=link_text)
        if not links:
            self._notify_submit(
                result=OfflineAddResult(
                    success=False,
                    adapter=self._adapter,
                    total=0,
                    target_path=self._resolve_target_path(self._adapter, None),
                    message="参数为空或无可用链接，命令格式：/p115_offline <链接>",
                ),
                channel=event_data.get("channel"),
                userid=event_data.get("user"),
                force_notify=True,
            )
            return

        result = self._submit_links(links=links)
        self._notify_submit(
            result=result,
            channel=event_data.get("channel"),
            userid=event_data.get("user"),
            force_notify=True,
        )

    @eventmanager.register(EventType.UserMessage)
    def handle_user_message_auto_submit(self, event: Event):
        """
        自动识别用户发送的磁力链接并提交离线任务。
        """
        if not self._enabled or not self._auto_recognize_enabled or not event:
            return

        event_data = event.event_data or {}
        text = str(event_data.get("text") or "").strip()
        if not text:
            return
        # 跳过命令，避免与 /p115_offline 指令重复触发
        if text.startswith("/"):
            return

        if self._auto_recognize_share_enabled:
            share_urls = self._extract_share_urls(text)
            if share_urls:
                share_result = self._submit_share_links(share_urls=share_urls)
                self._notify_share_submit(
                    result=share_result,
                    channel=event_data.get("channel"),
                    userid=event_data.get("userid") or event_data.get("user"),
                    force_notify=True,
                )
                return

        links = self._extract_auto_links(text)
        if not links:
            return

        result = self._submit_links(links=links)
        self._notify_submit(
            result=result,
            channel=event_data.get("channel"),
            userid=event_data.get("userid") or event_data.get("user"),
            force_notify=True,
        )
