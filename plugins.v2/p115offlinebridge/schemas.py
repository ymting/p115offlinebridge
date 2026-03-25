from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class OfflineSubmitPayload(BaseModel):
    """
    提交离线下载任务的 API 请求体。
    """

    links: Optional[List[str]] = Field(default=None, description="链接数组")
    link_text: Optional[str] = Field(default=None, description="多链接文本（换行/逗号分隔）")
    path: Optional[str] = Field(default=None, description="目标目录")
    adapter: Optional[str] = Field(default=None, description="接口对象：p115_strmhelper/clouddrive2_grpc")
    notify: Optional[bool] = Field(default=None, description="是否发送系统通知")


class OfflineSubmitResult(BaseModel):
    success: bool = Field(..., description="是否成功")
    adapter: str = Field(..., description="实际使用的接口对象")
    total: int = Field(..., description="任务数量")
    target_path: Optional[str] = Field(default=None, description="目标路径")
    message: str = Field(..., description="结果消息")
