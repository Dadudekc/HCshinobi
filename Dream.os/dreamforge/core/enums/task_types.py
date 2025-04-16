from enum import Enum, auto

class TaskType(str, Enum):
    """Task types for inter-agent communication."""
    
    # Code Generation Tasks
    GENERATE_TESTS = "generate_tests"
    FIX_CODE = "fix_code"
    ANALYZE_FILE = "analyze_file"
    REFACTOR_CODE = "refactor_code"
    
    # File Operations
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    
    # Analysis Tasks
    CODE_REVIEW = "code_review"
    COMPLEXITY_ANALYSIS = "complexity_analysis"
    DEPENDENCY_CHECK = "dependency_check"
    
    # Integration Tasks
    CURSOR_COMMAND = "cursor_command"
    CHATGPT_RESPONSE = "chatgpt_response"
    RESULT_DELIVERY = "result_delivery"
    
    # System Tasks
    HEALTH_CHECK = "health_check"
    ERROR_REPORT = "error_report"
    STATUS_UPDATE = "status_update" 