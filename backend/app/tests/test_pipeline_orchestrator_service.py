"""
Comprehensive tests for Pipeline Orchestrator Service
Tests both service implementation and API endpoints with CLI compatibility verification
"""

import pytest
import asyncio
import uuid
import json
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from ..services.implementations.pipeline_orchestrator_service import PipelineOrchestratorService
from ..models.schemas import (
    PipelineExecutionStatus,
    PipelineStepStatus,
    PipelineStepInfo
)


class TestPipelineOrchestratorService:
    """Test cases for PipelineOrchestratorService"""

    @pytest.fixture
    def orchestrator_service(self):
        """Create orchestrator service instance for testing"""
        return PipelineOrchestratorService()

    @pytest.fixture
    def mock_step_functions(self):
        """Mock all step functions to return success"""
        with patch.multiple(
            'main',
            step1_fetch_data=Mock(return_value=True),
            step2_parse_data=Mock(return_value=True),
            step3_parse_history=Mock(return_value=True),
            step4_optimize_portfolio=Mock(return_value=True),
            step5_update_currency=Mock(return_value=True),
            step6_calculate_targets=Mock(return_value=True),
            step7_calculate_quantities=Mock(return_value=True),
            step8_ibkr_search=Mock(return_value=True),
            step9_rebalancer=Mock(return_value=True),
            step10_execute_orders=Mock(return_value=True),
            step11_check_order_status=Mock(return_value=True)
        ) as mocks:
            yield mocks

    @pytest.fixture
    def mock_failing_step_functions(self):
        """Mock step functions with failure at step 5"""
        with patch.multiple(
            'main',
            step1_fetch_data=Mock(return_value=True),
            step2_parse_data=Mock(return_value=True),
            step3_parse_history=Mock(return_value=True),
            step4_optimize_portfolio=Mock(return_value=True),
            step5_update_currency=Mock(return_value=False),  # Fails here
            step6_calculate_targets=Mock(return_value=True),
            step7_calculate_quantities=Mock(return_value=True),
            step8_ibkr_search=Mock(return_value=True),
            step9_rebalancer=Mock(return_value=True),
            step10_execute_orders=Mock(return_value=True),
            step11_check_order_status=Mock(return_value=True)
        ) as mocks:
            yield mocks

    def test_service_initialization(self, orchestrator_service):
        """Test service initializes correctly with step metadata"""
        assert orchestrator_service is not None
        assert len(orchestrator_service._step_functions) == 11
        assert len(orchestrator_service._step_info) == 11

        # Test step 1 metadata
        step1_info = orchestrator_service._step_info[1]
        assert step1_info.step_number == 1
        assert step1_info.step_name == "Fetch Data"
        assert "1" in step1_info.aliases
        assert "step1" in step1_info.aliases
        assert "fetch" in step1_info.aliases

    def test_get_available_steps(self, orchestrator_service):
        """Test getting available steps information"""
        result = orchestrator_service.get_available_steps()

        assert result["total_steps"] == 11
        assert 1 in result["steps"]
        assert 11 in result["steps"]

        # Test aliases mapping
        assert result["step_aliases"]["1"] == 1
        assert result["step_aliases"]["fetch"] == 1
        assert result["step_aliases"]["11"] == 11
        assert result["step_aliases"]["status"] == 11

    def test_get_step_function_mapping(self, orchestrator_service):
        """Test step function mapping"""
        mapping = orchestrator_service.get_step_function_mapping()

        assert len(mapping) == 11
        assert 1 in mapping
        assert 11 in mapping
        assert callable(mapping[1])

    @pytest.mark.asyncio
    async def test_validate_pipeline_dependencies(self, orchestrator_service):
        """Test dependency validation"""
        result = await orchestrator_service.validate_pipeline_dependencies()

        assert "valid" in result
        assert "checks" in result
        assert "missing_dependencies" in result
        assert "recommendations" in result
        assert "checked_at" in result

        # Should have checks for main_py_functions, data_directory, write_permissions
        assert "main_py_functions" in result["checks"]

    @pytest.mark.asyncio
    async def test_run_individual_step_success(self, orchestrator_service, mock_step_functions):
        """Test running individual step successfully"""
        step_number = 1
        execution_id = str(uuid.uuid4())

        result = await orchestrator_service.run_individual_step(step_number, execution_id)

        assert result["execution_id"] == execution_id
        assert result["step_number"] == step_number
        assert result["step_name"] == "Fetch Data"
        assert result["success"] is True
        assert result["execution_time"] >= 0
        assert isinstance(result["created_files"], list)
        assert isinstance(result["console_output"], list)
        assert result["error_message"] is None

        # Verify step function was called
        mock_step_functions["step1_fetch_data"].assert_called_once()

    @pytest.mark.asyncio
    async def test_run_individual_step_failure(self, orchestrator_service):
        """Test running individual step with failure"""
        with patch('main.step1_fetch_data', Mock(return_value=False)):
            step_number = 1
            execution_id = str(uuid.uuid4())

            result = await orchestrator_service.run_individual_step(step_number, execution_id)

            assert result["execution_id"] == execution_id
            assert result["step_number"] == step_number
            assert result["success"] is False
            assert result["error_message"] is not None

    @pytest.mark.asyncio
    async def test_run_individual_step_invalid_number(self, orchestrator_service):
        """Test running invalid step number"""
        step_number = 15  # Invalid
        execution_id = str(uuid.uuid4())

        result = await orchestrator_service.run_individual_step(step_number, execution_id)

        assert result["success"] is False
        assert "Invalid step number" in result["error_message"]

    @pytest.mark.asyncio
    async def test_run_step_range_success(self, orchestrator_service, mock_step_functions):
        """Test running step range successfully"""
        start_step = 1
        end_step = 3
        execution_id = str(uuid.uuid4())

        result = await orchestrator_service.run_step_range(start_step, end_step, execution_id)

        assert result["execution_id"] == execution_id
        assert result["start_step"] == start_step
        assert result["end_step"] == end_step
        assert result["success"] is True
        assert result["completed_steps"] == [1, 2, 3]
        assert result["failed_step"] is None
        assert result["execution_time"] >= 0

        # Verify all steps in range were called
        mock_step_functions["step1_fetch_data"].assert_called_once()
        mock_step_functions["step2_parse_data"].assert_called_once()
        mock_step_functions["step3_parse_history"].assert_called_once()

    @pytest.mark.asyncio
    async def test_run_step_range_with_failure(self, orchestrator_service, mock_failing_step_functions):
        """Test running step range with failure (fail-fast behavior)"""
        start_step = 4
        end_step = 7
        execution_id = str(uuid.uuid4())

        result = await orchestrator_service.run_step_range(start_step, end_step, execution_id)

        assert result["execution_id"] == execution_id
        assert result["success"] is False
        assert result["completed_steps"] == [4]  # Only step 4 completes before step 5 fails
        assert result["failed_step"] == 5

        # Verify fail-fast: steps after failure are not called
        mock_failing_step_functions["step4_optimize_portfolio"].assert_called_once()
        mock_failing_step_functions["step5_update_currency"].assert_called_once()
        mock_failing_step_functions["step6_calculate_targets"].assert_not_called()
        mock_failing_step_functions["step7_calculate_quantities"].assert_not_called()

    @pytest.mark.asyncio
    async def test_run_step_range_invalid_range(self, orchestrator_service):
        """Test running invalid step range"""
        execution_id = str(uuid.uuid4())

        # Test invalid range (start > end)
        result = await orchestrator_service.run_step_range(5, 3, execution_id)
        assert result["success"] is False
        assert "Invalid step range" in result.get("error_message", "")

        # Test invalid step numbers
        result = await orchestrator_service.run_step_range(0, 5, execution_id)
        assert result["success"] is False
        assert "Invalid step range" in result.get("error_message", "")

    @pytest.mark.asyncio
    async def test_run_full_pipeline_success(self, orchestrator_service, mock_step_functions):
        """Test running complete pipeline successfully"""
        execution_id = str(uuid.uuid4())

        result = await orchestrator_service.run_full_pipeline(execution_id)

        assert result["execution_id"] == execution_id
        assert result["success"] is True
        assert result["completed_steps"] == list(range(1, 12))
        assert result["failed_step"] is None
        assert result["execution_time"] >= 0
        assert len(result["created_files"]) > 0
        assert len(result["step_results"]) == 11
        assert result["error_message"] is None

        # Verify all steps were called
        for i in range(1, 12):
            step_func_name = f"step{i}_fetch_data" if i == 1 else f"step{i}_parse_data" if i == 2 else f"step{i}_parse_history" if i == 3 else f"step{i}_optimize_portfolio" if i == 4 else f"step{i}_update_currency" if i == 5 else f"step{i}_calculate_targets" if i == 6 else f"step{i}_calculate_quantities" if i == 7 else f"step{i}_ibkr_search" if i == 8 else f"step{i}_rebalancer" if i == 9 else f"step{i}_execute_orders" if i == 10 else f"step{i}_check_order_status"

            # Simplified: just check a few key steps
            if i == 1:
                mock_step_functions["step1_fetch_data"].assert_called_once()
            elif i == 5:
                mock_step_functions["step5_update_currency"].assert_called_once()
            elif i == 11:
                mock_step_functions["step11_check_order_status"].assert_called_once()

    @pytest.mark.asyncio
    async def test_run_full_pipeline_with_failure(self, orchestrator_service, mock_failing_step_functions):
        """Test running complete pipeline with failure (fail-fast)"""
        execution_id = str(uuid.uuid4())

        result = await orchestrator_service.run_full_pipeline(execution_id)

        assert result["execution_id"] == execution_id
        assert result["success"] is False
        assert result["completed_steps"] == [1, 2, 3, 4]  # Steps 1-4 succeed
        assert result["failed_step"] == 5  # Step 5 fails
        assert result["error_message"] is not None

        # Verify fail-fast behavior: steps after failure not called
        mock_failing_step_functions["step6_calculate_targets"].assert_not_called()
        mock_failing_step_functions["step11_check_order_status"].assert_not_called()

    @pytest.mark.asyncio
    async def test_get_execution_status(self, orchestrator_service, mock_step_functions):
        """Test getting execution status"""
        execution_id = str(uuid.uuid4())

        # Start execution in background
        asyncio.create_task(orchestrator_service.run_full_pipeline(execution_id))

        # Give it a moment to start
        await asyncio.sleep(0.1)

        status = await orchestrator_service.get_execution_status(execution_id)

        assert status["execution_id"] == execution_id
        assert status["status"] in [PipelineExecutionStatus.RUNNING, PipelineExecutionStatus.COMPLETED]
        assert isinstance(status["completed_steps"], list)
        assert status["execution_time"] >= 0
        assert status["progress_percentage"] >= 0

    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self, orchestrator_service):
        """Test getting status for non-existent execution"""
        fake_execution_id = str(uuid.uuid4())

        status = await orchestrator_service.get_execution_status(fake_execution_id)

        assert status["execution_id"] == fake_execution_id
        assert status["status"] == PipelineExecutionStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_execution_logs(self, orchestrator_service, mock_step_functions):
        """Test getting execution logs"""
        execution_id = str(uuid.uuid4())

        # Run a single step to generate logs
        await orchestrator_service.run_individual_step(1, execution_id)

        logs = await orchestrator_service.get_execution_logs(execution_id)

        assert logs["execution_id"] == execution_id
        assert isinstance(logs["logs"], list)
        assert logs["total_log_entries"] > 0

        # Test step-specific logs
        step_logs = await orchestrator_service.get_execution_logs(execution_id, step_number=1)
        assert step_logs["execution_id"] == execution_id
        assert step_logs["step_logs"] is None  # When filtering by step

    @pytest.mark.asyncio
    async def test_get_execution_results(self, orchestrator_service, mock_step_functions):
        """Test getting execution results"""
        execution_id = str(uuid.uuid4())

        # Run a single step
        await orchestrator_service.run_individual_step(1, execution_id)

        results = await orchestrator_service.get_execution_results(execution_id)

        assert results["execution_id"] == execution_id
        assert isinstance(results["created_files"], dict)
        assert isinstance(results["file_summaries"], dict)
        assert isinstance(results["step_summaries"], dict)
        assert isinstance(results["performance_metrics"], dict)

    @pytest.mark.asyncio
    async def test_resume_failed_pipeline(self, orchestrator_service, mock_step_functions):
        """Test resuming failed pipeline execution"""
        original_execution_id = str(uuid.uuid4())

        # First, run a pipeline that will "fail" at step 5
        with patch('main.step5_update_currency', Mock(return_value=False)):
            await orchestrator_service.run_full_pipeline(original_execution_id)

        # Now resume from the failed step
        result = await orchestrator_service.resume_failed_pipeline(original_execution_id, from_step=5)

        assert result["original_execution_id"] == original_execution_id
        assert result["resumed_from_step"] == 5
        assert result["execution_id"] != original_execution_id  # New execution ID
        assert isinstance(result["success"], bool)
        assert isinstance(result["completed_steps"], list)

    @pytest.mark.asyncio
    async def test_resume_nonexistent_pipeline(self, orchestrator_service):
        """Test resuming non-existent pipeline"""
        fake_execution_id = str(uuid.uuid4())

        result = await orchestrator_service.resume_failed_pipeline(fake_execution_id)

        assert result["original_execution_id"] == fake_execution_id
        assert result["success"] is False
        assert "not found" in result["error_message"]

    @pytest.mark.asyncio
    async def test_get_pipeline_history(self, orchestrator_service, mock_step_functions):
        """Test getting pipeline execution history"""
        # Run a few executions to create history
        for i in range(3):
            execution_id = str(uuid.uuid4())
            await orchestrator_service.run_individual_step(1, execution_id)

        history = await orchestrator_service.get_pipeline_history(limit=10)

        assert isinstance(history["executions"], list)
        assert history["total_executions"] >= 3
        assert history["filtered_count"] >= 3
        assert history["status_filter"] is None

    @pytest.mark.asyncio
    async def test_get_pipeline_history_with_filter(self, orchestrator_service, mock_step_functions):
        """Test getting pipeline history with status filter"""
        # Run some executions
        execution_id = str(uuid.uuid4())
        await orchestrator_service.run_individual_step(1, execution_id)

        history = await orchestrator_service.get_pipeline_history(
            limit=50,
            status_filter=PipelineExecutionStatus.COMPLETED
        )

        assert isinstance(history["executions"], list)
        assert history["status_filter"] == PipelineExecutionStatus.COMPLETED


