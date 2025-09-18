#!/usr/bin/env python3
"""
Smart Pipeline Scheduler for Uncle Stock Portfolio System
Production-ready scheduler for automated daily and monthly pipeline execution
"""

import os
import sys
import asyncio
import requests
import time
from datetime import datetime, date
from pathlib import Path
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add project to Python path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PipelineScheduler:
    """
    Production scheduler for Uncle Stock Portfolio System

    Handles:
    - Daily pipeline execution (steps 2-11)
    - Monthly pipeline execution (steps 1-11)
    - Error handling and retry logic
    - Telegram notifications integration
    - Status monitoring and logging
    """

    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        """Initialize scheduler with API configuration"""
        self.api_base = f"{api_base_url}/api/v1"
        self.timeout = 30  # API request timeout in seconds
        self.max_retries = 3

        # Validate environment
        self._validate_environment()

        logger.info(f"Scheduler initialized with API base: {self.api_base}")

    def _validate_environment(self) -> None:
        """Validate required environment variables"""
        required_vars = [
            'UNCLE_STOCK_USER_ID',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

    async def _send_telegram_notification(self, message: str) -> bool:
        """Send Telegram notification directly (fallback if API fails)"""
        try:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')

            if not bot_token or not chat_id:
                logger.warning("Telegram credentials not available")
                return False

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }

            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    async def _make_api_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make API request with retry logic"""
        url = f"{self.api_base}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                logger.info(f"API {method} {endpoint} (attempt {attempt + 1})")

                if method.upper() == "POST":
                    response = requests.post(url, json=data, timeout=self.timeout)
                else:
                    response = requests.get(url, timeout=self.timeout)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"API request failed: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"API request error (attempt {attempt + 1}): {e}")

            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        raise Exception(f"Failed to complete API request after {self.max_retries} attempts")

    async def check_api_health(self) -> bool:
        """Check if API is healthy before execution"""
        try:
            health_data = await self._make_api_request("GET", "/pipeline/health")
            is_healthy = health_data.get("status") == "healthy"

            if is_healthy:
                logger.info("API health check passed")
            else:
                logger.error(f"API health check failed: {health_data}")

            return is_healthy

        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False

    async def should_run_monthly_fetch(self) -> bool:
        """Check if we should run Step 1 (monthly data fetch)"""
        today = date.today()
        is_monthly = today.day == 1

        logger.info(f"Monthly check: Today is {today}, is_monthly={is_monthly}")
        return is_monthly

    async def execute_pipeline(self, dry_run: bool = False) -> dict:
        """
        Execute the appropriate pipeline based on date

        Args:
            dry_run: If True, only validate without executing

        Returns:
            dict: Execution result with success status and details
        """
        try:
            # Check API health first
            if not await self.check_api_health():
                raise Exception("API health check failed")

            # Determine execution type
            is_monthly = await self.should_run_monthly_fetch()
            execution_type = "monthly" if is_monthly else "daily"
            execution_id = f"{execution_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            logger.info(f"Starting {execution_type} pipeline execution: {execution_id}")

            # Send start notification
            start_message = f"""
