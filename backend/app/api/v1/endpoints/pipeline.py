"""
Pipeline Orchestration API Endpoints
Implements complete REST API for 11-step fintech pipeline execution
Following fintech best practices with 100% CLI compatibility
"""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging

from ....core.dependencies import get_pipeline_orchestrator_service
from ....core.exceptions import ValidationError
from ....models.schemas import (
    # Request models
    PipelineExecutionRequest,
    StepExecutionRequest,
    StepRangeExecutionRequest,
    ResumeExecutionRequest,
    PipelineHistoryRequest,
    PipelineLogsRequest,

    # Response models
    FullPipelineResponse,
    IndividualStepResponse,
    StepRangeResponse,
    ResumeExecutionResponse,
    AvailableStepsResponse,
    PipelineHistoryResponse,
    PipelineExecutionLogs,
    PipelineExecutionFiles,
    PipelineDependencyValidation
)
from ....models.errors import ErrorResponse

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline Orchestration"])


# Background task storage for async execution tracking
_background_executions = {}


async def execute_pipeline_in_background(
    orchestrator_service,
    execution_id: str,
    execution_type: str,
    **kwargs
):
    """Execute pipeline in background and store results"""
    try:
        if execution_type == "full_pipeline":
            result = await orchestrator_service.run_full_pipeline(execution_id)
        elif execution_type == "individual_step":
            result = await orchestrator_service.run_individual_step(
                kwargs["step_number"], execution_id
            )
        elif execution_type == "step_range":
            result = await orchestrator_service.run_step_range(
                kwargs["start_step"], kwargs["end_step"], execution_id
            )
        elif execution_type == "resume":
            result = await orchestrator_service.resume_failed_pipeline(
                kwargs["original_execution_id"], kwargs.get("from_step")
            )
        else:
            result = {"success": False, "error_message": f"Unknown execution type: {execution_type}"}

        _background_executions[execution_id] = result
        logger.info(f"Background execution {execution_id} completed: {result.get('success', False)}")

    except Exception as e:
        error_result = {
            "execution_id": execution_id,
            "success": False,
            "error_message": f"Background execution failed: {str(e)}"
        }
        _background_executions[execution_id] = error_result
        logger.error(f"Background execution {execution_id} failed: {e}")


