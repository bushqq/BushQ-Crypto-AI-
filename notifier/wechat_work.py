"""企业微信推送模块"""

import json
import logging
from typing import List, Optional

import requests

logger = logging.getLogger("cic.notifier.wechat")


class WeChatWorkNotifier:
    """企业微信群机器人推送"""

    # 企业微信 Markdown 单条限制约 4096 字节（UTF-8）。
    # 中文、Markdown 与服务端校验会放大长度，保守留余量。
    MAX_CONTENT_BYTES = 3000

    def __init__(self, webhook_url: str = "", msg_type: str = "markdown"):
        self._webhook_url = webhook_url
        self._msg_type = msg_type  # text / markdown
        self._summary_only = True

    def initialize(self, config: any) -> None:
        """从配置初始化"""
        self._webhook_url = config.get("notification.webhook_url", "")
        self._msg_type = config.get("notification.msg_type", "markdown")
        self._summary_only = config.get("notification.summary_only", True)
        if not self._webhook_url:
            logger.warning("[WeChatWork] Webhook URL 未配置，推送不可用")
        else:
            logger.info("[WeChatWork] 初始化成功 (summary_only=%s)", self._summary_only)

    @staticmethod
    def _byte_len(s: str) -> int:
        """计算字符串的 UTF-8 字节长度"""
        return len(s.encode("utf-8"))

    def send(self, content: str) -> bool:
        """
        发送消息，自动处理长消息拆分。
        返回是否全部发送成功。
        """
        if not self._webhook_url:
            logger.error("[WeChatWork] Webhook URL 未配置")
            return False

        # 拆分长消息
        chunks = self._split_message(content)
        logger.info("[WeChatWork] 拆分为 %d 段, 字节: %s", len(chunks),
                     [self._byte_len(c) for c in chunks])
        all_success = True

        for i, chunk in enumerate(chunks):
            success = self._send_single(chunk)
            if not success:
                all_success = False
                logger.error("[WeChatWork] 第%d段发送失败", i + 1)
            else:
                logger.info("[WeChatWork] 第%d/%d段发送成功", i + 1, len(chunks))

        return all_success

    def _send_single(self, content: str) -> bool:
        """发送单条消息"""
        # 最终保底：超长则按字节截断
        if self._byte_len(content) > self.MAX_CONTENT_BYTES:
            suffix = "\n\n...(已截断)"
            content = self._truncate_bytes(content, self.MAX_CONTENT_BYTES - self._byte_len(suffix)) + suffix

        if self._msg_type == "markdown":
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content,
                },
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": content,
                },
            }

        try:
            resp = requests.post(
                self._webhook_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"},
            )
            result = resp.json()

            if result.get("errcode") == 0:
                return True
            else:
                logger.error("[WeChatWork] 推送失败: errcode=%d, errmsg=%s",
                             result.get("errcode"), result.get("errmsg"))
                return False

        except Exception as e:
            logger.error("[WeChatWork] 推送异常: %s", e)
            return False

    def _split_message(self, content: str) -> List[str]:
        """
        按段落拆分长消息，确保每段不超过字节限制。
        企业微信 Markdown 单条限制 4096 字节（UTF-8）。
        """
        if self._byte_len(content) <= self.MAX_CONTENT_BYTES:
            return [content]

        chunks = []
        lines = content.split("\n")
        current_chunk = ""

        for line in lines:
            line_bytes = self._byte_len(line)

            # 单行超长则按字节截断
            if line_bytes > self.MAX_CONTENT_BYTES - 200:
                line = self._truncate_bytes(line, self.MAX_CONTENT_BYTES - 240) + "..."

            new_bytes = self._byte_len(current_chunk) + line_bytes + 1  # +1 for \n

            if new_bytes > self.MAX_CONTENT_BYTES:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # 每段加上序号
        if len(chunks) > 1:
            for i in range(len(chunks)):
                prefix = f"**({i+1}/{len(chunks)})**\n\n"
                chunks[i] = prefix + chunks[i]
                # 最终校验：如果加上前缀还是超了，按字节强制截断
                if self._byte_len(chunks[i]) > self.MAX_CONTENT_BYTES:
                    chunks[i] = self._truncate_bytes(chunks[i], self.MAX_CONTENT_BYTES - self._byte_len("...\n")) + "...\n"

        return chunks

    @staticmethod
    def _truncate_bytes(content: str, max_bytes: int) -> str:
        """按 UTF-8 字节安全截断，不切断多字节字符。"""
        encoded = content.encode("utf-8")
        if len(encoded) <= max_bytes:
            return content
        return encoded[:max_bytes].decode("utf-8", errors="ignore")

    def send_report(self, report_markdown: str, report_brief: str = "", summary_only: Optional[bool] = None) -> bool:
        """发送日报报告"""
        use_summary_only = self._summary_only if summary_only is None else summary_only
        if use_summary_only:
            content = report_brief or report_markdown
            logger.info("[WeChatWork] summary_only=true，仅发送总结，字节: %d", self._byte_len(content))
            return self._send_single(content)

        all_ok = True
        if report_brief:
            brief_ok = self._send_single(report_brief)
            if not brief_ok:
                logger.warning("[WeChatWork] 简要版发送失败")
                all_ok = False

        full_ok = self.send(report_markdown)
        if not full_ok:
            all_ok = False

        return all_ok
