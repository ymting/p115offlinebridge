from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, List, Literal, Optional

from app.core.config import settings
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

    def _candidate_moviepilot_urls(self) -> List[str]:
        candidates: List[str] = []

        configured = (self._moviepilot_url or "").strip().rstrip("/")
        if configured:
            candidates.append(configured)

        fallback_ports = []
        try:
            fallback_ports.append(int(getattr(settings, "NGINX_PORT", 3000)))
        except Exception:
            fallback_ports.append(3000)
        try:
            fallback_ports.append(int(getattr(settings, "PORT", 3001)))
        except Exception:
            fallback_ports.append(3001)

        for port in fallback_ports:
            for host in ("127.0.0.1", "localhost"):
                fallback = f"http://{host}:{port}"
                if fallback not in candidates:
                    candidates.append(fallback)

        return candidates

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
        if not links:
            return OfflineAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=0,
                target_path=target_path,
                message="未提供可用链接",
            )

        if not self._candidate_moviepilot_urls():
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
        if target_path:
            payload["path"] = target_path

        try:
            last_http_message = ""
            attempt_bases = self._candidate_moviepilot_urls()
            for base_url in attempt_bases:
                url = f"{base_url}/api/v1/plugin/P115StrmHelper/add_offline_task"
                response = RequestUtils(
                    content_type="application/json",
                    timeout=self._timeout,
                ).post_res(
                    url=url,
                    params={"apikey": self._api_token},
                    json=payload,
                )
                if not response:
                    logger.warning("P115StrmHelper 离线提交无响应：%s", url)
                    continue

                body = self._load_json_body(response)
                if response.status_code >= 400:
                    err_msg = None
                    if isinstance(body, dict):
                        err_msg = body.get("msg") or body.get("message")
                    err_msg = err_msg or f"HTTP {response.status_code}"
                    last_http_message = f"{base_url}: {err_msg}"
                    logger.warning("P115StrmHelper 离线提交失败：%s", last_http_message)
                    continue

                if not body:
                    last_http_message = f"{base_url}: 响应不是有效 JSON"
                    logger.warning("P115StrmHelper 离线提交失败：%s", last_http_message)
                    continue

                code = int(body.get("code", 0))
                msg = str(body.get("msg") or "")
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

            fail_reason = last_http_message or f"无响应（尝试地址: {', '.join(attempt_bases)}）"
            return OfflineAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=len(links),
                target_path=target_path,
                message=f"调用 P115StrmHelper API 失败：{fail_reason}",
            )
        except Exception as err:
            logger.error("调用 P115StrmHelper API 异常: %s", err, exc_info=True)
            return OfflineAddResult(
                success=False,
                adapter="p115_strmhelper",
                total=len(links),
                target_path=target_path,
                message=f"调用异常：{err}",
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

        if not self._candidate_moviepilot_urls():
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

        for share_url in share_urls:
            try:
                call_ok = False
                for base_url in self._candidate_moviepilot_urls():
                    url = f"{base_url}/api/v1/plugin/P115StrmHelper/add_transfer_share"
                    response = RequestUtils(
                        content_type="application/json",
                        timeout=self._timeout,
                    ).get_res(
                        url=url,
                        params={"apikey": self._api_token, "share_url": share_url},
                    )
                    if not response:
                        logger.warning("P115StrmHelper 分享转存无响应：%s", url)
                        continue

                    body = self._load_json_body(response)
                    if response.status_code >= 400:
                        if isinstance(body, dict):
                            fail_messages.append(
                                str(body.get("msg") or body.get("message") or response.status_code)
                            )
                        else:
                            fail_messages.append(f"{base_url}: {response.status_code}")
                        continue

                    if body:
                        code = int(body.get("code", 0))
                        if code == 0:
                            success_count += 1
                        else:
                            failed_count += 1
                            fail_messages.append(str(body.get("msg") or "转存失败"))
                        call_ok = True
                        break

                    fail_messages.append(f"{base_url}: 响应不是有效 JSON")

                if not call_ok:
                    failed_count += 1
            except Exception as err:
                failed_count += 1
                fail_messages.append(str(err))
                logger.error("调用分享转存 API 异常: %s", err, exc_info=True)

        total = len(share_urls)
        ok = failed_count == 0
        if ok:
            message = f"分享转存任务提交成功（{success_count}/{total}）"
        else:
            first_fail = fail_messages[0] if fail_messages else "未知错误"
            message = f"分享转存部分/全部失败（成功 {success_count}，失败 {failed_count}）：{first_fail}"

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

        if not self._candidate_moviepilot_urls():
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
            last_http_message = ""
            attempt_bases = self._candidate_moviepilot_urls()
            for base_url in attempt_bases:
                url = f"{base_url}/api/v1/plugin/P115StrmHelper/browse_dir"
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
                    logger.warning("P115StrmHelper 浏览目录无响应：%s", url)
                    continue

                body = self._load_json_body(response)
                if response.status_code >= 400:
                    err_msg = None
                    if body:
                        err_msg = body.get("msg") or body.get("message")
                    err_msg = err_msg or f"HTTP {response.status_code}"
                    last_http_message = f"{base_url}: {err_msg}"
                    logger.warning("P115StrmHelper 浏览目录失败：%s", last_http_message)
                    continue

                if not body:
                    last_http_message = f"{base_url}: 响应不是有效 JSON"
                    logger.warning("P115StrmHelper 浏览目录失败：%s", last_http_message)
                    continue

                code = int(body.get("code", 0))
                if code != 0:
                    last_http_message = f"{base_url}: {body.get('msg') or '浏览目录失败'}"
                    logger.warning("P115StrmHelper 浏览目录失败：%s", last_http_message)
                    continue

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

            fail_reason = last_http_message or f"无响应（尝试地址: {', '.join(attempt_bases)}）"
            return BrowseDirResult(
                success=False,
                adapter="p115_strmhelper",
                path=normalized_path,
                items=[],
                message=f"调用 P115StrmHelper 浏览目录 API 失败：{fail_reason}",
            )
        except Exception as err:
            logger.error("调用 P115StrmHelper 浏览目录 API 异常: %s", err, exc_info=True)
            return BrowseDirResult(
                success=False,
                adapter="p115_strmhelper",
                path=normalized_path,
                items=[],
                message=f"调用异常：{err}",
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
            add_resp = stub.AddOfflineFiles(
                add_req,
                metadata=metadata,
                timeout=self._timeout,
            )

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
            logger.error("CloudDrive2 离线任务提交异常: %s", err, exc_info=True)
            return OfflineAddResult(
                success=False,
                adapter="clouddrive2_grpc",
                total=len(links),
                target_path=(target_path or "/"),
                message=f"CloudDrive2 调用异常：{err}",
            )
        finally:
            channel.close()
