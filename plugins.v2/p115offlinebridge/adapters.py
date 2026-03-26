from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, List, Literal, Optional

from app.log import logger
from app.utils.http import RequestUtils


AdapterType = Literal["p115_strmhelper", "clouddrive2_grpc"]


@dataclass
class OfflineAddResult:
    success: bool
    adapter: str
    total: int
    target_path: Optional[str]
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ShareAddResult:
    success: bool
    adapter: str
    total: int
    success_count: int
    failed_count: int
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BrowseDirItem:
    name: str
    path: str
    is_dir: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BrowseDirResult:
    success: bool
    adapter: str
    path: str
    items: List[BrowseDirItem]
    message: str

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "adapter": self.adapter,
            "path": self.path,
            "items": [item.to_dict() for item in self.items],
            "message": self.message,
        }


class P115StrmHelperAdapter:
    """
    通过 MoviePilot 插件 API 调用 P115StrmHelper 现有离线下载能力。
    """

    def __init__(self, moviepilot_url: str, api_token: str, timeout: int = 20):
        self._moviepilot_url = (moviepilot_url or "").rstrip("/")
        self._api_token = api_token or ""
        self._timeout = timeout

    @staticmethod
    def _downstream_label() -> str:
        return "115离线桥接下游接口（P115StrmHelper）"

    @staticmethod
    def _sanitize_downstream_message(message: Any) -> str:
        text = str(message or "").strip()
        if not text:
            return ""
        replacements = {
            "115STRM助手": "下游接口",
            "115网盘STRM助手": "下游接口",
            "P115StrmHelper": "下游接口",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def _load_json_body(response: Any) -> Optional[dict]:
        body = None
        try:
            body = response.json()
        except Exception:
            try:
                body = json.loads(response.text)
            except Exception:
                body = None
        return body if isinstance(body, dict) else None

    def add_links(self, links: List[str], target_path: Optional[str] = None) -> OfflineAddResult:
        target_path = str(target_path or "").strip() or None
        if not links:
            return OfflineAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=0,
                target_path=target_path,
                message="未提供可用链接",
            )

        if not self._moviepilot_url:
            return OfflineAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=len(links),
                target_path=target_path,
                message="MoviePilot 地址未配置",
            )

        if not self._api_token:
            return OfflineAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=len(links),
                target_path=target_path,
                message="MoviePilot API Token 未配置",
            )

        payload = {"links": links}
        request_params = {"apikey": self._api_token}
        if target_path:
            # 兼容不同历史版本字段名，避免下游忽略 path 导致落回默认目录。
            payload["path"] = target_path
            payload["target_path"] = target_path
            payload["savepath"] = target_path
            payload["dir_path"] = target_path
            request_params["path"] = target_path
            request_params["savepath"] = target_path

        url = f"{self._moviepilot_url}/api/v1/plugin/P115StrmHelper/add_offline_task"
        try:
            response = RequestUtils(
                content_type="application/json",
                timeout=self._timeout,
            ).post_res(
                url=url,
                params=request_params,
                json=payload,
            )
            if not response:
                return OfflineAddResult(
                    success=False,
                    adapter="p115_strmhelper",
                    total=len(links),
                    target_path=target_path,
                    message=(
                        f"{self._downstream_label()}调用失败："
                        f"无响应（{self._moviepilot_url}）"
                    ),
                )

            body = self._load_json_body(response)

            if response.status_code >= 400:
                err_msg = None
                if isinstance(body, dict):
                    err_msg = body.get("msg") or body.get("message")
                err_msg = err_msg or f"HTTP {response.status_code}"
                err_msg = self._sanitize_downstream_message(err_msg)
                return OfflineAddResult(
                    success=False,
                    adapter="p115_strmhelper",
                    total=len(links),
                    target_path=target_path,
                    message=f"{self._downstream_label()}返回错误：{err_msg}",
                )

            if not body:
                return OfflineAddResult(
                    success=False,
                    adapter="p115_strmhelper",
                    total=len(links),
                    target_path=target_path,
                    message="调用失败：响应不是有效 JSON",
                )

            code = int(body.get("code", 0))
            msg = self._sanitize_downstream_message(body.get("msg"))
            if code == 0:
                return OfflineAddResult(
                    success=True,
                    adapter="p115_strmhelper",
                    total=len(links),
                    target_path=target_path,
                    message=msg or "离线任务提交成功",
                )

            return OfflineAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=len(links),
                target_path=target_path,
                message=msg or "离线任务提交失败",
            )
        except Exception as err:
            logger.error(
                "【115离线桥接】下游接口 P115StrmHelper 调用异常: %s",
                err,
                exc_info=True,
            )
            return OfflineAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=len(links),
                target_path=target_path,
                message=f"{self._downstream_label()}调用异常：{err}",
            )

    def add_share_urls(self, share_urls: List[str]) -> ShareAddResult:
        if not share_urls:
            return ShareAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=0,
                success_count=0,
                failed_count=0,
                message="未提供可用分享链接",
            )

        if not self._moviepilot_url:
            return ShareAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=len(share_urls),
                success_count=0,
                failed_count=len(share_urls),
                message="MoviePilot 地址未配置",
            )

        if not self._api_token:
            return ShareAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=len(share_urls),
                success_count=0,
                failed_count=len(share_urls),
                message="MoviePilot API Token 未配置",
            )

        success_count = 0
        failed_count = 0
        fail_messages: List[str] = []
        url = f"{self._moviepilot_url}/api/v1/plugin/P115StrmHelper/add_transfer_share"

        for share_url in share_urls:
            try:
                response = RequestUtils(
                    content_type="application/json",
                    timeout=self._timeout,
                ).get_res(
                    url=url,
                    params={"apikey": self._api_token, "share_url": share_url},
                )
                if not response:
                    failed_count += 1
                    fail_messages.append(f"无响应（{self._moviepilot_url}）")
                    continue

                body = self._load_json_body(response)

                if response.status_code >= 400:
                    failed_count += 1
                    if isinstance(body, dict):
                        err_msg = body.get("msg") or body.get("message") or response.status_code
                        fail_messages.append(self._sanitize_downstream_message(err_msg))
                    else:
                        fail_messages.append(str(response.status_code))
                    continue

                if body:
                    code = int(body.get("code", 0))
                    if code == 0:
                        success_count += 1
                    else:
                        failed_count += 1
                        fail_messages.append(
                            self._sanitize_downstream_message(body.get("msg") or "转存失败")
                        )
                else:
                    failed_count += 1
                    fail_messages.append("响应不是有效 JSON")
            except Exception as err:
                failed_count += 1
                fail_messages.append(str(err))
                logger.error(
                    "【115离线桥接】下游接口 P115StrmHelper 分享转存调用异常: %s",
                    err,
                    exc_info=True,
                )

        total = len(share_urls)
        ok = failed_count == 0
        if ok:
            message = f"分享转存任务提交成功（{success_count}/{total}）"
        else:
            first_fail = fail_messages[0] if fail_messages else "未知错误"
            message = (
                f"分享转存部分/全部失败（成功 {success_count}，失败 {failed_count}）："
                f"{self._downstream_label()}返回 {first_fail}"
            )

        return ShareAddResult(
            success=ok,
            adapter="p115_strmhelper",
            total=total,
            success_count=success_count,
            failed_count=failed_count,
            message=message,
        )

    def browse_dir(self, path: str = "/", is_local: bool = False) -> BrowseDirResult:
        normalized_path = (path or "/").strip() or "/"
        if not normalized_path.startswith("/"):
            normalized_path = "/" + normalized_path
        if len(normalized_path) > 1:
            normalized_path = normalized_path.rstrip("/")
            if not normalized_path:
                normalized_path = "/"

        if not self._moviepilot_url:
            return BrowseDirResult(
                success=False,
                adapter="p115_strmhelper",
                path=normalized_path,
                items=[],
                message="MoviePilot 地址未配置",
            )
        if not self._api_token:
            return BrowseDirResult(
                success=False,
                adapter="p115_strmhelper",
                path=normalized_path,
                items=[],
                message="MoviePilot API Token 未配置",
            )

        try:
            url = f"{self._moviepilot_url}/api/v1/plugin/P115StrmHelper/browse_dir"
            response = RequestUtils(
                content_type="application/json",
                timeout=self._timeout,
            ).get_res(
                url=url,
                params={
                    "apikey": self._api_token,
                    "path": normalized_path,
                    "is_local": str(bool(is_local)).lower(),
                },
            )
            if not response:
                return BrowseDirResult(
                    success=False,
                    adapter="p115_strmhelper",
                    path=normalized_path,
                    items=[],
                    message=(
                        f"{self._downstream_label()}浏览目录调用失败："
                        f"无响应（{self._moviepilot_url}）"
                    ),
                )

            body = self._load_json_body(response)
            if response.status_code >= 400:
                err_msg = None
                if body:
                    err_msg = body.get("msg") or body.get("message")
                err_msg = err_msg or f"HTTP {response.status_code}"
                err_msg = self._sanitize_downstream_message(err_msg)
                return BrowseDirResult(
                    success=False,
                    adapter="p115_strmhelper",
                    path=normalized_path,
                    items=[],
                    message=f"浏览目录失败：{err_msg}",
                )

            if not body:
                return BrowseDirResult(
                    success=False,
                    adapter="p115_strmhelper",
                    path=normalized_path,
                    items=[],
                    message="浏览目录失败：响应不是有效 JSON",
                )

            code = int(body.get("code", 0))
            if code != 0:
                return BrowseDirResult(
                    success=False,
                    adapter="p115_strmhelper",
                    path=normalized_path,
                    items=[],
                    message=self._sanitize_downstream_message(
                        body.get("msg") or "浏览目录失败"
                    ),
                )

            data = body.get("data")
            if not isinstance(data, dict):
                data = {}
            result_path = str(data.get("path") or normalized_path)
            raw_items = data.get("items")
            if not isinstance(raw_items, list):
                raw_items = []

            items: List[BrowseDirItem] = []
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                item_path = str(raw_item.get("path") or "")
                item_name = str(raw_item.get("name") or "")
                if not item_path and not item_name:
                    continue
                items.append(
                    BrowseDirItem(
                        name=item_name or item_path.rstrip("/").split("/")[-1] or "/",
                        path=item_path or item_name,
                        is_dir=bool(raw_item.get("is_dir")),
                    )
                )
            items = sorted(items, key=lambda item: item.name)

            return BrowseDirResult(
                success=True,
                adapter="p115_strmhelper",
                path=result_path,
                items=items,
                message="ok",
            )
        except Exception as err:
            logger.error(
                "【115离线桥接】下游接口 P115StrmHelper 浏览目录调用异常: %s",
                err,
                exc_info=True,
            )
            return BrowseDirResult(
                success=False,
                adapter="p115_strmhelper",
                path=normalized_path,
                items=[],
                message=f"{self._downstream_label()}调用异常：{err}",
            )


