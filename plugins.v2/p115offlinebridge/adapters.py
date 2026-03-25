from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import List, Literal, Optional

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


class P115StrmHelperAdapter:
    """
    通过 MoviePilot 插件 API 调用 P115StrmHelper 现有离线下载能力。
    """

    def __init__(self, moviepilot_url: str, api_token: str, timeout: int = 20):
        self._moviepilot_url = (moviepilot_url or "").rstrip("/")
        self._api_token = api_token or ""
        self._timeout = timeout

    def add_links(self, links: List[str], target_path: Optional[str] = None) -> OfflineAddResult:
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

        url = f"{self._moviepilot_url}/api/v1/plugin/P115StrmHelper/add_offline_task"
        payload = {"links": links}
        if target_path:
            payload["path"] = target_path

        try:
            response = RequestUtils(
                content_type="application/json",
                timeout=self._timeout,
            ).post_res(
                url=url,
                params={"apikey": self._api_token},
                json=payload,
            )
            if not response:
                return OfflineAddResult(
                    success=False,
                    adapter="p115_strmhelper",
                    total=len(links),
                    target_path=target_path,
                    message="调用 P115StrmHelper API 失败：无响应",
                )

            body = None
            try:
                body = response.json()
            except Exception:
                try:
                    body = json.loads(response.text)
                except Exception:
                    body = None

            if response.status_code >= 400:
                err_msg = None
                if isinstance(body, dict):
                    err_msg = body.get("msg") or body.get("message")
                err_msg = err_msg or f"HTTP {response.status_code}"
                return OfflineAddResult(
                    success=False,
                    adapter="p115_strmhelper",
                    total=len(links),
                    target_path=target_path,
                    message=f"调用失败：{err_msg}",
                )

            if not isinstance(body, dict):
                return OfflineAddResult(
                    success=False,
                    adapter="p115_strmhelper",
                    total=len(links),
                    target_path=target_path,
                    message="调用失败：响应不是有效 JSON",
                )

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

        url = f"{self._moviepilot_url}/api/v1/plugin/P115StrmHelper/add_transfer_share"
        success_count = 0
        failed_count = 0
        fail_messages: List[str] = []

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
                    fail_messages.append("无响应")
                    continue

                body = None
                try:
                    body = response.json()
                except Exception:
                    try:
                        body = json.loads(response.text)
                    except Exception:
                        body = None

                if response.status_code >= 400:
                    failed_count += 1
                    if isinstance(body, dict):
                        fail_messages.append(
                            str(body.get("msg") or body.get("message") or response.status_code)
                        )
                    else:
                        fail_messages.append(str(response.status_code))
                    continue

                if isinstance(body, dict):
                    code = int(body.get("code", 0))
                    if code == 0:
                        success_count += 1
                    else:
                        failed_count += 1
                        fail_messages.append(str(body.get("msg") or "转存失败"))
                else:
                    failed_count += 1
                    fail_messages.append("响应不是有效 JSON")
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
