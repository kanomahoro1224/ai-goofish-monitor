"""
OneBot V11 QQ 群通知客户端
通过 OneBot V11 HTTP API 向 QQ 群发送商品推荐通知（文字 + 图片）。
"""
import asyncio
from typing import Dict, Optional

import httpx

from .base import NotificationClient


class OneBotQQClient(NotificationClient):
    """QQ 群通知客户端 (OneBot V11)"""

    channel_key = "onebot_qq"
    display_name = "QQ群推送"

    def __init__(
        self,
        http_url: Optional[str] = None,
        group_id: Optional[str] = None,
        pcurl_to_mobile: bool = True,
    ):
        super().__init__(
            enabled=bool(http_url and group_id),
            pcurl_to_mobile=pcurl_to_mobile,
        )
        self.http_url = (http_url or "").rstrip("/")
        self.group_id = group_id

    async def send(self, product_data: Dict, reason: str) -> None:
        """发送 QQ 群通知：新商品：标题 - 价格CNY + 图片"""
        if not self.is_enabled():
            raise RuntimeError("QQ群推送 未启用")

        message = self._build_message(product_data, reason)

        # 构建 OneBot V11 消息段数组
        segments = []

        # 文本部分：新商品：标题 - 价格CNY
        text_content = f"新商品：{message.title} - {message.price}CNY"
        if message.reason:
            text_content += f"\n原因：{message.reason}"
        if message.mobile_link:
            text_content += f"\n📱 {message.mobile_link}"
        else:
            text_content += f"\n🔗 {message.desktop_link}"
        segments.append({"type": "text", "data": {"text": text_content}})

        # 图片部分
        if message.image_url:
            segments.append({"type": "image", "data": {"file": message.image_url}})

        payload = {
            "group_id": int(self.group_id),
            "message": segments,
        }

        async with httpx.AsyncClient() as client:
            url = f"{self.http_url}/send_group_msg"
            response = await client.post(url, json=payload, timeout=20)
            response.raise_for_status()
            result = response.json()
            if result.get("status") != "ok" and result.get("retcode") != 0:
                raise RuntimeError(
                    f"QQ群消息发送失败: {result.get('message', result.get('wording', '未知错误'))}"
                )
