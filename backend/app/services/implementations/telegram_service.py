"""
Telegram Notification Service Implementation
Provides real-time notifications for Uncle Stock Portfolio System pipeline execution
Following Interface-First Design for external messaging service integration
"""

import os
import re
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

from ..interfaces import ITelegramService
from ...core.exceptions import BaseServiceError


class TelegramServiceError(BaseServiceError):
    """Telegram service specific error"""
    pass


class TelegramService(ITelegramService):
    """
    Telegram notification service implementation

    Provides comprehensive notifications for:
    - Pipeline execution lifecycle (start/complete)
    - Individual step execution (start/complete with timing)
    - Daily portfolio summaries
    - Error alerts and system notifications

    Configuration via environment variables:
    - TELEGRAM_BOT_TOKEN: Bot token from @BotFather
    - TELEGRAM_CHAT_ID: Target chat/user ID for notifications
    - TELEGRAM_TIMEOUT: Request timeout in seconds (default: 10)
    - TELEGRAM_ENABLED: Enable/disable notifications (default: true)
    """

    def __init__(self):
        """Initialize Telegram service with environment configuration"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.timeout = int(os.getenv('TELEGRAM_TIMEOUT', '10'))
        self.enabled = os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true'

        # Service state tracking
        self.message_count = 0
        self.last_message_sent = None
        self.session = None

        # Configure logging
        self.logger = logging.getLogger(__name__)

        # Validate configuration
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate Telegram service configuration"""
        if not self.enabled:
            self.logger.info("Telegram notifications disabled via TELEGRAM_ENABLED=false")
            return

        if not self.bot_token:
            raise TelegramServiceError("TELEGRAM_BOT_TOKEN environment variable not set", "TELEGRAM_CONFIG_ERROR")

        if not self.chat_id:
            raise TelegramServiceError("TELEGRAM_CHAT_ID environment variable not set", "TELEGRAM_CONFIG_ERROR")

        # Validate bot token format (basic check)
        if not re.match(r'^\d+:[A-Za-z0-9_-]{35}$', self.bot_token):
            raise TelegramServiceError("TELEGRAM_BOT_TOKEN format appears invalid", "TELEGRAM_CONFIG_ERROR")

        self.logger.info(f"Telegram service configured for chat ID: {self.chat_id}")

    @property
    def base_url(self) -> str:
        """Get Telegram Bot API base URL"""
        return f"https://api.telegram.org/bot{self.bot_token}"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def _close_session(self) -> None:
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def send_message(
        self,
        message: str,
        parse_mode: str = "Markdown",
        disable_notification: bool = False
    ) -> bool:
        """
        Send a message to the configured Telegram chat

        Args:
            message: Text message to send (supports Markdown formatting)
            parse_mode: Message formatting mode (Markdown, HTML, or None)
            disable_notification: Send message silently without notification

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.enabled:
            self.logger.debug("Telegram notifications disabled, skipping message")
            return True

        try:
            session = await self._get_session()

            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'disable_notification': disable_notification
            }

            # Add parse_mode if specified
            if parse_mode and parse_mode.lower() != 'none':
                payload['parse_mode'] = parse_mode

            url = f"{self.base_url}/sendMessage"

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    self.message_count += 1
                    self.last_message_sent = datetime.now(timezone.utc)
                    self.logger.debug(f"Telegram message sent successfully (#{self.message_count})")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Telegram API error {response.status}: {error_text}")
                    return False

        except asyncio.TimeoutError:
            self.logger.error("Telegram API request timeout")
            return False
        except Exception as e:
            self.logger.error(f"Telegram service error: {e}")
            return False

    async def notify_step_start(
        self,
        step_number: int,
        step_name: str,
        execution_id: str
    ) -> bool:
        """Send notification when pipeline step starts execution"""
        time_str = datetime.now().strftime('%H:%M:%S CET')

        message = f"""🚀 *Step {step_number} Started*