class CloudDriveGrpcAdapter:
    """
    通过 CloudDrive2 gRPC 直接提交离线任务。
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int = 20,
        check_after_secs: int = 10,
    ):
        self._host = (host or "localhost").strip()
        self._port = int(port or 19798)
        self._username = (username or "").strip()
        self._password = password or ""
        self._timeout = timeout
        self._check_after_secs = max(int(check_after_secs or 0), 0)

    @staticmethod
    def _extract_message(obj: Any, default: str = "未知错误") -> str:
        if obj is None:
            return default

        keys = (
            "errorMessage",
            "error_message",
            "message",
            "msg",
            "reason",
            "detail",
            "details",
        )

        if isinstance(obj, dict):
            for key in keys:
                value = obj.get(key)
                if value is not None and str(value).strip():
                    return str(value).strip()
            return default

        for key in keys:
            value = getattr(obj, key, None)
            if value is not None and str(value).strip():
                return str(value).strip()
        return default

    @staticmethod
    def _extract_success(obj: Any) -> bool:
        if isinstance(obj, bool):
            return bool(obj)
        if obj is None:
            return False

        if isinstance(obj, dict):
            for key in ("success", "ok", "result"):
                if key in obj:
                    return bool(obj.get(key))
            return False

        for key in ("success", "ok", "result"):
            if hasattr(obj, key):
                return bool(getattr(obj, key))
        return False

    def _new_cd2_client(self):
        from clouddrive2_client import CloudDriveClient

        address = f"{self._host}:{self._port}"
        options = [
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
            ("grpc.keepalive_permit_without_calls", True),
            ("grpc.http2.max_pings_without_data", 0),
        ]
        try:
            return CloudDriveClient(address, options=options)
        except TypeError:
            return CloudDriveClient(address)

    @staticmethod
    def _close_cd2_client(client: Any):
        try:
            close_fn = getattr(client, "close", None)
            if callable(close_fn):
                close_fn()
        except Exception:
            pass

    def _authenticate_cd2_client(self, client: Any) -> Optional[str]:
        auth_fn = getattr(client, "authenticate", None)
        if callable(auth_fn):
            try:
                ok = auth_fn(self._username, self._password)
            except TypeError:
                ok = auth_fn(username=self._username, password=self._password)
            if ok:
                return None
            return "CloudDrive2 认证失败：用户名或密码错误"

        login_fn = getattr(client, "login", None)
        if callable(login_fn):
            try:
                resp = login_fn(self._username, self._password)
            except TypeError:
                resp = login_fn(username=self._username, password=self._password)
            if self._extract_success(resp):
                return None
            return f"CloudDrive2 认证失败：{self._extract_message(resp)}"

        return "CloudDrive2 客户端不支持认证方法"

    @staticmethod
    def _iter_cd2_entries(response: Any) -> List[Any]:
        if response is None:
            return []
        if isinstance(response, list):
            return response
        if isinstance(response, tuple):
            return list(response)
        if isinstance(response, dict):
            raw = response.get("subFiles") or response.get("sub_files") or response.get("items")
            if isinstance(raw, list):
                return raw
            return []
        if hasattr(response, "subFiles"):
            raw = getattr(response, "subFiles")
            if isinstance(raw, list):
                return raw
            try:
                return list(raw)
            except Exception:
                return []
        try:
            if isinstance(response, (str, bytes, bytearray)):
                return []
            return list(response)
        except Exception:
            return []

    def _add_links_via_client(
        self, links: List[str], target_path: Optional[str]
    ) -> Optional[OfflineAddResult]:
        try:
            client = self._new_cd2_client()
        except Exception:
            return None

        try:
            auth_error = self._authenticate_cd2_client(client)
            if auth_error:
                return OfflineAddResult(
                    success=False,
                    adapter="clouddrive2_grpc",
                    total=len(links),
                    target_path=(target_path or "/"),
                    message=auth_error,
                )

            add_fn = getattr(client, "add_offline_files", None)
            if not callable(add_fn):
                add_fn = getattr(client, "add_offline_file", None)
            if not callable(add_fn):
                return OfflineAddResult(
                    success=False,
                    adapter="clouddrive2_grpc",
                    total=len(links),
                    target_path=(target_path or "/"),
                    message="CloudDrive2 客户端不支持离线提交接口",
                )

            urls_text = "\n".join(links)
            to_folder = target_path or "/"

            attempts = [
                ((), {"urls": urls_text, "to_folder": to_folder, "check_folder_after_secs": self._check_after_secs}),
                ((), {"urls": urls_text, "toFolder": to_folder, "checkFolderAfterSecs": self._check_after_secs}),
                ((urls_text, to_folder, self._check_after_secs), {}),
                ((urls_text, to_folder), {}),
                ((), {"urls": links, "to_folder": to_folder, "check_folder_after_secs": self._check_after_secs}),
                ((), {"urls": links, "toFolder": to_folder, "checkFolderAfterSecs": self._check_after_secs}),
                ((links, to_folder), {}),
            ]

            response = None
            last_type_error: Optional[Exception] = None
            for args, kwargs in attempts:
                try:
                    response = add_fn(*args, **kwargs)
                    last_type_error = None
                    break
                except TypeError as err:
                    last_type_error = err
                    continue

            if last_type_error is not None and response is None:
                return OfflineAddResult(
                    success=False,
                    adapter="clouddrive2_grpc",
                    total=len(links),
                    target_path=to_folder,
                    message=f"CloudDrive2 客户端调用参数不兼容：{last_type_error}",
                )

            if self._extract_success(response):
                return OfflineAddResult(
                    success=True,
                    adapter="clouddrive2_grpc",
                    total=len(links),
                    target_path=to_folder,
                    message="CloudDrive2 离线任务提交成功",
                )

            return OfflineAddResult(
                success=False,
                adapter="clouddrive2_grpc",
                total=len(links),
                target_path=to_folder,
                message=f"CloudDrive2 提交失败：{self._extract_message(response)}",
            )
        except Exception as err:
            logger.error("CloudDrive2 客户端离线任务提交异常: %s", err, exc_info=True)
            return OfflineAddResult(
                success=False,
                adapter="clouddrive2_grpc",
                total=len(links),
                target_path=(target_path or "/"),
                message=f"CloudDrive2 调用异常：{err}",
            )
        finally:
            self._close_cd2_client(client)

    def _browse_dir_via_client(self, normalized_path: str) -> Optional[BrowseDirResult]:
        try:
            client = self._new_cd2_client()
        except Exception:
            return None

        try:
            auth_error = self._authenticate_cd2_client(client)
            if auth_error:
                return BrowseDirResult(
                    success=False,
                    adapter="clouddrive2_grpc",
                    path=normalized_path,
                    items=[],
                    message=auth_error,
                )

            list_fn = getattr(client, "get_sub_files", None)
            if not callable(list_fn):
                list_fn = getattr(client, "list_sub_files", None)
            if not callable(list_fn):
                return BrowseDirResult(
                    success=False,
                    adapter="clouddrive2_grpc",
                    path=normalized_path,
                    items=[],
                    message="CloudDrive2 客户端不支持目录浏览接口",
                )

            attempts = [
                ((normalized_path,), {"force_refresh": False}),
                ((normalized_path,), {"forceRefresh": False}),
                ((), {"path": normalized_path, "force_refresh": False}),
                ((), {"path": normalized_path, "forceRefresh": False}),
                ((normalized_path,), {}),
            ]

            response = None
            last_type_error: Optional[Exception] = None
            for args, kwargs in attempts:
                try:
                    response = list_fn(*args, **kwargs)
                    last_type_error = None
                    break
                except TypeError as err:
                    last_type_error = err
                    continue

            if last_type_error is not None and response is None:
                return BrowseDirResult(
                    success=False,
                    adapter="clouddrive2_grpc",
                    path=normalized_path,
                    items=[],
                    message=f"CloudDrive2 客户端调用参数不兼容：{last_type_error}",
                )

            entries = self._iter_cd2_entries(response)
            items: List[BrowseDirItem] = []
            for sub in entries:
                is_dir = bool(
                    getattr(sub, "isDirectory", False)
                    or getattr(sub, "is_directory", False)
                )
                if not is_dir:
                    try:
                        is_dir = int(getattr(sub, "fileType", getattr(sub, "file_type", 1))) == 0
                    except Exception:
                        is_dir = False
                if not is_dir:
                    continue

                sub_path = str(
                    getattr(sub, "fullPathName", "")
                    or getattr(sub, "full_path_name", "")
                    or getattr(sub, "path", "")
                    or ""
                ).strip()
                sub_name = str(getattr(sub, "name", "") or "").strip()
                if not sub_path and not sub_name:
                    continue

                items.append(
                    BrowseDirItem(
                        name=sub_name or sub_path.rstrip("/").split("/")[-1] or "/",
                        path=sub_path or sub_name,
                        is_dir=True,
                    )
                )

            items = sorted(items, key=lambda x: x.path or x.name)
            return BrowseDirResult(
                success=True,
                adapter="clouddrive2_grpc",
                path=normalized_path,
                items=items,
                message="ok",
            )
        except Exception as err:
            logger.error("CloudDrive2 客户端浏览目录异常: %s", err, exc_info=True)
            return BrowseDirResult(
                success=False,
                adapter="clouddrive2_grpc",
                path=normalized_path,
                items=[],
                message=f"CloudDrive2 调用异常：{err}",
            )
        finally:
            self._close_cd2_client(client)

    def _add_links_via_grpc_fallback(
        self, links: List[str], target_path: Optional[str]
    ) -> OfflineAddResult:
        try:
            import grpc
            from . import clouddrive_pb2
            from . import clouddrive_pb2_grpc
        except Exception as err:
            return OfflineAddResult(
                success=False,
                adapter="clouddrive2_grpc",
                total=len(links),
                target_path=target_path,
                message=f"CloudDrive2 依赖未就绪：{err}",
            )

        address = f"{self._host}:{self._port}"
        channel = grpc.insecure_channel(address)
        try:
            stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(channel)
            token_req = clouddrive_pb2.GetTokenRequest(
                userName=self._username,
                password=self._password,
            )
            token_resp = stub.GetToken(token_req, timeout=self._timeout)
            if not token_resp.success or not token_resp.token:
                return OfflineAddResult(
                    success=False,
                    adapter="clouddrive2_grpc",
                    total=len(links),
                    target_path=target_path,
                    message=f"CloudDrive2 认证失败：{token_resp.errorMessage or '未知错误'}",
                )

            metadata = [("authorization", f"Bearer {token_resp.token}")]
            add_req = clouddrive_pb2.AddOfflineFileRequest(
                urls="\n".join(links),
                toFolder=(target_path or "/"),
                checkFolderAfterSecs=self._check_after_secs,
            )
            add_resp = stub.AddOfflineFiles(add_req, metadata=metadata, timeout=self._timeout)
            if bool(add_resp.success):
                return OfflineAddResult(
                    success=True,
                    adapter="clouddrive2_grpc",
                    total=len(links),
                    target_path=(target_path or "/"),
                    message="CloudDrive2 离线任务提交成功",
                )
            return OfflineAddResult(
                success=False,
                adapter="clouddrive2_grpc",
                total=len(links),
                target_path=(target_path or "/"),
                message=f"CloudDrive2 提交失败：{add_resp.errorMessage or '未知错误'}",
            )
        except Exception as err:
            logger.error("CloudDrive2 gRPC 兜底离线任务提交异常: %s", err, exc_info=True)
            return OfflineAddResult(
                success=False,
                adapter="clouddrive2_grpc",
                total=len(links),
                target_path=(target_path or "/"),
                message=f"CloudDrive2 调用异常：{err}",
            )
        finally:
            channel.close()

    def _browse_dir_via_grpc_fallback(self, normalized_path: str) -> BrowseDirResult:
        try:
            import grpc
            from . import clouddrive_pb2
            from . import clouddrive_pb2_grpc
        except Exception as err:
            return BrowseDirResult(
                success=False,
                adapter="clouddrive2_grpc",
                path=normalized_path,
                items=[],
                message=f"CloudDrive2 依赖未就绪：{err}",
            )

        address = f"{self._host}:{self._port}"
        channel = grpc.insecure_channel(address)
        try:
            stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(channel)
            token_req = clouddrive_pb2.GetTokenRequest(
                userName=self._username,
                password=self._password,
            )
            token_resp = stub.GetToken(token_req, timeout=self._timeout)
            if not token_resp.success or not token_resp.token:
                return BrowseDirResult(
                    success=False,
                    adapter="clouddrive2_grpc",
                    path=normalized_path,
                    items=[],
                    message=f"CloudDrive2 认证失败：{token_resp.errorMessage or '未知错误'}",
                )

            metadata = [("authorization", f"Bearer {token_resp.token}")]
            req = clouddrive_pb2.ListSubFileRequest(path=normalized_path, forceRefresh=False)
            replies = stub.GetSubFiles(req, metadata=metadata, timeout=self._timeout)

            items: List[BrowseDirItem] = []
            for reply in replies:
                for sub in getattr(reply, "subFiles", []):
                    is_dir = bool(getattr(sub, "isDirectory", False))
                    if not is_dir:
                        try:
                            is_dir = int(getattr(sub, "fileType", 1)) == 0
                        except Exception:
                            is_dir = False
                    if not is_dir:
                        continue

                    sub_path = str(getattr(sub, "fullPathName", "") or "").strip()
                    sub_name = str(getattr(sub, "name", "") or "").strip()
                    if not sub_path and not sub_name:
                        continue

                    items.append(
                        BrowseDirItem(
                            name=sub_name or sub_path.rstrip("/").split("/")[-1] or "/",
                            path=sub_path or sub_name,
                            is_dir=True,
                        )
                    )

            items = sorted(items, key=lambda x: x.path or x.name)
            return BrowseDirResult(
                success=True,
                adapter="clouddrive2_grpc",
                path=normalized_path,
                items=items,
                message="ok",
            )
        except Exception as err:
            logger.error("CloudDrive2 gRPC 兜底浏览目录异常: %s", err, exc_info=True)
            return BrowseDirResult(
                success=False,
                adapter="clouddrive2_grpc",
                path=normalized_path,
                items=[],
                message=f"CloudDrive2 调用异常：{err}",
            )
        finally:
            channel.close()

    def add_links(self, links: List[str], target_path: Optional[str] = None) -> OfflineAddResult:
        if not links:
            return OfflineAddResult(
                success=False,
                adapter="clouddrive2_grpc",
                total=0,
                target_path=target_path,
                message="未提供可用链接",
            )

        if not self._username or not self._password:
            return OfflineAddResult(
                success=False,
                adapter="clouddrive2_grpc",
                total=len(links),
                target_path=target_path,
                message="CloudDrive2 用户名或密码未配置",
            )

        # 优先使用 clouddrive2-client，避免 protobuf gencode/runtime 直接冲突。
        client_result = self._add_links_via_client(links=links, target_path=target_path)
        if client_result is not None:
            return client_result

        logger.warning("CloudDrive2 客户端不可用，回退 gRPC 直连模式")
        return self._add_links_via_grpc_fallback(links=links, target_path=target_path)

    def browse_dir(self, path: str = "/") -> BrowseDirResult:
        normalized_path = (path or "/").strip() or "/"
        if not normalized_path.startswith("/"):
            normalized_path = "/" + normalized_path
        if len(normalized_path) > 1:
            normalized_path = normalized_path.rstrip("/") or "/"

        if not self._username or not self._password:
            return BrowseDirResult(
                success=False,
                adapter="clouddrive2_grpc",
                path=normalized_path,
                items=[],
                message="CloudDrive2 用户名或密码未配置",
            )

        # 优先使用 clouddrive2-client，避免 protobuf gencode/runtime 直接冲突。
        client_result = self._browse_dir_via_client(normalized_path=normalized_path)
        if client_result is not None:
            return client_result

        logger.warning("CloudDrive2 客户端不可用，回退 gRPC 直连模式")
        return self._browse_dir_via_grpc_fallback(normalized_path=normalized_path)