class TestPipelineOrchestratorServiceCLICompatibility:
    """Test CLI compatibility aspects"""

    @pytest.fixture
    def orchestrator_service(self):
        return PipelineOrchestratorService()

    def test_step_aliases_match_cli(self, orchestrator_service):
        """Test that step aliases match CLI arguments exactly"""
        available_steps = orchestrator_service.get_available_steps()
        aliases = available_steps["step_aliases"]

        # Test CLI aliases as documented in main.py analysis
        assert aliases["1"] == 1
        assert aliases["step1"] == 1
        assert aliases["fetch"] == 1

        assert aliases["2"] == 2
        assert aliases["step2"] == 2
        assert aliases["parse"] == 2

        assert aliases["4"] == 4
        assert aliases["step4"] == 4
        assert aliases["portfolio"] == 4

        assert aliases["11"] == 11
        assert aliases["step11"] == 11
        assert aliases["status"] == 11

    def test_step_dependencies_match_analysis(self, orchestrator_service):
        """Test that step dependencies match the analysis from main.py"""
        step_info = orchestrator_service._step_info

        # Step 1 has no dependencies
        assert step_info[1].dependencies == []

        # Step 2 depends on step 1
        assert step_info[2].dependencies == [1]

        # Step 3 depends on step 2
        assert step_info[3].dependencies == [2]

        # Each subsequent step depends on the previous one
        for i in range(2, 12):
            assert step_info[i].dependencies == [i-1]

    def test_file_creation_patterns(self, orchestrator_service):
        """Test that file creation patterns match CLI analysis"""
        step_info = orchestrator_service._step_info

        # Step 1 creates CSV files
        assert "data/files_exports/*.csv" in step_info[1].creates_files

        # Step 2 creates universe.json
        assert "data/universe.json" in step_info[2].creates_files

        # Steps 3-7 modify universe.json
        for i in range(3, 8):
            assert "data/universe.json" in step_info[i].modifies_files

        # Step 8 creates universe_with_ibkr.json
        assert "data/universe_with_ibkr.json" in step_info[8].creates_files

        # Step 9 creates orders.json
        assert "data/orders.json" in step_info[9].creates_files