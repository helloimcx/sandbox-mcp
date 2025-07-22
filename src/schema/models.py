"""Data models for the sandbox MCP server."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class MessageType(str, Enum):
    """Message type enumeration."""
    STREAM = "stream"
    DISPLAY_DATA = "display_data"
    ERROR = "error"
    STATUS = "status"
    EXECUTE_RESULT = "execute_result"
    EXECUTE_INPUT = "execute_input"


class ExecuteRequest(BaseModel):
    """Request model for code execution."""
    code: str = Field(..., description="Python code to execute")
    session_id: Optional[str] = Field(None, description="Session ID for kernel reuse")
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds")
    variables: Optional[Dict[str, Any]] = Field(None, description="Variables to inject")


class CreateSessionRequest(BaseModel):
    """Request model for creating session with file downloads."""
    session_id: Optional[str] = Field(None, description="Optional session ID")
    file_urls: Optional[List[str]] = Field(None, description="List of file URLs to download")
    timeout: Optional[int] = Field(30, description="Download timeout in seconds")


class CreateSessionResponse(BaseModel):
    """Response model for session creation."""
    session_id: str = Field(..., description="Created session ID")
    working_directory: str = Field(..., description="Session working directory")
    downloaded_files: List[str] = Field(default_factory=list, description="List of downloaded file names")
    errors: List[str] = Field(default_factory=list, description="Download errors if any")


class StreamMessage(BaseModel):
    """Stream message model."""
    type: MessageType
    content: Dict[str, Any]
    timestamp: float
    execution_count: Optional[int] = None


class TextOutput(BaseModel):
    """Text output model."""
    text: str


class ImageOutput(BaseModel):
    """Image output model."""
    image: str  # base64 encoded
    format: str = "png"


class ErrorOutput(BaseModel):
    """Error output model."""
    error: str
    traceback: List[str]


class ExecutionResult(BaseModel):
    """Execution result model."""
    status: ExecutionStatus
    execution_count: int
    outputs: List[Dict[str, Any]]
    execution_time: float
    error: Optional[str] = None


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    kernel_id: str
    created_at: float
    last_activity: float
    status: str


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str
    active_sessions: int
    uptime: float


class ApiResponse(BaseModel):
    resultCode: int = 0
    resultMsg: str = "success"
    data: Optional[Any] = None


class ExecuteSyncResponse(BaseModel):
    texts: List[str] = []
    images: List[str] = []
    errors: List[Dict[str, Any]] = []