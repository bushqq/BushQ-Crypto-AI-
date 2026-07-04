"""Enterprise WeChat notification module."""

import logging
from typing import List, Optional

import requests

logger = logging.getLogger("cic.notifier.wechat")


class WeChatWorkNotifier:
    """Enterprise WeChat bot notifier."""

    # Enterprise WeChat markdown limit is about 4096 UTF-8 bytes.
    # Keep a conservative margin for Chinese text and server-side validation.
    MAX_CONTENT_BYTES = 3000

    def __init__(self, webhook_url: str = "", msg_type: str = "markdown"):
        self._webhook_url = webhook_url
        self._msg_type = msg_type  # text / markdown
        self._summary_only = True

    def initialize(self, config: any) -> None:
        self._webhook_url = config.get("notification.webhook_url", "")
        self._msg_type = config.get("notification.msg_type", "markdown")
        self._summary_only = config.get("notification.summary_only", True)
        if not self._webhook_url:
            logger.warning("[WeChatWork] Webhook URL is not configured; push is disabled")
        else:
            logger.info("[WeChatWork] initialized (summary_only=%s)", self._summary_only)

    @staticmethod
    def _byte_len(s: str) -> int:
        return len(s.encode("utf-8"))

    def send(self, content: str) -> bool:
        if not self._webhook_url:
            logger.error("[WeChatWork] Webhook URL is not configured")
            return False

        chunks = self._split_message(content)
        logger.info(
            "[WeChatWork] split into %d chunks, bytes=%s",
            len(chunks),
            [self._byte_len(c) for c in chunks],
        )
        all_success = True

        for i, chunk in enumerate(chunks):
            success = self._send_single(chunk)
            if not success:
                all_success = False
                logger.error("[WeChatWork] chunk %d send failed", i + 1)
            else:
                logger.info("[WeChatWork] chunk %d/%d sent", i + 1, len(chunks))

        return all_success

    def _send_single(self, content: str) -> bool:
        if self._byte_len(content) > self.MAX_CONTENT_BYTES:
            suffix = "\n\n...(已截断)"
            content = self._truncate_bytes(
                content,
                self.MAX_CONTENT_BYTES - self._byte_len(suffix),
            ) + suffix

        if self._msg_type == "markdown":
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": content},
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {"content": content},
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

            logger.error(
                "[WeChatWork] push failed: errcode=%s, errmsg=%s",
                result.get("errcode"),
                result.get("errmsg"),
            )
            return False

        except Exception as e:
            logger.error("[WeChatWork] push exception: %s", e)
            return False

    def _split_message(self, content: str) -> List[str]:
        if self._byte_len(content) <= self.MAX_CONTENT_BYTES:
            return [content]

        prefix_reserve = 64
        chunk_limit = self.MAX_CONTENT_BYTES - prefix_reserve
        chunks: List[str] = []
        current_lines: List[str] = []
        current_bytes = 0

        for line in content.split("\n"):
            for part in self._split_text_by_bytes(line, chunk_limit):
                part_bytes = self._byte_len(part)
                separator_bytes = 1 if current_lines else 0
                new_bytes = current_bytes + separator_bytes + part_bytes

                if new_bytes > chunk_limit and current_lines:
                    chunks.append("\n".join(current_lines).strip())
                    current_lines = [part]
                    current_bytes = part_bytes
                else:
                    current_lines.append(part)
                    current_bytes = new_bytes

        if current_lines:
            chunk = "\n".join(current_lines).strip()
            if chunk:
                chunks.append(chunk)

        if len(chunks) > 1:
            total = len(chunks)
            prefixed_chunks: List[str] = []
            for i, chunk in enumerate(chunks):
                prefix = f"**({i + 1}/{total})**\n\n"
                limit = self.MAX_CONTENT_BYTES - self._byte_len(prefix)
                for part in self._split_text_by_bytes(chunk, limit):
                    prefixed_chunks.append(prefix + part)
            chunks = prefixed_chunks

        return chunks

    @staticmethod
    def _truncate_bytes(content: str, max_bytes: int) -> str:
        if max_bytes <= 0:
            return ""
        encoded = content.encode("utf-8")
        if len(encoded) <= max_bytes:
            return content

        while max_bytes > 0:
            try:
                return encoded[:max_bytes].decode("utf-8")
            except UnicodeDecodeError:
                max_bytes -= 1
        return ""

    @classmethod
    def _split_text_by_bytes(cls, content: str, max_bytes: int) -> List[str]:
        if cls._byte_len(content) <= max_bytes:
            return [content]

        parts: List[str] = []
        remaining = content
        while remaining:
            part = cls._truncate_bytes(remaining, max_bytes)
            if not part:
                break
            parts.append(part)
            remaining = remaining[len(part):]
        return parts

    def send_report(
        self,
        report_markdown: str,
        report_brief: str = "",
        summary_only: Optional[bool] = None,
    ) -> bool:
        use_summary_only = self._summary_only if summary_only is None else summary_only
        if use_summary_only:
            content = report_brief or report_markdown
            logger.info(
                "[WeChatWork] summary_only=true, sending brief only, bytes=%d",
                self._byte_len(content),
            )
            return self._send_single(content)

        all_ok = True
        if report_brief:
            brief_ok = self._send_single(report_brief)
            if not brief_ok:
                logger.warning("[WeChatWork] brief send failed")
                all_ok = False

        full_ok = self.send(report_markdown)
        if not full_ok:
            all_ok = False

        return all_ok
