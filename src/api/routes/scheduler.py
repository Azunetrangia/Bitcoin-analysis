"""
Scheduler API Routes.

Endpoints for managing scheduler and triggering pipelines.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from src.api.dependencies import get_scheduler_service, get_orchestrator
from src.api.models import (
    SchedulerStatusResponse,
    JobStatus,
    PipelineResultResponse
)
from src.application.services.scheduler_service import SchedulerService
from src.application.services.pipeline_orchestrator import PipelineOrchestrator

router = APIRouter()


# ============================================================================
# SCHEDULER MANAGEMENT
# ============================================================================

@router.get(
    "/status",
    response_model=SchedulerStatusResponse,
    summary="Get scheduler status",
    description="Get current scheduler and job status"
)
async def get_scheduler_status(
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
):
    """
    Get scheduler status.
    
    Returns scheduler running state and all job information.
    
    ## Returns
    - Scheduler running status
    - List of all jobs with their states and next run times
    """
    try:
        status = scheduler_service.get_scheduler_status()
        
        jobs = [
            JobStatus(
                job_id=job["job_id"],
                name=job["name"],
                next_run=job.get("next_run"),
                trigger=job.get("trigger", "unknown")
            )
            for job in status.get("jobs", [])
        ]
        
        return SchedulerStatusResponse(
            running=status.get("running", False),
            jobs_count=len(jobs),
            timezone=status.get("timezone", "UTC"),
            jobs=jobs
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post(
    "/start",
    summary="Start scheduler",
    description="Start the scheduler with all configured jobs"
)
async def start_scheduler(
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
):
    """
    Start scheduler.
    
    Initializes and starts the scheduler with all jobs from config.
    
    ## Returns
    Confirmation message with job count.
    """
    try:
        scheduler_service.start()
        status = scheduler_service.get_scheduler_status()
        
        return {
            "message": "Scheduler started successfully",
            "running": True,
            "jobs_count": len(status.get("jobs", []))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Start failed: {str(e)}")


@router.post(
    "/stop",
    summary="Stop scheduler",
    description="Stop the scheduler and all running jobs"
)
async def stop_scheduler(
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
):
    """
    Stop scheduler.
    
    Shuts down the scheduler gracefully.
    
    ## Returns
    Confirmation message.
    """
    try:
        scheduler_service.stop()
        
        return {
            "message": "Scheduler stopped successfully",
            "running": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stop failed: {str(e)}")


@router.post(
    "/trigger/{job_id}",
    summary="Trigger a job",
    description="Manually trigger a specific job to run immediately"
)
async def trigger_job(
    job_id: str = Path(..., description="Job ID to trigger"),
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
):
    """
    Trigger a job manually.
    
    Runs the specified job immediately, outside of its regular schedule.
    
    ## Parameters
    - **job_id**: The ID of the job to trigger
    
    ## Returns
    Execution confirmation.
    """
    try:
        scheduler_service.trigger_job(job_id)
        
        return {
            "message": f"Job {job_id} triggered successfully",
            "job_id": job_id
        }
        
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trigger failed: {str(e)}")


# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

@router.post(
    "/pipeline/update",
    response_model=PipelineResultResponse,
    summary="Run incremental update",
    description="Run incremental data update pipeline"
)
async def run_incremental_update(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="1h"),
    limit: int = Query(default=2, ge=1, le=100),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator)
):
    """
    Run incremental update pipeline.
    
    Downloads latest candles and updates storage.
    
    ## Parameters
    - **symbol**: Trading pair
    - **interval**: Timeframe
    - **limit**: Number of recent candles to fetch
    
    ## Returns
    Pipeline execution result with metrics.
    """
    try:
        result = orchestrator.run_incremental_update(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        return _format_pipeline_result(result, "incremental_update")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.post(
    "/pipeline/backfill",
    response_model=PipelineResultResponse,
    summary="Run historical backfill",
    description="Run historical data backfill pipeline"
)
async def run_historical_backfill(
    symbol: str = Query(default="BTCUSDT"),
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
    interval: str = Query(default="1h"),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator)
):
    """
    Run historical backfill pipeline.
    
    Downloads historical data for a date range.
    
    ## Parameters
    - **symbol**: Trading pair
    - **start**: Start date (YYYY-MM-DD)
    - **end**: End date (YYYY-MM-DD)
    - **interval**: Timeframe
    
    ## Returns
    Pipeline execution result with metrics.
    """
    try:
        # Parse dates
        from datetime import datetime
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        
        result = orchestrator.run_historical_backfill(
            symbol=symbol,
            start=start_dt,
            end=end_dt,
            interval=interval
        )
        
        return _format_pipeline_result(result, "historical_backfill")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.post(
    "/pipeline/retrain",
    response_model=PipelineResultResponse,
    summary="Run model retraining",
    description="Run regime classifier retraining pipeline"
)
async def run_model_retraining(
    symbol: str = Query(default="BTCUSDT"),
    start: str = Query(..., description="Training start date (YYYY-MM-DD)"),
    end: str = Query(..., description="Training end date (YYYY-MM-DD)"),
    interval: str = Query(default="1h"),
    n_states: int = Query(default=4, ge=2, le=10),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator)
):
    """
    Run model retraining pipeline.
    
    Retrains the regime classifier on specified date range.
    
    ## Parameters
    - **symbol**: Trading pair
    - **start**: Training start date (YYYY-MM-DD)
    - **end**: Training end date (YYYY-MM-DD)
    - **interval**: Timeframe
    - **n_states**: Number of HMM states (2-10)
    
    ## Returns
    Pipeline execution result with model metrics.
    """
    try:
        # Parse dates
        from datetime import datetime
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        
        result = orchestrator.run_model_retraining(
            symbol=symbol,
            start=start_dt,
            end=end_dt,
            interval=interval,
            n_states=n_states
        )
        
        return _format_pipeline_result(result, "model_retraining")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.post(
    "/pipeline/full-update",
    response_model=PipelineResultResponse,
    summary="Run full update pipeline",
    description="Run complete update pipeline (data + analysis + regime)"
)
async def run_full_update(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="1h"),
    limit: int = Query(default=2, ge=1, le=100),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator)
):
    """
    Run full update pipeline.
    
    Executes complete pipeline:
    1. Download latest data
    2. Calculate technical indicators
    3. Classify market regimes
    4. Calculate risk metrics
    
    ## Parameters
    - **symbol**: Trading pair
    - **interval**: Timeframe
    - **limit**: Number of recent candles to fetch
    
    ## Returns
    Pipeline execution result with all metrics.
    """
    try:
        result = orchestrator.run_full_update_pipeline(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        return _format_pipeline_result(result, "full_update")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_pipeline_result(result: Dict[str, Any], pipeline_type: str) -> PipelineResultResponse:
    """Format pipeline result into response model."""
    return PipelineResultResponse(
        pipeline_type=pipeline_type,
        success=result.get("success", False),
        message=result.get("message", ""),
        duration_seconds=result.get("duration", 0.0),
        steps_completed=result.get("steps_completed", []),
        metrics=result.get("metrics", {})
    )
