"""
Integration tests for Pipeline Orchestration API endpoints
Tests complete REST API functionality with CLI compatibility
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from ..main import app
from ..services.implementations.pipeline_orchestrator_service import PipelineOrchestratorService


class TestPipelineAPI:
    """Test cases for Pipeline API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_orchestrator_service(self):
        """Mock orchestrator service for testing"""
        mock_service = AsyncMock(spec=PipelineOrchestratorService)

        # Mock available steps
        mock_service.get_available_steps.return_value = {
            "steps": {
                1: {
                    "step_number": 1,
                    "step_name": "Fetch Data",
                    "description": "Fetch current stocks and backtest history from all screeners",
                    "aliases": ["1", "step1", "fetch"],
                    "dependencies": [],
                    "creates_files": ["data/files_exports/*.csv"],
                    "modifies_files": []
                }
            },
            "total_steps": 11,
            "step_aliases": {
                "1": 1,
                "step1": 1,
                "fetch": 1
            }
        }

        # Mock dependency validation
        mock_service.validate_pipeline_dependencies.return_value = {
            "valid": True,
            "checks": {},
            "missing_dependencies": [],
            "recommendations": [],
            "checked_at": "2024-01-01T12:00:00Z"
        }

        return mock_service

    def test_get_available_steps_success(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/steps/available"""
        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get("/api/v1/pipeline/steps/available")

            assert response.status_code == 200
            data = response.json()

            assert "steps" in data
            assert "total_steps" in data
            assert "step_aliases" in data
            assert data["total_steps"] == 11
            assert "1" in data["step_aliases"]

    def test_validate_dependencies_success(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/dependencies/validate"""
        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get("/api/v1/pipeline/dependencies/validate")

            assert response.status_code == 200
            data = response.json()

            assert "valid" in data
            assert "checks" in data
            assert "missing_dependencies" in data
            assert "recommendations" in data
            assert data["valid"] is True

    def test_run_individual_step_success(self, client, mock_orchestrator_service):
        """Test POST /api/v1/pipeline/run/step/{step_number}"""
        mock_orchestrator_service.run_individual_step.return_value = {
            "execution_id": "test-execution-id",
            "step_number": 1,
            "step_name": "Fetch Data",
            "success": True,
            "execution_time": 45.2,
            "created_files": ["data/files_exports/screener1.csv"],
            "console_output": ["STEP 1: Fetching data", "Step 1 complete"],
            "error_message": None
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.post("/api/v1/pipeline/run/step/1")

            assert response.status_code == 200
            data = response.json()

            assert data["step_number"] == 1
            assert data["step_name"] == "Fetch Data"
            assert data["success"] is True
            assert isinstance(data["created_files"], list)
            assert isinstance(data["console_output"], list)

    def test_run_individual_step_invalid_number(self, client, mock_orchestrator_service):
        """Test POST /api/v1/pipeline/run/step/{step_number} with invalid step"""
        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.post("/api/v1/pipeline/run/step/15")

            assert response.status_code == 400
            data = response.json()
            assert "Invalid step number" in data["detail"]

    def test_run_full_pipeline_success(self, client, mock_orchestrator_service):
        """Test POST /api/v1/pipeline/run"""
        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.post("/api/v1/pipeline/run")

            assert response.status_code == 200
            data = response.json()

            assert "execution_id" in data
            assert data["success"] is True
            assert "message" in data
            assert "estimated_duration" in data
            assert "started_at" in data

    def test_run_step_range_success(self, client, mock_orchestrator_service):
        """Test POST /api/v1/pipeline/run/steps/{start_step}-{end_step}"""
        mock_orchestrator_service.run_step_range.return_value = {
            "execution_id": "test-execution-id",
            "start_step": 1,
            "end_step": 3,
            "success": True,
            "completed_steps": [1, 2, 3],
            "failed_step": None,
            "execution_time": 120.5,
            "step_results": {}
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.post("/api/v1/pipeline/run/steps/1-3")

            assert response.status_code == 200
            data = response.json()

            assert data["start_step"] == 1
            assert data["end_step"] == 3
            assert data["success"] is True
            assert data["completed_steps"] == [1, 2, 3]

    def test_run_step_range_invalid_range(self, client, mock_orchestrator_service):
        """Test POST /api/v1/pipeline/run/steps/{start_step}-{end_step} with invalid range"""
        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.post("/api/v1/pipeline/run/steps/5-3")

            assert response.status_code == 400
            data = response.json()
            assert "Invalid step range" in data["detail"]

    def test_get_execution_status_success(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/runs/{execution_id}/status"""
        execution_id = "test-execution-id"
        mock_orchestrator_service.get_execution_status.return_value = {
            "execution_id": execution_id,
            "status": "running",
            "current_step": 5,
            "completed_steps": [1, 2, 3, 4],
            "failed_step": None,
            "start_time": "2024-01-01T12:00:00Z",
            "execution_time": 300.5,
            "progress_percentage": 45.5,
            "estimated_remaining_time": 600.0
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get(f"/api/v1/pipeline/runs/{execution_id}/status")

            assert response.status_code == 200
            data = response.json()

            assert data["execution_id"] == execution_id
            assert data["status"] == "running"
            assert data["current_step"] == 5
            assert data["progress_percentage"] == 45.5

    def test_get_execution_status_not_found(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/runs/{execution_id}/status with non-existent execution"""
        execution_id = "non-existent-id"
        mock_orchestrator_service.get_execution_status.return_value = {
            "execution_id": execution_id,
            "status": "not_found",
            "current_step": None,
            "completed_steps": [],
            "failed_step": None,
            "start_time": None,
            "execution_time": 0,
            "progress_percentage": 0,
            "estimated_remaining_time": None
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get(f"/api/v1/pipeline/runs/{execution_id}/status")

            assert response.status_code == 404
            data = response.json()
            assert f"Execution {execution_id} not found" in data["detail"]

    def test_get_execution_logs_success(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/runs/{execution_id}/logs"""
        execution_id = "test-execution-id"
        mock_orchestrator_service.get_execution_logs.return_value = {
            "execution_id": execution_id,
            "logs": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "execution_id": execution_id,
                    "step_number": 1,
                    "level": "INFO",
                    "message": "Starting Fetch Data",
                    "details": {}
                }
            ],
            "step_logs": {
                "1": [
                    {
                        "timestamp": "2024-01-01T12:00:00Z",
                        "message": "Starting Fetch Data"
                    }
                ]
            },
            "total_log_entries": 1
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get(f"/api/v1/pipeline/runs/{execution_id}/logs")

            assert response.status_code == 200
            data = response.json()

            assert data["execution_id"] == execution_id
            assert isinstance(data["logs"], list)
            assert data["total_log_entries"] == 1

    def test_get_execution_logs_with_step_filter(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/runs/{execution_id}/logs with step filter"""
        execution_id = "test-execution-id"
        mock_orchestrator_service.get_execution_logs.return_value = {
            "execution_id": execution_id,
            "logs": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "execution_id": execution_id,
                    "step_number": 1,
                    "level": "INFO",
                    "message": "Starting Fetch Data",
                    "details": {}
                }
            ],
            "step_logs": None,
            "total_log_entries": 1
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get(f"/api/v1/pipeline/runs/{execution_id}/logs?step_number=1")

            assert response.status_code == 200
            data = response.json()

            assert data["execution_id"] == execution_id
            assert data["step_logs"] is None  # When filtering by step

    def test_get_execution_results_success(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/runs/{execution_id}/results"""
        execution_id = "test-execution-id"
        mock_orchestrator_service.get_execution_results.return_value = {
            "execution_id": execution_id,
            "success": True,
            "created_files": {
                "1": ["data/files_exports/screener1.csv"],
                "2": ["data/universe.json"]
            },
            "file_summaries": {
                "data/universe.json": {
                    "file_path": "/absolute/path/data/universe.json",
                    "file_size": 150000,
                    "created_at": "2024-01-01T12:30:00Z",
                    "created_by_step": 2,
                    "file_type": "json"
                }
            },
            "step_summaries": {},
            "performance_metrics": {
                "total_execution_time": 120.5,
                "completed_steps": 2,
                "total_steps": 11
            }
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get(f"/api/v1/pipeline/runs/{execution_id}/results")

            assert response.status_code == 200
            data = response.json()

            assert data["execution_id"] == execution_id
            assert data["success"] is True
            assert isinstance(data["created_files"], dict)
            assert isinstance(data["file_summaries"], dict)

    def test_resume_failed_execution_success(self, client, mock_orchestrator_service):
        """Test POST /api/v1/pipeline/runs/{execution_id}/resume"""
        original_execution_id = "original-execution-id"
        new_execution_id = "new-execution-id"

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.post(f"/api/v1/pipeline/runs/{original_execution_id}/resume")

            assert response.status_code == 200
            data = response.json()

            assert data["original_execution_id"] == original_execution_id
            assert "execution_id" in data
            assert data["success"] is True
            assert "message" in data

    def test_get_pipeline_history_success(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/history"""
        mock_orchestrator_service.get_pipeline_history.return_value = {
            "executions": [
                {
                    "execution_id": "test-execution-1",
                    "execution_type": "full_pipeline",
                    "status": "completed",
                    "success": True,
                    "start_time": "2024-01-01T12:00:00Z",
                    "end_time": "2024-01-01T12:30:00Z",
                    "execution_time": 1800.0,
                    "completed_steps": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                    "failed_step": None,
                    "total_files_created": 5,
                    "is_resumed": False
                }
            ],
            "total_executions": 1,
            "filtered_count": 1,
            "status_filter": None
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get("/api/v1/pipeline/history")

            assert response.status_code == 200
            data = response.json()

            assert isinstance(data["executions"], list)
            assert data["total_executions"] == 1
            assert data["filtered_count"] == 1

    def test_get_pipeline_history_with_filters(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/history with query parameters"""
        mock_orchestrator_service.get_pipeline_history.return_value = {
            "executions": [],
            "total_executions": 0,
            "filtered_count": 0,
            "status_filter": "completed"
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get("/api/v1/pipeline/history?limit=10&status_filter=completed")

            assert response.status_code == 200
            data = response.json()

            assert data["status_filter"] == "completed"
            mock_orchestrator_service.get_pipeline_history.assert_called_with(10, "completed")

    def test_get_pipeline_history_invalid_limit(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/history with invalid limit"""
        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get("/api/v1/pipeline/history?limit=2000")

            assert response.status_code == 400
            data = response.json()
            assert "Limit must be between 1 and 1000" in data["detail"]

    def test_pipeline_health_check_healthy(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/health - healthy service"""
        mock_orchestrator_service.get_available_steps.return_value = {
            "steps": {i: {} for i in range(1, 12)},
            "total_steps": 11,
            "step_aliases": {}
        }

        mock_orchestrator_service.validate_pipeline_dependencies.return_value = {
            "valid": True,
            "checks": {},
            "missing_dependencies": [],
            "recommendations": []
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get("/api/v1/pipeline/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["service"] == "pipeline_orchestrator"
            assert data["available_steps"] == 11
            assert data["dependencies_valid"] is True

    def test_pipeline_health_check_unhealthy(self, client, mock_orchestrator_service):
        """Test GET /api/v1/pipeline/health - unhealthy service"""
        mock_orchestrator_service.get_available_steps.return_value = {
            "steps": {},
            "total_steps": 0,
            "step_aliases": {}
        }

        mock_orchestrator_service.validate_pipeline_dependencies.return_value = {
            "valid": False,
            "checks": {},
            "missing_dependencies": ["main_py_functions"],
            "recommendations": ["Fix main.py import path"]
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_orchestrator_service):
            response = client.get("/api/v1/pipeline/health")

            assert response.status_code == 503
            data = response.json()

            assert data["status"] == "unhealthy"
            assert data["service"] == "pipeline_orchestrator"
            assert data["available_steps"] == 0
            assert data["dependencies_valid"] is False


class TestPipelineAPICLICompatibility:
    """Test CLI compatibility aspects of the API"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_step_aliases_in_api_response(self, client):
        """Test that API returns correct step aliases matching CLI"""
        mock_service = AsyncMock()
        mock_service.get_available_steps.return_value = {
            "steps": {
                1: {"aliases": ["1", "step1", "fetch"]},
                4: {"aliases": ["4", "step4", "portfolio"]},
                11: {"aliases": ["11", "step11", "status"]}
            },
            "total_steps": 11,
            "step_aliases": {
                "1": 1, "step1": 1, "fetch": 1,
                "4": 4, "step4": 4, "portfolio": 4,
                "11": 11, "step11": 11, "status": 11
            }
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_service):
            response = client.get("/api/v1/pipeline/steps/available")

            assert response.status_code == 200
            data = response.json()

            # Test that CLI aliases are present
            assert data["step_aliases"]["fetch"] == 1
            assert data["step_aliases"]["portfolio"] == 4
            assert data["step_aliases"]["status"] == 11

    def test_api_mimics_cli_behavior(self, client):
        """Test that API endpoints mimic CLI commands"""
        mock_service = AsyncMock()

        # Test individual step execution (equivalent to `python main.py 1`)
        mock_service.run_individual_step.return_value = {
            "execution_id": "test-id",
            "step_number": 1,
            "step_name": "Fetch Data",
            "success": True,
            "execution_time": 45.0,
            "created_files": ["data/files_exports/screener1.csv"],
            "console_output": [
                "STEP 1: Fetching data from Uncle Stock API",
                "Step 1 complete - CSV files saved"
            ],
            "error_message": None
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_service):
            response = client.post("/api/v1/pipeline/run/step/1")

            assert response.status_code == 200
            data = response.json()

            # Should have same structure as CLI would produce
            assert data["step_name"] == "Fetch Data"
            assert data["success"] is True
            assert "CSV files saved" in " ".join(data["console_output"])

    def test_error_messages_match_cli_patterns(self, client):
        """Test that API error messages match CLI error patterns"""
        mock_service = AsyncMock()
        mock_service.run_individual_step.return_value = {
            "execution_id": "test-id",
            "step_number": 5,
            "step_name": "Update Currency",
            "success": False,
            "execution_time": 10.0,
            "created_files": [],
            "console_output": [],
            "error_message": "Step 5 failed - stopping pipeline"
        }

        with patch('backend.app.core.dependencies.get_pipeline_orchestrator_service', return_value=mock_service):
            response = client.post("/api/v1/pipeline/run/step/5")

            assert response.status_code == 200
            data = response.json()

            # Error message should match CLI pattern
            assert data["success"] is False
            assert "Step 5 failed" in data["error_message"]