🎯 *{execution_type.title()} Pipeline Started*
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🆔 Execution ID: `{execution_id}`
🔧 Steps: {'1-11 (Full Pipeline)' if is_monthly else '2-11 (Daily Pipeline)'}
"""
            await self._send_telegram_notification(start_message)

            if dry_run:
                logger.info("Dry run mode - skipping actual execution")
                return {
                    "success": True,
                    "execution_id": execution_id,
                    "execution_type": execution_type,
                    "dry_run": True
                }

            # Execute pipeline
            start_time = time.time()

            if is_monthly:
                # Run full pipeline including Step 1
                response_data = await self._make_api_request(
                    "POST",
                    "/pipeline/run",
                    {"execution_id": execution_id}
                )
            else:
                # Run steps 2-11 only (skip expensive Step 1)
                response_data = await self._make_api_request(
                    "POST",
                    "/pipeline/run/steps/2-11",
                    {
                        "execution_id": execution_id,
                        "start_step": 2,
                        "end_step": 11,
                        "started_by": "scheduler"
                    }
                )

            execution_time = time.time() - start_time

            # Wait for completion (for step ranges, they might be async)
            if response_data.get("success") and not response_data.get("completed_steps"):
                logger.info("Pipeline started in background, monitoring status...")
                await self._monitor_execution(execution_id, execution_type)

            # Send completion notification
            success = response_data.get("success", False)
            completed_steps = response_data.get("completed_steps", [])
            failed_step = response_data.get("failed_step")

            status_emoji = "🎉" if success else "💥"
            status_text = "COMPLETED" if success else "FAILED"

            completion_message = f"""
{status_emoji} *{execution_type.title()} Pipeline {status_text}*
⏱️ Execution Time: {execution_time:.1f}s
✅ Completed Steps: {len(completed_steps)}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🆔 Execution ID: `{execution_id}`
"""

            if failed_step:
                completion_message += f"\n❌ Failed at Step: {failed_step}"

            await self._send_telegram_notification(completion_message)

            result = {
                "success": success,
                "execution_id": execution_id,
                "execution_type": execution_type,
                "execution_time": execution_time,
                "completed_steps": completed_steps,
                "failed_step": failed_step,
                "dry_run": False
            }

            logger.info(f"Pipeline execution completed: {result}")
            return result

        except Exception as e:
            error_message = f"💥 Scheduler Error: {str(e)}"
            logger.error(error_message)
            await self._send_telegram_notification(error_message)

            return {
                "success": False,
                "error": str(e),
                "execution_id": locals().get('execution_id', 'unknown'),
                "execution_type": locals().get('execution_type', 'unknown')
            }

    async def _monitor_execution(self, execution_id: str, execution_type: str, max_wait: int = 1800) -> None:
        """Monitor background execution until completion"""
        start_time = time.time()
        last_status = None

        while time.time() - start_time < max_wait:
            try:
                status_data = await self._make_api_request("GET", f"/pipeline/runs/{execution_id}/status")
                current_status = status_data.get("status")

                if current_status != last_status:
                    logger.info(f"Execution {execution_id} status: {current_status}")
                    last_status = current_status

                if current_status in ["completed", "failed"]:
                    logger.info(f"Execution {execution_id} finished with status: {current_status}")
                    break

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error monitoring execution {execution_id}: {e}")
                break
        else:
            logger.warning(f"Execution {execution_id} monitoring timed out after {max_wait}s")

    async def get_execution_history(self, limit: int = 10) -> dict:
        """Get recent pipeline execution history"""
        try:
            return await self._make_api_request("GET", f"/pipeline/history?limit={limit}")
        except Exception as e:
            logger.error(f"Failed to get execution history: {e}")
            return {"executions": [], "error": str(e)}


def main():
    """Main entry point for scheduler"""
    import argparse

    parser = argparse.ArgumentParser(description="Uncle Stock Pipeline Scheduler")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without executing pipeline")
    parser.add_argument("--force-monthly", action="store_true", help="Force monthly execution (including Step 1)")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--history", action="store_true", help="Show recent execution history")

    args = parser.parse_args()

    try:
        scheduler = PipelineScheduler(args.api_url)

        if args.history:
            # Show execution history
            history = asyncio.run(scheduler.get_execution_history())
            print(f"Recent executions: {len(history.get('executions', []))}")
            for exec_info in history.get('executions', [])[:5]:
                print(f"  {exec_info.get('execution_id')}: {exec_info.get('status')} ({exec_info.get('execution_type')})")
            return

        # Override monthly check if forced
        if args.force_monthly:
            logger.info("Forcing monthly execution (--force-monthly)")
            # Temporarily set today as 1st for testing
            original_should_run = scheduler.should_run_monthly_fetch
            scheduler.should_run_monthly_fetch = lambda: asyncio.create_task(asyncio.coroutine(lambda: True)())

        # Execute pipeline
        result = asyncio.run(scheduler.execute_pipeline(dry_run=args.dry_run))

        if result["success"]:
            logger.info("Pipeline execution completed successfully")
            sys.exit(0)
        else:
            logger.error(f"Pipeline execution failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Scheduler initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()