@router.post(
    "/run",
    response_model=FullPipelineResponse,
    summary="Run Complete Pipeline",
    description="Execute complete 11-step fintech pipeline asynchronously",
    responses={
        200: {
            "description": "Pipeline execution started successfully",
            "content": {
                "application/json": {
                    "example": {
                        "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                        "success": True,
                        "message": "Full pipeline execution started",
                        "estimated_duration": 1800.0,
                        "started_at": "2024-01-01T12:00:00Z"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error starting pipeline",
            "model": ErrorResponse
        }
    }
)
async def run_full_pipeline(
    background_tasks: BackgroundTasks,
    request: PipelineExecutionRequest = PipelineExecutionRequest(),
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Execute complete 11-step pipeline asynchronously

    This endpoint replicates the behavior of `python main.py` with full CLI compatibility:
    1. Step 1: Fetch data from Uncle Stock API
    2. Step 2: Parse CSV files and create universe.json
    3. Step 3: Parse historical performance data
    4. Step 4: Optimize portfolio allocations
    5. Step 5: Update EUR exchange rates
    6. Step 6: Calculate final stock allocations
    7. Step 7: Calculate stock quantities from IBKR account
    8. Step 8: Search for stocks on IBKR
    9. Step 9: Generate rebalancing orders
    10. Step 10: Execute orders through IBKR API
    11. Step 11: Check order status and verify execution

    **Execution Model:**
    - Asynchronous background execution
    - Real-time status tracking via status endpoint
    - Fail-fast behavior: stops on first step failure
    - Complete file ecosystem creation matching CLI

    **Created Files:**
    - CSV files in data/files_exports/
    - universe.json with complete stock data and allocations
    - universe_with_ibkr.json with IBKR contract details
    - data/orders.json with rebalancing orders
    - Complete execution logs

    **Monitor Progress:**
    - Use GET /pipeline/runs/{execution_id}/status for real-time updates
    - Use GET /pipeline/runs/{execution_id}/logs for detailed logs
    """
    try:
        logger.info("Starting full pipeline execution")

        # Generate execution ID if not provided
        if not request.execution_id:
            import uuid
            request.execution_id = str(uuid.uuid4())

        # Add background task for async execution
        background_tasks.add_task(
            execute_pipeline_in_background,
            orchestrator_service,
            request.execution_id,
            "full_pipeline"
        )

        logger.info(f"Full pipeline execution queued: {request.execution_id}")

        return {
            "execution_id": request.execution_id,
            "success": True,
            "message": "Full pipeline execution started",
            "estimated_duration": 1800.0,  # 30 minutes estimated
            "started_at": "2024-01-01T12:00:00Z"  # Will be replaced with actual timestamp
        }

    except Exception as e:
        logger.error(f"Error starting full pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error starting pipeline execution"
        )


@router.post(
    "/run/step/{step_number}",
    response_model=IndividualStepResponse,
    summary="Run Individual Step",
    description="Execute single pipeline step",
    responses={
        200: {
            "description": "Step execution completed",
            "content": {
                "application/json": {
                    "example": {
                        "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                        "step_number": 1,
                        "step_name": "Fetch Data",
                        "success": True,
                        "execution_time": 45.2,
                        "created_files": ["data/files_exports/screener1.csv"],
                        "console_output": ["STEP 1: Fetching data from Uncle Stock API", "Step 1 complete"],
                        "error_message": None
                    }
                }
            }
        },
        400: {
            "description": "Invalid step number",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error during step execution",
            "model": ErrorResponse
        }
    }
)
async def run_individual_step(
    step_number: int,
    request: StepExecutionRequest = StepExecutionRequest(step_number=1),
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Execute single pipeline step

    This endpoint replicates the behavior of `python main.py [1-11]` with aliases support:

    **Available Steps:**
    - Step 1 (fetch): Fetch data from Uncle Stock API
    - Step 2 (parse): Parse CSV files and create universe.json
    - Step 3 (history): Parse historical performance data
    - Step 4 (portfolio): Optimize portfolio allocations
    - Step 5 (currency): Update EUR exchange rates
    - Step 6 (target): Calculate final stock allocations
    - Step 7 (qty): Calculate stock quantities from IBKR account
    - Step 8 (ibkr): Search for stocks on IBKR
    - Step 9 (rebalance): Generate rebalancing orders
    - Step 10 (execute): Execute orders through IBKR API
    - Step 11 (status): Check order status and verify execution

    **Execution Model:**
    - Synchronous execution for individual steps
    - Complete console output capture
    - File creation tracking
    - Error handling with detailed messages
    """
    try:
        if step_number < 1 or step_number > 11:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid step number: {step_number}. Must be 1-11."
            )

        logger.info(f"Starting individual step execution: step {step_number}")

        # Override step number in request
        request.step_number = step_number

        # Generate execution ID if not provided
        if not request.execution_id:
            import uuid
            request.execution_id = str(uuid.uuid4())

        # Execute step synchronously
        result = await orchestrator_service.run_individual_step(
            request.step_number,
            request.execution_id
        )

        logger.info(f"Step {step_number} execution completed: {result['success']}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing step {step_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error executing step {step_number}"
        )


@router.post(
    "/run/steps/{start_step}-{end_step}",
    response_model=StepRangeResponse,
    summary="Run Step Range",
    description="Execute range of pipeline steps with fail-fast behavior",
    responses={
        200: {
            "description": "Step range execution completed",
            "content": {
                "application/json": {
                    "example": {
                        "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                        "start_step": 1,
                        "end_step": 3,
                        "success": True,
                        "completed_steps": [1, 2, 3],
                        "failed_step": None,
                        "execution_time": 120.5,
                        "step_results": {
                            "1": {"success": True, "execution_time": 45.2},
                            "2": {"success": True, "execution_time": 30.1},
                            "3": {"success": True, "execution_time": 45.2}
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid step range",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error during step range execution",
            "model": ErrorResponse
        }
    }
)
async def run_step_range(
    start_step: int,
    end_step: int,
    background_tasks: BackgroundTasks,
    request: StepRangeExecutionRequest = StepRangeExecutionRequest(start_step=1, end_step=1),
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Execute range of pipeline steps with fail-fast behavior

    This endpoint allows running a subset of the pipeline steps sequentially.
    Useful for:
    - Partial pipeline execution (e.g., steps 1-5 for data preparation)
    - Recovery after fixing specific step issues
    - Development and testing of step sequences

    **Execution Model:**
    - Sequential execution with fail-fast behavior
    - Stops immediately on first step failure
    - Complete step result tracking
    - Background execution for longer ranges

    **Examples:**
    - `/run/steps/1-3`: Data fetching and parsing (steps 1-3)
    - `/run/steps/4-6`: Portfolio optimization through allocations (steps 4-6)
    - `/run/steps/9-11`: Order generation and execution (steps 9-11)
    """
    try:
        if start_step < 1 or end_step > 11 or start_step > end_step:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid step range: {start_step}-{end_step}. Steps must be 1-11 and start <= end."
            )

        logger.info(f"Starting step range execution: steps {start_step}-{end_step}")

        # Override step range in request
        request.start_step = start_step
        request.end_step = end_step

        # Generate execution ID if not provided
        if not request.execution_id:
            import uuid
            request.execution_id = str(uuid.uuid4())

        # For small ranges (3 steps or less), execute synchronously
        # For larger ranges, execute asynchronously
        step_count = end_step - start_step + 1

        if step_count <= 3:
            # Synchronous execution for small ranges
            result = await orchestrator_service.run_step_range(
                request.start_step,
                request.end_step,
                request.execution_id
            )
            logger.info(f"Step range {start_step}-{end_step} execution completed: {result['success']}")
            return result
        else:
            # Asynchronous execution for larger ranges
            background_tasks.add_task(
                execute_pipeline_in_background,
                orchestrator_service,
                request.execution_id,
                "step_range",
                start_step=request.start_step,
                end_step=request.end_step
            )

            return {
                "execution_id": request.execution_id,
                "start_step": start_step,
                "end_step": end_step,
                "success": True,
                "message": f"Step range {start_step}-{end_step} execution started in background",
                "execution_time": 0.0,
                "step_results": {}
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing step range {start_step}-{end_step}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error executing step range {start_step}-{end_step}"
        )


@router.get(
    "/runs/{execution_id}/status",
    summary="Get Execution Status",
    description="Get real-time status of running or completed pipeline execution",
    responses={
        200: {
            "description": "Execution status retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "running",
                        "current_step": 5,
                        "completed_steps": [1, 2, 3, 4],
                        "failed_step": None,
                        "start_time": "2024-01-01T12:00:00Z",
                        "execution_time": 300.5,
                        "progress_percentage": 45.5,
                        "estimated_remaining_time": 600.0
                    }
                }
            }
        },
        404: {
            "description": "Execution not found",
            "model": ErrorResponse
        }
    }
)
async def get_execution_status(
    execution_id: str,
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Get real-time status of pipeline execution

    Provides complete execution status including:
    - Current execution status (pending, running, completed, failed)
    - Currently executing step (if running)
    - List of completed steps
    - Failed step number (if applicable)
    - Execution timing and progress information
    - Estimated remaining time for running executions

    **Status Values:**
    - `pending`: Execution queued but not started
    - `running`: Execution in progress
    - `completed`: Execution finished successfully
    - `failed`: Execution stopped due to step failure
    - `not_found`: Execution ID not found
    """
    try:
        logger.info(f"Getting execution status for: {execution_id}")

        status_info = await orchestrator_service.get_execution_status(execution_id)

        if status_info["status"] == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found"
            )

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status for {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving execution status"
        )


@router.get(
    "/runs/{execution_id}/logs",
    response_model=PipelineExecutionLogs,
    summary="Get Execution Logs",
    description="Get structured execution logs for pipeline run",
    responses={
        200: {
            "description": "Execution logs retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                        "logs": [
                            {
                                "timestamp": "2024-01-01T12:00:00Z",
                                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                                "step_number": 1,
                                "level": "INFO",
                                "message": "Starting Fetch Data",
                                "details": {}
                            }
                        ],
                        "step_logs": {
                            "1": [{"timestamp": "2024-01-01T12:00:00Z", "message": "Starting Fetch Data"}]
                        },
                        "total_log_entries": 1
                    }
                }
            }
        },
        404: {
            "description": "Execution not found",
            "model": ErrorResponse
        }
    }
)
async def get_execution_logs(
    execution_id: str,
    step_number: Optional[int] = None,
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Get structured execution logs for pipeline run

    Returns detailed logs from pipeline execution including:
    - Chronological log entries with timestamps
    - Log entries grouped by step (if step_number not specified)
    - Different log levels (INFO, WARNING, ERROR)
    - Detailed information for debugging and auditing

    **Parameters:**
    - `step_number`: Optional filter to get logs for specific step only
    - If not specified, returns all logs grouped by step

    **Log Levels:**
    - `INFO`: General information about pipeline progress
    - `WARNING`: Non-critical issues that don't stop execution
    - `ERROR`: Critical errors that cause step or pipeline failure

    **Use Cases:**
    - Debugging failed executions
    - Monitoring pipeline progress
    - Audit trail for compliance
    - Performance analysis
    """
    try:
        logger.info(f"Getting execution logs for: {execution_id}")

        logs_info = await orchestrator_service.get_execution_logs(execution_id, step_number)

        return logs_info

    except Exception as e:
        logger.error(f"Error getting execution logs for {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving execution logs"
        )


@router.get(
    "/runs/{execution_id}/results",
    response_model=PipelineExecutionFiles,
    summary="Get Execution Results",
    description="Get detailed execution results and created files",
    responses={
        200: {
            "description": "Execution results retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                        "created_files": {
                            "1": ["data/files_exports/screener1.csv", "data/files_exports/screener2.csv"],
                            "2": ["data/universe.json"],
                            "8": ["data/universe_with_ibkr.json"],
                            "9": ["data/orders.json"]
                        },
                        "file_info": {
                            "data/universe.json": {
                                "file_path": "/absolute/path/data/universe.json",
                                "file_size": 150000,
                                "created_at": "2024-01-01T12:30:00Z",
                                "created_by_step": 2,
                                "file_type": "json"
                            }
                        },
                        "total_files_created": 5,
                        "total_file_size": 500000
                    }
                }
            }
        },
        404: {
            "description": "Execution not found",
            "model": ErrorResponse
        }
    }
)
async def get_execution_results(
    execution_id: str,
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Get detailed execution results and created files

    Provides comprehensive information about pipeline execution results:
    - Files created by each step
    - File metadata (size, timestamps, type)
    - Step execution summaries
    - Performance metrics

    **File Information Includes:**
    - Absolute file paths
    - File sizes in bytes
    - Creation and modification timestamps
    - Which step created each file
    - File type classification

    **Use Cases:**
    - Verifying pipeline output
    - File management and cleanup
    - Performance monitoring
    - Integration with downstream systems
    """
    try:
        logger.info(f"Getting execution results for: {execution_id}")

        results = await orchestrator_service.get_execution_results(execution_id)

        return results

    except Exception as e:
        logger.error(f"Error getting execution results for {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving execution results"
        )


@router.post(
    "/runs/{execution_id}/resume",
    response_model=ResumeExecutionResponse,
    summary="Resume Failed Execution",
    description="Resume failed pipeline execution from specified step",
    responses={
        200: {
            "description": "Pipeline resume started successfully",
            "content": {
                "application/json": {
                    "example": {
                        "execution_id": "new-execution-id-here",
                        "original_execution_id": "550e8400-e29b-41d4-a716-446655440000",
                        "resumed_from_step": 8,
                        "success": True,
                        "message": "Pipeline resumed from step 8"
                    }
                }
            }
        },
        404: {
            "description": "Original execution not found",
            "model": ErrorResponse
        },
        400: {
            "description": "Invalid resume parameters",
            "model": ErrorResponse
        }
    }
)
async def resume_failed_execution(
    execution_id: str,
    background_tasks: BackgroundTasks,
    request: ResumeExecutionRequest = ResumeExecutionRequest(execution_id=""),
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Resume failed pipeline execution from specified step

    This endpoint allows resuming a failed pipeline execution from a specific step,
    useful for:
    - Recovering from transient failures (network issues, API timeouts)
    - Continuing after fixing data or configuration issues
    - Selective re-execution of failed steps

    **Resume Logic:**
    - If `from_step` not specified: auto-detects failed step or continues from last completed
    - Creates new execution ID for the resumed run
    - Maintains link to original execution for audit trail
    - Executes remaining steps with fail-fast behavior

    **Auto-Detection:**
    - If original execution failed at step N: resumes from step N
    - If original execution completed some steps: resumes from next step after last completed
    - If resume step > 11: returns error

    **Use Cases:**
    - Network connectivity issues during IBKR steps (steps 7, 8, 10, 11)
    - External API timeouts (steps 1, 5)
    - Data processing issues after manual fixes
    """
    try:
        logger.info(f"Resuming execution: {execution_id}")

        # Override execution ID in request
        request.execution_id = execution_id

        # Add background task for async resume
        import uuid
        new_execution_id = str(uuid.uuid4())

        background_tasks.add_task(
            execute_pipeline_in_background,
            orchestrator_service,
            new_execution_id,
            "resume",
            original_execution_id=execution_id,
            from_step=request.from_step
        )

        return {
            "execution_id": new_execution_id,
            "original_execution_id": execution_id,
            "resumed_from_step": request.from_step or 0,  # 0 indicates auto-detection
            "success": True,
            "message": f"Pipeline resume started from {'auto-detected step' if not request.from_step else f'step {request.from_step}'}"
        }

    except Exception as e:
        logger.error(f"Error resuming execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error resuming execution"
        )


@router.get(
    "/history",
    response_model=PipelineHistoryResponse,
    summary="Get Pipeline History",
    description="Get history of pipeline executions with filtering",
    responses={
        200: {
            "description": "Pipeline execution history retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "executions": [
                            {
                                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
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
                }
            }
        }
    }
)
async def get_pipeline_history(
    limit: int = 50,
    status_filter: Optional[str] = None,
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Get history of pipeline executions

    Provides paginated history of pipeline executions with optional filtering:
    - Recent executions first (sorted by start_time descending)
    - Configurable limit (default 50, max 1000)
    - Optional status filtering

    **Status Filter Values:**
    - `completed`: Successfully completed executions
    - `failed`: Failed executions
    - `running`: Currently running executions
    - `pending`: Queued executions

    **Execution Information:**
    - Execution metadata (ID, type, timing)
    - Success/failure status
    - Completed and failed steps
    - File creation counts
    - Resume relationship information

    **Use Cases:**
    - Monitoring pipeline usage
    - Debugging execution patterns
    - Performance analysis
    - Audit trail maintenance
    """
    try:
        logger.info(f"Getting pipeline history (limit: {limit}, filter: {status_filter})")

        # Validate limit
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 1000"
            )

        history = await orchestrator_service.get_pipeline_history(limit, status_filter)

        logger.info(f"Retrieved {len(history['executions'])} executions from history")

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pipeline history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving pipeline history"
        )


@router.get(
    "/steps/available",
    response_model=AvailableStepsResponse,
    summary="Get Available Steps",
    description="Get list of all available pipeline steps with descriptions and aliases",
    responses={
        200: {
            "description": "Available steps retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "steps": {
                            "1": {
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
                }
            }
        }
    }
)
async def get_available_steps(
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Get list of all available pipeline steps

    Provides comprehensive information about all pipeline steps:
    - Step numbers, names, and descriptions
    - CLI aliases for each step
    - Step dependencies
    - Files created and modified by each step

    **Step Information Includes:**
    - Human-readable names and descriptions
    - CLI compatibility aliases (e.g., "fetch", "parse", "portfolio")
    - Dependency relationships between steps
    - File I/O information for each step

    **CLI Alias Examples:**
    - Step 1: `1`, `step1`, `fetch`
    - Step 2: `2`, `step2`, `parse`
    - Step 4: `4`, `step4`, `portfolio`
    - Step 8: `8`, `step8`, `ibkr`

    **Use Cases:**
    - Frontend step selection interfaces
    - CLI help documentation
    - Step dependency validation
    - Pipeline planning and sequencing
    """
    try:
        logger.info("Getting available pipeline steps")

        steps_info = orchestrator_service.get_available_steps()

        return steps_info

    except Exception as e:
        logger.error(f"Error getting available steps: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving available steps"
        )


@router.get(
    "/dependencies/validate",
    response_model=PipelineDependencyValidation,
    summary="Validate Pipeline Dependencies",
    description="Validate that all pipeline dependencies and prerequisites are met",
    responses={
        200: {
            "description": "Dependency validation completed",
            "content": {
                "application/json": {
                    "example": {
                        "valid": True,
                        "checks": {
                            "main_py_functions": {
                                "name": "main_py_functions",
                                "type": "code",
                                "required": True,
                                "valid": True,
                                "details": "All step functions from main.py are accessible"
                            },
                            "data_directory": {
                                "name": "data_directory",
                                "type": "file",
                                "required": True,
                                "valid": True,
                                "details": "Data directory exists and is accessible"
                            }
                        },
                        "missing_dependencies": [],
                        "recommendations": [],
                        "checked_at": "2024-01-01T12:00:00Z"
                    }
                }
            }
        }
    }
)
async def validate_dependencies(
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Validate pipeline dependencies and prerequisites

    Performs comprehensive validation of all pipeline requirements:
    - Code dependencies (main.py step functions)
    - File system requirements (data directory, write permissions)
    - Service connectivity (where applicable)

    **Dependency Categories:**
    - `code`: Python modules and functions
    - `file`: Directories and file permissions
    - `service`: External service connectivity
    - `configuration`: Required configuration values

    **Validation Results:**
    - Individual dependency check results
    - Overall validation status
    - Missing dependencies list
    - Actionable recommendations for fixes

    **Use Cases:**
    - Pre-execution validation
    - Environment setup verification
    - Troubleshooting pipeline failures
    - System health monitoring

    **Recommendations Include:**
    - Commands to fix missing dependencies
    - Configuration changes needed
    - File system setup instructions
    """
    try:
        logger.info("Validating pipeline dependencies")

        validation_result = await orchestrator_service.validate_pipeline_dependencies()

        logger.info(f"Dependency validation completed: {validation_result['valid']}")

        return validation_result

    except Exception as e:
        logger.error(f"Error validating dependencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during dependency validation"
        )


# Health check endpoint
@router.get(
    "/health",
    summary="Pipeline Service Health Check",
    description="Check if pipeline orchestration service is operational"
)
async def pipeline_health_check(
    orchestrator_service = Depends(get_pipeline_orchestrator_service)
):
    """
    Health check for pipeline orchestration service

    Verifies:
    - Service initialization and basic functionality
    - Access to step functions
    - Basic dependency availability

    **Health Status:**
    - `healthy`: Service is operational and ready for pipeline execution
    - `unhealthy`: Service has issues that prevent pipeline execution

    **Additional Information:**
    - Service version and build information
    - Basic capability checks
    - Last successful execution information (if any)
    """
    try:
        # Test basic service functionality
        steps_info = orchestrator_service.get_available_steps()
        dependency_validation = await orchestrator_service.validate_pipeline_dependencies()

        # Determine health status
        is_healthy = dependency_validation["valid"] and len(steps_info["steps"]) == 11

        if is_healthy:
            return {
                "status": "healthy",
                "service": "pipeline_orchestrator",
                "available_steps": len(steps_info["steps"]),
                "dependencies_valid": dependency_validation["valid"],
                "timestamp": "2024-01-01T00:00:00Z",  # Will be replaced with actual timestamp
                "version": "1.0.0"
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "service": "pipeline_orchestrator",
                    "available_steps": len(steps_info["steps"]),
                    "dependencies_valid": dependency_validation["valid"],
                    "missing_dependencies": dependency_validation["missing_dependencies"],
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            )

    except Exception as e:
        logger.error(f"Pipeline health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "pipeline_orchestrator",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )