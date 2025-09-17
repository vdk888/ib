"""
Pipeline Orchestrator Service Implementation
Provides unified API for complete 11-step fintech pipeline execution
Following Interface-First Design with 100% CLI compatibility
"""

import asyncio
import uuid
import time
import traceback
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from io import StringIO

# Service layer imports for proper dependency injection
from ..interfaces import (
    IScreenerService,
    IUniverseRepository,
    IHistoricalDataService,
    IPortfolioOptimizer,
    ICurrencyService,
    ITargetAllocationService,
    IQuantityCalculator,
    IIBKRSearchService,
    IRebalancingService,
    IOrderExecutionService,
    IOrderStatusService,
    ITelegramService
)

from ..interfaces import IPipelineOrchestrator
from ...models.schemas import (
    PipelineExecutionStatus,
    PipelineStepStatus,
    PipelineStepInfo,
    PipelineStepResult,
    PipelineLogEntry,
    PipelineExecutionMetadata,
    PipelineExecutionResult,
    PipelineDependencyCheck,
    PipelineDependencyValidation
)


class PipelineExecutionManager:
    """
    Manages execution state, logging, and status tracking for pipeline runs
    """

    def __init__(self):
        self._executions: Dict[str, Dict[str, Any]] = {}
        self._logs: Dict[str, List[PipelineLogEntry]] = {}

    def create_execution(
        self,
        execution_id: str,
        execution_type: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Create new execution tracking"""
        self._executions[execution_id] = {
            "execution_id": execution_id,
            "status": PipelineExecutionStatus.PENDING,
            "current_step": None,
            "completed_steps": [],
            "failed_step": None,
            "start_time": datetime.utcnow(),
            "end_time": None,
            "execution_time": 0.0,
            "progress_percentage": 0.0,
            "step_results": {},
            "created_files": {},
            "metadata": metadata
        }
        self._logs[execution_id] = []

    def update_execution_status(
        self,
        execution_id: str,
        status: PipelineExecutionStatus,
        current_step: Optional[int] = None
    ) -> None:
        """Update execution status"""
        if execution_id in self._executions:
            self._executions[execution_id]["status"] = status
            if current_step is not None:
                self._executions[execution_id]["current_step"] = current_step
            self._executions[execution_id]["execution_time"] = (
                datetime.utcnow() - self._executions[execution_id]["start_time"]
            ).total_seconds()

    def add_step_result(
        self,
        execution_id: str,
        step_result: PipelineStepResult
    ) -> None:
        """Add step execution result"""
        if execution_id in self._executions:
            self._executions[execution_id]["step_results"][step_result.step_number] = step_result

            if step_result.success:
                if step_result.step_number not in self._executions[execution_id]["completed_steps"]:
                    self._executions[execution_id]["completed_steps"].append(step_result.step_number)
                self._executions[execution_id]["created_files"][step_result.step_number] = step_result.created_files
            else:
                self._executions[execution_id]["failed_step"] = step_result.step_number

    def add_log_entry(
        self,
        execution_id: str,
        level: str,
        message: str,
        step_number: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add structured log entry"""
        if execution_id not in self._logs:
            self._logs[execution_id] = []

        log_entry = PipelineLogEntry(
            timestamp=datetime.utcnow(),
            execution_id=execution_id,
            step_number=step_number,
            level=level,
            message=message,
            details=details
        )
        self._logs[execution_id].append(log_entry)

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current execution status"""
        return self._executions.get(execution_id)

    def get_execution_logs(self, execution_id: str) -> List[PipelineLogEntry]:
        """Get execution logs"""
        return self._logs.get(execution_id, [])


class PipelineOrchestratorService(IPipelineOrchestrator):
    """
    Pipeline Orchestrator Service Implementation

    Provides unified API orchestration of the complete 11-step fintech pipeline
    with 100% CLI compatibility and async execution capabilities.
    Uses service layer dependency injection instead of direct main.py imports.
    """

    def __init__(
        self,
        screener_service: IScreenerService,
        universe_service: IUniverseRepository,
        historical_data_service: IHistoricalDataService,
        portfolio_optimizer_service: IPortfolioOptimizer,
        currency_service: ICurrencyService,
        target_allocation_service: ITargetAllocationService,
        quantity_service: IQuantityCalculator,
        ibkr_search_service: IIBKRSearchService,
        rebalancing_service: IRebalancingService,
        order_execution_service: IOrderExecutionService,
        order_status_service: IOrderStatusService,
        telegram_service: ITelegramService
    ):
        self.execution_manager = PipelineExecutionManager()

        # Inject service dependencies
        self.screener_service = screener_service
        self.universe_service = universe_service
        self.historical_data_service = historical_data_service
        self.portfolio_optimizer_service = portfolio_optimizer_service
        self.currency_service = currency_service
        self.target_allocation_service = target_allocation_service
        self.quantity_service = quantity_service
        self.ibkr_search_service = ibkr_search_service
        self.rebalancing_service = rebalancing_service
        self.order_execution_service = order_execution_service
        self.order_status_service = order_status_service
        self.telegram_service = telegram_service

        # Step function mapping using service layer methods
        self._step_functions: Dict[int, Callable[[], bool]] = {
            1: self._step1_fetch_data,
            2: self._step2_parse_data,
            3: self._step3_parse_history,
            4: self._step4_optimize_portfolio,
            5: self._step5_update_currency,
            6: self._step6_calculate_targets,
            7: self._step7_calculate_quantities,
            8: self._step8_ibkr_search,
            9: self._step9_rebalancer,
            10: self._step10_execute_orders,
            11: self._step11_check_order_status,
        }

        # Step metadata from main.py analysis
        self._step_info: Dict[int, PipelineStepInfo] = {
            1: PipelineStepInfo(
                step_number=1,
                step_name="Fetch Data",
                description="Fetch current stocks and backtest history from all screeners",
                aliases=["1", "step1", "fetch"],
                dependencies=[],
                creates_files=["data/files_exports/*.csv"],
                modifies_files=[]
            ),
            2: PipelineStepInfo(
                step_number=2,
                step_name="Parse Data",
                description="Parse CSV files and create universe.json",
                aliases=["2", "step2", "parse"],
                dependencies=[1],
                creates_files=["data/universe.json"],
                modifies_files=[]
            ),
            3: PipelineStepInfo(
                step_number=3,
                step_name="Parse History",
                description="Parse historical performance data and update universe.json",
                aliases=["3", "step3", "history"],
                dependencies=[2],
                creates_files=[],
                modifies_files=["data/universe.json"]
            ),
            4: PipelineStepInfo(
                step_number=4,
                step_name="Optimize Portfolio",
                description="Optimize portfolio allocations using Sharpe ratio maximization",
                aliases=["4", "step4", "portfolio"],
                dependencies=[3],
                creates_files=[],
                modifies_files=["data/universe.json"]
            ),
            5: PipelineStepInfo(
                step_number=5,
                step_name="Update Currency",
                description="Update EUR exchange rates",
                aliases=["5", "step5", "currency"],
                dependencies=[4],
                creates_files=[],
                modifies_files=["data/universe.json"]
            ),
            6: PipelineStepInfo(
                step_number=6,
                step_name="Calculate Targets",
                description="Calculate final stock allocations",
                aliases=["6", "step6", "target"],
                dependencies=[5],
                creates_files=[],
                modifies_files=["data/universe.json"]
            ),
            7: PipelineStepInfo(
                step_number=7,
                step_name="Calculate Quantities",
                description="Get account value from IBKR and calculate stock quantities",
                aliases=["7", "step7", "qty"],
                dependencies=[6],
                creates_files=[],
                modifies_files=["data/universe.json"]
            ),
            8: PipelineStepInfo(
                step_number=8,
                step_name="IBKR Search",
                description="Search for all universe stocks on IBKR and update with identification details",
                aliases=["8", "step8", "ibkr"],
                dependencies=[7],
                creates_files=["data/universe_with_ibkr.json"],
                modifies_files=[]
            ),
            9: PipelineStepInfo(
                step_number=9,
                step_name="Rebalance",
                description="Generate rebalancing orders based on targets vs current positions",
                aliases=["9", "step9", "rebalance"],
                dependencies=[8],
                creates_files=["data/orders.json"],
                modifies_files=[]
            ),
            10: PipelineStepInfo(
                step_number=10,
                step_name="Execute Orders",
                description="Execute rebalancing orders through IBKR API",
                aliases=["10", "step10", "execute"],
                dependencies=[9],
                creates_files=[],
                modifies_files=[]
            ),
            11: PipelineStepInfo(
                step_number=11,
                step_name="Check Status",
                description="Check order status and verify execution",
                aliases=["11", "step11", "status"],
                dependencies=[10],
                creates_files=[],
                modifies_files=[]
            )
        }

    @contextmanager
    def _capture_console_output(self):
        """Context manager to capture console output from step functions"""
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()

        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                yield stdout_buffer, stderr_buffer
        finally:
            pass

    async def _execute_step(
        self,
        step_number: int,
        execution_id: str
    ) -> PipelineStepResult:
        """Execute individual step with console output capture and error handling"""
        step_info = self._step_info[step_number]
        start_time = datetime.utcnow()

        # Send Telegram notification for step start
        await self.telegram_service.notify_step_start(
            step_number=step_number,
            step_name=step_info.step_name,
            execution_id=execution_id
        )

        # Log step start
        self.execution_manager.add_log_entry(
            execution_id,
            "INFO",
            f"Starting {step_info.step_name}",
            step_number
        )

        # Update execution status
        self.execution_manager.update_execution_status(
            execution_id,
            PipelineExecutionStatus.RUNNING,
            step_number
        )

        try:
            # Capture console output and execute step function
            with self._capture_console_output() as (stdout_buffer, stderr_buffer):
                step_function = self._step_functions[step_number]
                success = step_function()

            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()

            # Get console output
            stdout_lines = stdout_buffer.getvalue().splitlines()
            stderr_lines = stderr_buffer.getvalue().splitlines()
            console_output = stdout_lines + stderr_lines

            # Create step result
            step_result = PipelineStepResult(
                step_number=step_number,
                step_name=step_info.step_name,
                status=PipelineStepStatus.COMPLETED if success else PipelineStepStatus.FAILED,
                success=success,
                execution_time=execution_time,
                start_time=start_time,
                end_time=end_time,
                created_files=step_info.creates_files if success else [],
                modified_files=step_info.modifies_files if success else [],
                console_output=console_output,
                error_message=None if success else f"Step {step_number} failed - stopping pipeline"
            )

            # Send Telegram notification for step completion
            details = {}
            if success and len(step_info.creates_files) > 0:
                details["created_files"] = step_info.creates_files
            elif not success:
                details["error_message"] = step_result.error_message

            await self.telegram_service.notify_step_complete(
                step_number=step_number,
                step_name=step_info.step_name,
                execution_id=execution_id,
                success=success,
                execution_time=execution_time,
                details=details
            )

            # Log step completion
            self.execution_manager.add_log_entry(
                execution_id,
                "INFO" if success else "ERROR",
                f"{'Completed' if success else 'Failed'} {step_info.step_name} in {execution_time:.2f}s",
                step_number,
                {"success": success, "execution_time": execution_time}
            )

            return step_result

        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            error_traceback = traceback.format_exc()

            # Send Telegram notification for step failure due to exception
            await self.telegram_service.notify_step_complete(
                step_number=step_number,
                step_name=step_info.step_name,
                execution_id=execution_id,
                success=False,
                execution_time=execution_time,
                details={"error_message": str(e)}
            )

            # Log step error
            self.execution_manager.add_log_entry(
                execution_id,
                "ERROR",
                f"Exception in {step_info.step_name}: {str(e)}",
                step_number,
                {"exception": str(e), "traceback": error_traceback}
            )

            step_result = PipelineStepResult(
                step_number=step_number,
                step_name=step_info.step_name,
                status=PipelineStepStatus.FAILED,
                success=False,
                execution_time=execution_time,
                start_time=start_time,
                end_time=end_time,
                created_files=[],
                modified_files=[],
                console_output=[],
                error_message=str(e),
                error_traceback=error_traceback
            )

            return step_result

    async def run_full_pipeline(self, execution_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute complete 11-step pipeline with fail-fast error handling"""
        if execution_id is None:
            execution_id = str(uuid.uuid4())

        # Create execution tracking
        metadata = PipelineExecutionMetadata(
            execution_id=execution_id,
            execution_type="full_pipeline",
            start_time=datetime.utcnow(),
            target_steps=list(range(1, 12))
        )

        self.execution_manager.create_execution(execution_id, "full_pipeline", metadata.dict())

        # Send Telegram notification for pipeline start
        await self.telegram_service.notify_pipeline_start(
            pipeline_type="monthly",
            target_steps=list(range(1, 12)),
            execution_id=execution_id
        )

        # Log pipeline start
        self.execution_manager.add_log_entry(
            execution_id,
            "INFO",
            "Starting full pipeline execution (11 steps)",
            details={"execution_type": "full_pipeline", "target_steps": list(range(1, 12))}
        )

        overall_start_time = time.time()
        completed_steps = []
        failed_step = None
        step_results = {}
        created_files = {}

        try:
            # Execute steps 1-11 sequentially with fail-fast behavior
            for step_number in range(1, 12):
                step_result = await self._execute_step(step_number, execution_id)
                step_results[step_number] = step_result

                # Add step result to execution manager
                self.execution_manager.add_step_result(execution_id, step_result)

                if step_result.success:
                    completed_steps.append(step_number)
                    created_files[step_number] = step_result.created_files

                    # Update progress
                    progress = (step_number / 11) * 100
                    execution = self.execution_manager.get_execution_status(execution_id)
                    if execution:
                        execution["progress_percentage"] = progress
                else:
                    # Fail-fast behavior - stop on first failure
                    failed_step = step_number
                    self.execution_manager.add_log_entry(
                        execution_id,
                        "ERROR",
                        f"Pipeline failed at step {step_number} - stopping execution",
                        details={"failed_step": step_number, "error": step_result.error_message}
                    )
                    break

            # Calculate final results
            overall_execution_time = time.time() - overall_start_time
            success = failed_step is None

            # Update execution status
            final_status = PipelineExecutionStatus.COMPLETED if success else PipelineExecutionStatus.FAILED
            self.execution_manager.update_execution_status(execution_id, final_status)

            # Send Telegram notification for pipeline completion
            await self.telegram_service.notify_pipeline_complete(
                pipeline_type="monthly",
                execution_id=execution_id,
                success=success,
                completed_steps=completed_steps,
                failed_step=failed_step,
                execution_time=overall_execution_time,
                summary_stats=None  # Could add portfolio stats here if available
            )

            # Final logging
            self.execution_manager.add_log_entry(
                execution_id,
                "INFO" if success else "ERROR",
                f"Pipeline {'completed successfully' if success else 'failed'} in {overall_execution_time:.2f}s",
                details={
                    "success": success,
                    "execution_time": overall_execution_time,
                    "completed_steps": completed_steps,
                    "failed_step": failed_step
                }
            )

            return {
                "execution_id": execution_id,
                "success": success,
                "completed_steps": completed_steps,
                "failed_step": failed_step,
                "execution_time": overall_execution_time,
                "created_files": created_files,
                "step_results": step_results,
                "error_message": step_results.get(failed_step, {}).get("error_message") if failed_step else None
            }

        except Exception as e:
            # Handle unexpected pipeline-level errors
            overall_execution_time = time.time() - overall_start_time
            error_message = f"Pipeline execution failed with unexpected error: {str(e)}"

            self.execution_manager.update_execution_status(execution_id, PipelineExecutionStatus.FAILED)

            # Send Telegram notification for pipeline failure due to exception
            await self.telegram_service.notify_pipeline_complete(
                pipeline_type="monthly",
                execution_id=execution_id,
                success=False,
                completed_steps=completed_steps,
                failed_step=None,  # Pipeline-level failure
                execution_time=overall_execution_time,
                summary_stats=None
            )

            self.execution_manager.add_log_entry(
                execution_id,
                "ERROR",
                error_message,
                details={"exception": str(e), "traceback": traceback.format_exc()}
            )

            return {
                "execution_id": execution_id,
                "success": False,
                "completed_steps": completed_steps,
                "failed_step": None,  # Pipeline-level failure
                "execution_time": overall_execution_time,
                "created_files": created_files,
                "step_results": step_results,
                "error_message": error_message
            }

    async def run_individual_step(
        self,
        step_number: int,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute single pipeline step"""
        if execution_id is None:
            execution_id = str(uuid.uuid4())

        if step_number not in self._step_functions:
            return {
                "execution_id": execution_id,
                "step_number": step_number,
                "step_name": f"Step {step_number}",
                "success": False,
                "execution_time": 0,
                "created_files": [],
                "console_output": [],
                "error_message": f"Invalid step number: {step_number}. Must be 1-11."
            }

        # Create execution tracking
        metadata = PipelineExecutionMetadata(
            execution_id=execution_id,
            execution_type="individual_step",
            start_time=datetime.utcnow(),
            single_step=step_number
        )

        self.execution_manager.create_execution(execution_id, "individual_step", metadata.dict())

        # Execute step
        step_result = await self._execute_step(step_number, execution_id)

        # Update final execution status
        final_status = PipelineExecutionStatus.COMPLETED if step_result.success else PipelineExecutionStatus.FAILED
        self.execution_manager.update_execution_status(execution_id, final_status)

        return {
            "execution_id": execution_id,
            "step_number": step_number,
            "step_name": step_result.step_name,
            "success": step_result.success,
            "execution_time": step_result.execution_time,
            "created_files": step_result.created_files,
            "console_output": step_result.console_output,
            "error_message": step_result.error_message
        }

    async def run_step_range(
        self,
        start_step: int,
        end_step: int,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute range of pipeline steps with fail-fast behavior"""
        if execution_id is None:
            execution_id = str(uuid.uuid4())

        # Validate step range
        if start_step < 1 or end_step > 11 or start_step > end_step:
            return {
                "execution_id": execution_id,
                "success": False,
                "start_step": start_step,
                "end_step": end_step,
                "completed_steps": [],
                "failed_step": None,
                "execution_time": 0,
                "step_results": {},
                "error_message": f"Invalid step range: {start_step}-{end_step}. Steps must be 1-11 and start <= end."
            }

        # Create execution tracking
        target_steps = list(range(start_step, end_step + 1))
        metadata = PipelineExecutionMetadata(
            execution_id=execution_id,
            execution_type="step_range",
            start_time=datetime.utcnow(),
            target_steps=target_steps,
            start_step=start_step,
            end_step=end_step
        )

        self.execution_manager.create_execution(execution_id, "step_range", metadata.dict())

        # Log range start
        self.execution_manager.add_log_entry(
            execution_id,
            "INFO",
            f"Starting step range execution: steps {start_step}-{end_step}",
            details={"start_step": start_step, "end_step": end_step, "target_steps": target_steps}
        )

        overall_start_time = time.time()
        completed_steps = []
        failed_step = None
        step_results = {}

        try:
            # Execute steps in range sequentially with fail-fast behavior
            for step_number in range(start_step, end_step + 1):
                step_result = await self._execute_step(step_number, execution_id)
                step_results[step_number] = step_result

                # Add step result to execution manager
                self.execution_manager.add_step_result(execution_id, step_result)

                if step_result.success:
                    completed_steps.append(step_number)
                else:
                    # Fail-fast behavior - stop on first failure
                    failed_step = step_number
                    self.execution_manager.add_log_entry(
                        execution_id,
                        "ERROR",
                        f"Step range failed at step {step_number} - stopping execution",
                        details={"failed_step": step_number, "error": step_result.error_message}
                    )
                    break

            # Calculate final results
            overall_execution_time = time.time() - overall_start_time
            success = failed_step is None

            # Update execution status
            final_status = PipelineExecutionStatus.COMPLETED if success else PipelineExecutionStatus.FAILED
            self.execution_manager.update_execution_status(execution_id, final_status)

            return {
                "execution_id": execution_id,
                "success": success,
                "start_step": start_step,
                "end_step": end_step,
                "completed_steps": completed_steps,
                "failed_step": failed_step,
                "execution_time": overall_execution_time,
                "step_results": step_results
            }

        except Exception as e:
            # Handle unexpected range-level errors
            overall_execution_time = time.time() - overall_start_time
            error_message = f"Step range execution failed with unexpected error: {str(e)}"

            self.execution_manager.update_execution_status(execution_id, PipelineExecutionStatus.FAILED)
            self.execution_manager.add_log_entry(
                execution_id,
                "ERROR",
                error_message,
                details={"exception": str(e), "traceback": traceback.format_exc()}
            )

            return {
                "execution_id": execution_id,
                "success": False,
                "start_step": start_step,
                "end_step": end_step,
                "completed_steps": completed_steps,
                "failed_step": None,
                "execution_time": overall_execution_time,
                "step_results": step_results
            }

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get real-time status of running or completed pipeline execution"""
        execution = self.execution_manager.get_execution_status(execution_id)
        if not execution:
            return {
                "execution_id": execution_id,
                "status": PipelineExecutionStatus.NOT_FOUND,
                "current_step": None,
                "completed_steps": [],
                "failed_step": None,
                "start_time": None,
                "execution_time": 0,
                "progress_percentage": 0,
                "estimated_remaining_time": None
            }

        # Calculate estimated remaining time for running executions
        estimated_remaining = None
        if execution["status"] == PipelineExecutionStatus.RUNNING and execution["current_step"]:
            # Simple estimation based on average step time (rough estimate)
            avg_step_time = execution["execution_time"] / len(execution["completed_steps"]) if execution["completed_steps"] else 30
            remaining_steps = 11 - len(execution["completed_steps"])
            estimated_remaining = avg_step_time * remaining_steps

        return {
            "execution_id": execution_id,
            "status": execution["status"],
            "current_step": execution["current_step"],
            "completed_steps": execution["completed_steps"],
            "failed_step": execution["failed_step"],
            "start_time": execution["start_time"],
            "execution_time": execution["execution_time"],
            "progress_percentage": execution["progress_percentage"],
            "estimated_remaining_time": estimated_remaining
        }

    async def get_execution_logs(
        self,
        execution_id: str,
        step_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get structured execution logs for pipeline run"""
        logs = self.execution_manager.get_execution_logs(execution_id)

        if step_number is not None:
            # Filter logs for specific step
            filtered_logs = [log for log in logs if log.step_number == step_number]
            return {
                "execution_id": execution_id,
                "logs": [log.dict() for log in filtered_logs],
                "step_logs": None,
                "total_log_entries": len(filtered_logs)
            }
        else:
            # Group logs by step
            step_logs = {}
            for log in logs:
                step_num = log.step_number if log.step_number is not None else 0  # 0 for pipeline-level logs
                if step_num not in step_logs:
                    step_logs[step_num] = []
                step_logs[step_num].append(log)

            return {
                "execution_id": execution_id,
                "logs": [log.dict() for log in logs],
                "step_logs": {k: [log.dict() for log in v] for k, v in step_logs.items()},
                "total_log_entries": len(logs)
            }

    async def get_execution_results(self, execution_id: str) -> Dict[str, Any]:
        """Get detailed execution results and created files"""
        execution = self.execution_manager.get_execution_status(execution_id)
        if not execution:
            return {
                "execution_id": execution_id,
                "success": False,
                "created_files": {},
                "file_summaries": {},
                "step_summaries": {},
                "performance_metrics": {}
            }

        # Get file summaries (basic file info)
        file_summaries = {}
        for step_num, files in execution.get("created_files", {}).items():
            for file_path in files:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    file_summaries[file_path] = {
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime),
                        "created_by_step": step_num
                    }

        # Get step summaries
        step_summaries = {}
        for step_num, step_result in execution.get("step_results", {}).items():
            if hasattr(step_result, 'dict'):
                step_summaries[step_num] = step_result.dict()
            else:
                step_summaries[step_num] = step_result

        return {
            "execution_id": execution_id,
            "success": execution.get("status") == PipelineExecutionStatus.COMPLETED,
            "created_files": execution.get("created_files", {}),
            "file_summaries": file_summaries,
            "step_summaries": step_summaries,
            "performance_metrics": {
                "total_execution_time": execution.get("execution_time", 0),
                "completed_steps": len(execution.get("completed_steps", [])),
                "total_steps": 11
            }
        }

    async def resume_failed_pipeline(
        self,
        execution_id: str,
        from_step: Optional[int] = None
    ) -> Dict[str, Any]:
        """Resume failed pipeline execution from specified step"""
        original_execution = self.execution_manager.get_execution_status(execution_id)
        if not original_execution:
            return {
                "execution_id": None,
                "original_execution_id": execution_id,
                "resumed_from_step": None,
                "success": False,
                "completed_steps": [],
                "execution_time": 0,
                "error_message": f"Original execution {execution_id} not found"
            }

        # Determine resume step
        if from_step is None:
            # Auto-detect: resume from failed step or next step after last completed
            if original_execution.get("failed_step"):
                from_step = original_execution["failed_step"]
            else:
                completed_steps = original_execution.get("completed_steps", [])
                from_step = max(completed_steps) + 1 if completed_steps else 1

        if from_step > 11:
            return {
                "execution_id": None,
                "original_execution_id": execution_id,
                "resumed_from_step": from_step,
                "success": False,
                "completed_steps": [],
                "execution_time": 0,
                "error_message": f"Cannot resume from step {from_step}: pipeline only has 11 steps"
            }

        # Create new execution for resumed run
        new_execution_id = str(uuid.uuid4())

        # Run remaining steps
        result = await self.run_step_range(from_step, 11, new_execution_id)

        # Mark as resumed execution
        execution = self.execution_manager.get_execution_status(new_execution_id)
        if execution and "metadata" in execution:
            execution["metadata"]["is_resumed"] = True
            execution["metadata"]["original_execution_id"] = execution_id
            execution["metadata"]["resumed_from_step"] = from_step

        return {
            "execution_id": new_execution_id,
            "original_execution_id": execution_id,
            "resumed_from_step": from_step,
            "success": result["success"],
            "completed_steps": result["completed_steps"],
            "execution_time": result["execution_time"]
        }

    async def get_pipeline_history(
        self,
        limit: int = 50,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get history of pipeline executions"""
        # Get all executions
        all_executions = []
        for exec_id, execution in self.execution_manager._executions.items():
            if status_filter is None or execution.get("status") == status_filter:
                all_executions.append({
                    "execution_id": exec_id,
                    "execution_type": execution.get("metadata", {}).get("execution_type", "unknown"),
                    "status": execution.get("status"),
                    "success": execution.get("status") == PipelineExecutionStatus.COMPLETED,
                    "start_time": execution.get("start_time"),
                    "end_time": execution.get("end_time"),
                    "execution_time": execution.get("execution_time"),
                    "completed_steps": execution.get("completed_steps", []),
                    "failed_step": execution.get("failed_step"),
                    "total_files_created": sum(len(files) for files in execution.get("created_files", {}).values()),
                    "is_resumed": execution.get("metadata", {}).get("is_resumed", False)
                })

        # Sort by start time (most recent first) and limit
        all_executions.sort(key=lambda x: x["start_time"], reverse=True)
        limited_executions = all_executions[:limit]

        return {
            "executions": limited_executions,
            "total_executions": len(all_executions),
            "filtered_count": len(limited_executions),
            "status_filter": status_filter
        }

    def get_available_steps(self) -> Dict[str, Any]:
        """Get list of all available pipeline steps with descriptions"""
        # Build step aliases mapping
        step_aliases = {}
        for step_num, step_info in self._step_info.items():
            for alias in step_info.aliases:
                step_aliases[alias] = step_num

        return {
            "steps": {num: info.dict() for num, info in self._step_info.items()},
            "total_steps": len(self._step_info),
            "step_aliases": step_aliases
        }

    async def validate_pipeline_dependencies(self) -> Dict[str, Any]:
        """Validate that all pipeline dependencies and prerequisites are met"""
        checks = {}
        missing_dependencies = []
        recommendations = []

        # Check service layer accessibility
        try:
            # Validate that all required services are available
            services_to_check = [
                ("screener_service", self.screener_service),
                ("universe_service", self.universe_service),
                ("historical_data_service", self.historical_data_service),
                ("portfolio_optimizer_service", self.portfolio_optimizer_service),
                ("currency_service", self.currency_service),
                ("target_allocation_service", self.target_allocation_service),
                ("quantity_service", self.quantity_service),
                ("ibkr_search_service", self.ibkr_search_service),
                ("rebalancing_service", self.rebalancing_service),
                ("order_execution_service", self.order_execution_service),
                ("order_status_service", self.order_status_service)
            ]

            for service_name, service_instance in services_to_check:
                if service_instance is None:
                    checks[service_name] = PipelineDependencyCheck(
                        name=service_name,
                        type="service",
                        required=True,
                        valid=False,
                        details=f"Service {service_name} is not injected or is None",
                        recommendation=f"Ensure {service_name} is properly injected in dependencies.py"
                    )
                    missing_dependencies.append(service_name)
                    recommendations.append(f"Fix {service_name} dependency injection")
                else:
                    checks[service_name] = PipelineDependencyCheck(
                        name=service_name,
                        type="service",
                        required=True,
                        valid=True,
                        details=f"Service {service_name} is properly injected",
                        recommendation=None
                    )

        except Exception as e:
            checks["service_layer"] = PipelineDependencyCheck(
                name="service_layer",
                type="code",
                required=True,
                valid=False,
                details=f"Cannot access service layer: {str(e)}",
                recommendation="Ensure all services are properly configured in dependencies.py"
            )
            missing_dependencies.append("service_layer")
            recommendations.append("Fix service layer dependency injection configuration")

        # Check data directory structure
        data_dir = "data"
        if os.path.exists(data_dir) and os.path.isdir(data_dir):
            checks["data_directory"] = PipelineDependencyCheck(
                name="data_directory",
                type="file",
                required=True,
                valid=True,
                details="Data directory exists and is accessible",
                recommendation=None
            )
        else:
            checks["data_directory"] = PipelineDependencyCheck(
                name="data_directory",
                type="file",
                required=True,
                valid=False,
                details="Data directory does not exist",
                recommendation="Create data directory: mkdir data"
            )
            missing_dependencies.append("data_directory")
            recommendations.append("Create the data directory for file storage")

        # Check for write permissions in current directory
        try:
            test_file = "test_permissions.tmp"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            checks["write_permissions"] = PipelineDependencyCheck(
                name="write_permissions",
                type="system",
                required=True,
                valid=True,
                details="Write permissions available in current directory",
                recommendation=None
            )
        except Exception as e:
            checks["write_permissions"] = PipelineDependencyCheck(
                name="write_permissions",
                type="system",
                required=True,
                valid=False,
                details=f"Cannot write to current directory: {str(e)}",
                recommendation="Ensure write permissions in the working directory"
            )
            missing_dependencies.append("write_permissions")
            recommendations.append("Fix directory write permissions")

        # Overall validation result
        all_valid = len(missing_dependencies) == 0

        return {
            "valid": all_valid,
            "checks": {name: check.dict() for name, check in checks.items()},
            "missing_dependencies": missing_dependencies,
            "recommendations": recommendations,
            "checked_at": datetime.utcnow()
        }

    def get_step_function_mapping(self) -> Dict[int, Callable]:
        """Get mapping of step numbers to their corresponding functions"""
        return self._step_functions.copy()

    # Service layer step implementations
    # Each step wraps the corresponding service method to return boolean success status

    def _step1_fetch_data(self) -> bool:
        """Step 1: Fetch data from screeners"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.screener_service.fetch_all_screener_data())
            loop.close()
            # Check if any screeners returned data
            return any(screen_data.get('success', False) for screen_data in result.values())
        except Exception as e:
            print(f"Step 1 failed: {e}")
            return False

    def _step2_parse_data(self) -> bool:
        """Step 2: Parse CSV files and create universe.json"""
        try:
            result = self.universe_service.create_universe()
            if result and 'metadata' in result:
                self.universe_service.save_universe(result)
                return True
            return False
        except Exception as e:
            print(f"Step 2 failed: {e}")
            return False

    def _step3_parse_history(self) -> bool:
        """Step 3: Parse historical performance data"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.historical_data_service.update_universe_with_history())
            loop.close()
            return result
        except Exception as e:
            print(f"Step 3 failed: {e}")
            return False

    def _step4_optimize_portfolio(self) -> bool:
        """Step 4: Optimize portfolio allocations"""
        try:
            return self.portfolio_optimizer_service.main()
        except Exception as e:
            print(f"Step 4 failed: {e}")
            return False

    def _step5_update_currency(self) -> bool:
        """Step 5: Update EUR exchange rates"""
        try:
            return self.currency_service.run_currency_update()
        except Exception as e:
            print(f"Step 5 failed: {e}")
            return False

    def _step6_calculate_targets(self) -> bool:
        """Step 6: Calculate target allocations"""
        try:
            return self.target_allocation_service.main()
        except Exception as e:
            print(f"Step 6 failed: {e}")
            return False

    def _step7_calculate_quantities(self) -> bool:
        """Step 7: Calculate quantities from IBKR account value"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Get account value and calculate quantities
            from ...core.dependencies import get_quantity_orchestrator_service
            quantity_orchestrator = get_quantity_orchestrator_service()
            result = loop.run_until_complete(quantity_orchestrator.calculate_all_quantities())
            loop.close()
            return result.get('success', False)
        except Exception as e:
            print(f"Step 7 failed: {e}")
            return False

    def _step8_ibkr_search(self) -> bool:
        """Step 8: Search stocks on IBKR"""
        try:
            result = self.ibkr_search_service.process_all_universe_stocks()
            # Success if we found any stocks
            found_count = result.get('found_isin', 0) + result.get('found_ticker', 0) + result.get('found_name', 0)
            return found_count > 0
        except Exception as e:
            print(f"Step 8 failed: {e}")
            return False

    def _step9_rebalancer(self) -> bool:
        """Step 9: Generate rebalancing orders"""
        try:
            result = self.rebalancing_service.run_rebalancing("data/universe_with_ibkr.json")
            return len(result.get('orders', [])) > 0
        except Exception as e:
            print(f"Step 9 failed: {e}")
            return False

    def _step10_execute_orders(self) -> bool:
        """Step 10: Execute orders through IBKR"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.order_execution_service.run_execution())
            loop.close()
            return result.get('success', False)
        except Exception as e:
            print(f"Step 10 failed: {e}")
            return False

    def _step11_check_order_status(self) -> bool:
        """Step 11: Check order status and verification"""
        try:
            return self.order_status_service.run_status_check()
        except Exception as e:
            print(f"Step 11 failed: {e}")
            return False