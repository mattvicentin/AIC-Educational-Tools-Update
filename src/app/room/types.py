"""
Type definitions for room management.
Ensures type safety across all room-related modules.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from flask import Request

# Request/Response Types
@dataclass
class RoomCreationData:
    """Type-safe room creation data."""
    name: str
    description: Optional[str]
    goals: str
    group_size: Optional[str]
    template_type: Optional[str]
    
    @classmethod
    def from_request(cls, request: Request) -> 'RoomCreationData':
        """Create from Flask request with validation."""
        data = request.get_json(silent=True) or {}
        # Fallback to form data for standard form submissions
        if not data and request.form:
            data = request.form.to_dict()
        return cls(
            # Accept both legacy keys (room_name/room_description) and simple keys (name/description)
            name=(data.get('room_name') or data.get('name') or '').strip(),
            description=(data.get('room_description') or data.get('description') or '').strip(),
            goals=(data.get('goals') or '').strip(),
            group_size=(data.get('group_size') or '').strip() or None,
            template_type=(data.get('template_type') or data.get('template') or '').strip() or None
        )

@dataclass
class InvitationData:
    """Type-safe invitation data."""
    display_name: str
    can_create_chats: bool
    can_invite_members: bool

# Service Response Types
@dataclass
class RoomServiceResult:
    """Standardized service result."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    room_id: Optional[int] = None

# Template Types
TemplateType = str
GoalType = str
ModeKey = str

# Room Management Types
@dataclass
class RoomUpdateData:
    """Type-safe room update data."""
    name: Optional[str] = None
    description: Optional[str] = None
    goals: Optional[str] = None
    group_size: Optional[str] = None
    is_active: Optional[bool] = None

@dataclass
class RoomFilterData:
    """Type-safe room filtering data."""
    owner_id: Optional[int] = None
    is_active: Optional[bool] = None
    template_type: Optional[str] = None
    group_size: Optional[str] = None
    search_query: Optional[str] = None

# Template System Types
@dataclass
class TemplateInfo:
    """Template information structure."""
    id: str
    name: str
    description: str
    modes: Dict[str, Any]
    goals: List[str]
    is_active: bool = True

@dataclass
class ModeInfo:
    """Learning mode information structure."""
    key: str
    label: str
    prompt: str
    order: int
    is_active: bool = True

# Invitation System Types
@dataclass
class InvitationCreateData:
    """Type-safe invitation creation data."""
    room_id: int
    user_id: int
    display_name: str
    can_create_chats: bool = False
    can_invite_members: bool = False
    expires_at: Optional[datetime] = None

@dataclass
class InvitationResponse:
    """Type-safe invitation response data."""
    invitation_id: int
    room_id: int
    user_id: int
    status: str  # 'pending', 'accepted', 'declined', 'expired'
    created_at: datetime
    accepted_at: Optional[datetime] = None

# API Response Types
@dataclass
class ApiResponse:
    """Standardized API response."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

# Validation Types
@dataclass
class ValidationResult:
    """Type-safe validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

# Room Statistics Types
@dataclass
class RoomStats:
    """Room statistics data."""
    total_members: int
    active_members: int
    total_chats: int
    total_messages: int
    last_activity: Optional[datetime] = None
    created_at: datetime = None

# Search and Filter Types
@dataclass
class SearchFilters:
    """Search and filter parameters."""
    query: Optional[str] = None
    template_type: Optional[str] = None
    group_size: Optional[str] = None
    is_active: Optional[bool] = None
    owner_id: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = 50
    offset: int = 0

# Pagination Types
@dataclass
class PaginationInfo:
    """Pagination information."""
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool

@dataclass
class PaginatedResponse:
    """Paginated response wrapper."""
    data: List[Any]
    pagination: PaginationInfo
    filters: Optional[SearchFilters] = None

# Error Types
@dataclass
class RoomError:
    """Room-specific error information."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

# Type Aliases for Common Patterns
RoomId = int
UserId = int
ChatId = int
MessageId = int
InvitationId = int

# Dictionary Types
RoomDict = Dict[str, Any]
UserDict = Dict[str, Any]
ChatDict = Dict[str, Any]
MessageDict = Dict[str, Any]
TemplateDict = Dict[str, Any]

# List Types
RoomList = List[RoomDict]
UserList = List[UserDict]
ChatList = List[ChatDict]
MessageList = List[MessageDict]
TemplateList = List[TemplateDict]