📋 {step_name}
⏰ {time_str}
🆔 `{execution_id[:8]}...`"""

        return await self.send_message(message)

    async def notify_step_complete(
        self,
        step_number: int,
        step_name: str,
        execution_id: str,
        success: bool,
        execution_time: float,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification when pipeline step completes"""
        status_emoji = "✅" if success else "❌"
        status_text = "SUCCESS" if success else "FAILED"
        time_str = datetime.now().strftime('%H:%M:%S CET')

        message = f"""{status_emoji} *Step {step_number} {status_text}*
📋 {step_name}
⏱️ Duration: {execution_time:.2f}s
⏰ {time_str}
🆔 `{execution_id[:8]}...`"""

        # Add additional details if provided
        if details:
            if success:
                if 'created_files' in details and details['created_files']:
                    file_count = len(details['created_files'])
                    message += f"\n📁 Files created: {file_count}"

                if 'processed_items' in details:
                    message += f"\n📊 Processed: {details['processed_items']}"

                if 'total_stocks' in details:
                    message += f"\n🏢 Stocks: {details['total_stocks']}"

                if 'success_rate' in details:
                    rate = details['success_rate'] * 100
                    message += f"\n📈 Success rate: {rate:.1f}%"
            else:
                # Add error details for failed steps
                if 'error_message' in details:
                    error_msg = details['error_message']
                    # Truncate long error messages
                    if len(error_msg) > 100:
                        error_msg = error_msg[:97] + "..."
                    message += f"\n⚠️ Error: `{error_msg}`"

        return await self.send_message(message)

    async def notify_pipeline_start(
        self,
        pipeline_type: str,
        target_steps: List[int],
        execution_id: str
    ) -> bool:
        """Send notification when pipeline execution begins"""
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S CET')

        # Determine pipeline emoji and description
        if pipeline_type.lower() == 'monthly':
            emoji = "🌕"
            description = "Monthly Full Pipeline"
        elif pipeline_type.lower() == 'daily':
            emoji = "📅"
            description = "Daily Pipeline"
        else:
            emoji = "⚙️"
            description = f"{pipeline_type.title()} Pipeline"

        step_range = f"{min(target_steps)}-{max(target_steps)}" if len(target_steps) > 1 else str(target_steps[0])

        message = f"""{emoji} *{description} Started*
📅 {time_str}
🔧 Steps: {len(target_steps)} ({step_range})
🆔 `{execution_id[:8]}...`"""

        # Add special note for monthly pipeline
        if pipeline_type.lower() == 'monthly':
            message += "\n🔄 *Fresh data fetch included*"

        return await self.send_message(message)

    async def notify_pipeline_complete(
        self,
        pipeline_type: str,
        execution_id: str,
        success: bool,
        completed_steps: List[int],
        failed_step: Optional[int],
        execution_time: float,
        summary_stats: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification when pipeline execution completes"""
        status_emoji = "🎉" if success else "💥"
        status_text = "COMPLETED" if success else "FAILED"
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S CET')

        # Format execution time
        if execution_time < 60:
            time_display = f"{execution_time:.1f}s"
        elif execution_time < 3600:
            minutes = int(execution_time // 60)
            seconds = int(execution_time % 60)
            time_display = f"{minutes}m {seconds}s"
        else:
            hours = int(execution_time // 3600)
            minutes = int((execution_time % 3600) // 60)
            time_display = f"{hours}h {minutes}m"

        message = f"""{status_emoji} *{pipeline_type.title()} Pipeline {status_text}*
⏱️ Total Time: {time_display}
✅ Completed Steps: {len(completed_steps)}
📅 {time_str}
🆔 `{execution_id[:8]}...`"""

        if failed_step:
            message += f"\n❌ Failed at Step: {failed_step}"

        # Add summary statistics if provided
        if summary_stats:
            if 'total_orders' in summary_stats and summary_stats['total_orders'] > 0:
                message += f"\n💼 Orders: {summary_stats['total_orders']}"

            if 'portfolio_value' in summary_stats:
                value = summary_stats['portfolio_value']
                message += f"\n💰 Portfolio: €{value:,.0f}"

        return await self.send_message(message)

    async def send_daily_summary(
        self,
        portfolio_value: float,
        active_positions: int,
        orders_executed: int,
        performance_change: Optional[float] = None
    ) -> bool:
        """Send daily portfolio performance summary"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        time_str = datetime.now().strftime('%H:%M CET')

        message = f"""📊 *Daily Portfolio Summary*
📅 {date_str} at {time_str}

💰 Portfolio Value: €{portfolio_value:,.2f}
📈 Active Positions: {active_positions}
🔄 Orders Executed: {orders_executed}"""

        # Add performance change if provided
        if performance_change is not None:
            change_emoji = "📈" if performance_change >= 0 else "📉"
            change_sign = "+" if performance_change > 0 else ""
            message += f"\n{change_emoji} Daily Change: {change_sign}{performance_change:.2f}%"

        return await self.send_message(message)

    async def send_error_alert(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send critical error alert notification"""
        time_str = datetime.now().strftime('%H:%M:%S CET')

        message = f"""🚨 *System Alert*
⚠️ Error Type: {error_type}
⏰ {time_str}

📝 Message: `{error_message[:200]}...` if len(error_message) > 200 else `{error_message}`"""

        # Add context information if provided
        if context:
            if 'step_number' in context:
                message += f"\n🔧 Step: {context['step_number']}"

            if 'service' in context:
                message += f"\n⚙️ Service: {context['service']}"

            if 'execution_id' in context:
                message += f"\n🆔 Execution: `{context['execution_id'][:8]}...`"

        return await self.send_message(message, disable_notification=False)

    def get_service_status(self) -> Dict[str, Any]:
        """Get current Telegram service configuration and status"""
        bot_token_valid = bool(
            self.bot_token and
            re.match(r'^\d+:[A-Za-z0-9_-]{35}$', self.bot_token)
        )

        return {
            "configured": bool(self.bot_token and self.chat_id),
            "enabled": self.enabled,
            "bot_token_valid": bot_token_valid,
            "chat_id_configured": bool(self.chat_id),
            "last_message_sent": self.last_message_sent.isoformat() if self.last_message_sent else None,
            "message_count": self.message_count,
            "timeout_seconds": self.timeout,
            "session_active": bool(self.session and not self.session.closed)
        }

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Telegram bot connection and configuration

        Returns:
            Dict with test results including bot info and connectivity status
        """
        if not self.enabled:
            return {
                "success": True,
                "message": "Telegram notifications disabled",
                "bot_info": None
            }

        try:
            session = await self._get_session()

            # Test bot token by getting bot info
            url = f"{self.base_url}/getMe"
            async with session.get(url) as response:
                if response.status == 200:
                    bot_data = await response.json()

                    # Send test message
                    test_message = f"""🔧 *Connection Test*
✅ Bot: {bot_data['result']['first_name']}
⏰ {datetime.now().strftime('%H:%M:%S CET')}
🚀 Uncle Stock Portfolio System ready!"""

                    message_sent = await self.send_message(test_message)

                    return {
                        "success": True,
                        "message": "Connection test successful",
                        "bot_info": bot_data['result'],
                        "test_message_sent": message_sent
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "message": f"Bot API error: {error_text}",
                        "bot_info": None
                    }

        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "bot_info": None
            }

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup session"""
        await self._close_session()

    def __del__(self):
        """Cleanup on object deletion"""
        if self.session and not self.session.closed:
            # Cannot await in __del__, log warning
            self.logger.warning("TelegramService session not properly closed")