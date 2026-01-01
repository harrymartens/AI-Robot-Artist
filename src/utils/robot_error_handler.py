"""
Robot Error Handler for XArm API errors.
Provides comprehensive error handling and recovery strategies.
"""

from typing import Dict, Optional, Tuple
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"           # Can be auto-recovered
    MEDIUM = "medium"     # Requires user intervention
    HIGH = "high"         # Requires manual intervention
    CRITICAL = "critical" # Requires technical support


class RecoveryAction(Enum):
    """Recovery actions for different errors."""
    AUTO_RETRY = "auto_retry"
    REDUCE_SPEED = "reduce_speed"
    RE_PLAN_PATH = "re_plan_path"
    MANUAL_INTERVENTION = "manual_intervention"
    RESTART_ROBOT = "restart_robot"
    CONTACT_SUPPORT = "contact_support"
    EMERGENCY_STOP = "emergency_stop"


class XArmErrorHandler:
    """
    Handles XArm robot errors with recovery strategies.
    """
    
    # Controller Error Code Map (from XArm documentation)
    CONTROLLER_ERROR_CODES = {
        1: {
            'title': 'Emergency Stop Button Pressed',
            'description': 'The Emergency Stop Button on the xArm Controller is pushed in to stop',
            'action': 'Please release the Emergency Stop Button, and then re-enable the robot',
            'severity': ErrorSeverity.HIGH,
            'recovery': RecoveryAction.MANUAL_INTERVENTION
        },
        2: {
            'title': 'Emergency IO Triggered',
            'description': 'The Emergency IO of the Control Box is triggered',
            'action': 'Please ground the 2 EIs of the Control Box, and then re-enable the robot',
            'severity': ErrorSeverity.HIGH,
            'recovery': RecoveryAction.MANUAL_INTERVENTION
        },
        3: {
            'title': 'Three-state Switch Emergency Stop',
            'description': 'The Emergency Stop Button of the Three-state Switch is pressed',
            'action': 'Please release the Emergency Stop Button of the Three-state Switch, and then re-enable the robot',
            'severity': ErrorSeverity.HIGH,
            'recovery': RecoveryAction.MANUAL_INTERVENTION
        },
        10: {
            'title': 'Servo Motor Error',
            'description': 'General servo motor error',
            'action': 'Check motor connections and restart robot',
            'severity': ErrorSeverity.MEDIUM,
            'recovery': RecoveryAction.RESTART_ROBOT
        },
        11: {'title': 'Servo Motor 1 Error', 'severity': ErrorSeverity.MEDIUM, 'recovery': RecoveryAction.RESTART_ROBOT},
        12: {'title': 'Servo Motor 2 Error', 'severity': ErrorSeverity.MEDIUM, 'recovery': RecoveryAction.RESTART_ROBOT},
        13: {'title': 'Servo Motor 3 Error', 'severity': ErrorSeverity.MEDIUM, 'recovery': RecoveryAction.RESTART_ROBOT},
        14: {'title': 'Servo Motor 4 Error', 'severity': ErrorSeverity.MEDIUM, 'recovery': RecoveryAction.RESTART_ROBOT},
        15: {'title': 'Servo Motor 5 Error', 'severity': ErrorSeverity.MEDIUM, 'recovery': RecoveryAction.RESTART_ROBOT},
        16: {'title': 'Servo Motor 6 Error', 'severity': ErrorSeverity.MEDIUM, 'recovery': RecoveryAction.RESTART_ROBOT},
        17: {'title': 'Servo Motor 7 Error', 'severity': ErrorSeverity.MEDIUM, 'recovery': RecoveryAction.RESTART_ROBOT},
        18: {
            'title': 'Force Torque Sensor Communication Error',
            'description': 'Force Torque Sensor Communication Error',
            'action': 'Please check whether the force torque sensor is installed',
            'severity': ErrorSeverity.MEDIUM,
            'recovery': RecoveryAction.MANUAL_INTERVENTION
        },
        19: {
            'title': 'End Effector Communication Error',
            'description': 'End Effector Communication Error',
            'action': 'Please check whether end effector is installed and the baud rate setting is correct',
            'severity': ErrorSeverity.MEDIUM,
            'recovery': RecoveryAction.MANUAL_INTERVENTION
        },
        21: {
            'title': 'Kinematic Error',
            'description': 'Kinematic Error - robot cannot reach the target position',
            'action': 'Please re-plan the path or adjust the target position',
            'severity': ErrorSeverity.LOW,
            'recovery': RecoveryAction.RE_PLAN_PATH
        },
        22: {
            'title': 'Self-Collision Error',
            'description': 'The robot is about to collide with itself',
            'action': 'Please re-plan the path. If the robot reports the self-collision error continually, please turn on the manual mode and drag the robotic back to the normal area',
            'severity': ErrorSeverity.MEDIUM,
            'recovery': RecoveryAction.RE_PLAN_PATH
        },
        23: {
            'title': 'Joints Angle Exceed Limit',
            'description': 'Joint angles are outside the allowed range',
            'action': 'Please go to the "Live Control" page and press the "INITIAL POSITION" button to let the robot go to the initial position',
            'severity': ErrorSeverity.MEDIUM,
            'recovery': RecoveryAction.MANUAL_INTERVENTION
        },
        24: {
            'title': 'Speed Exceeds Limit',
            'description': 'Movement speed is too high',
            'action': 'Please check if the xArm is out of working range, or reduce the speed and acceleration values',
            'severity': ErrorSeverity.LOW,
            'recovery': RecoveryAction.REDUCE_SPEED
        },
        25: {
            'title': 'Planning Error',
            'description': 'Path planning failed',
            'action': 'Please re-plan the path or reduce the speed',
            'severity': ErrorSeverity.LOW,
            'recovery': RecoveryAction.RE_PLAN_PATH
        },
        26: {
            'title': 'Linux RT Error',
            'description': 'Linux Real-Time system error',
            'action': 'Please contact technical support',
            'severity': ErrorSeverity.CRITICAL,
            'recovery': RecoveryAction.CONTACT_SUPPORT
        },
        27: {
            'title': 'Command Reply Error',
            'description': 'Command reply timeout or error',
            'action': 'Check connection and retry',
            'severity': ErrorSeverity.LOW,
            'recovery': RecoveryAction.AUTO_RETRY
        },
        35: {
            'title': 'Safety Boundary Limit',
            'description': 'The xArm reaches the safety boundary',
            'action': 'Please move the xArm to the safety boundary after turning on the Manual mode on the Live Control interface',
            'severity': ErrorSeverity.MEDIUM,
            'recovery': RecoveryAction.MANUAL_INTERVENTION
        },
        38: {
            'title': 'Abnormal Joint Angle',
            'description': 'Joint angles are in an abnormal state',
            'action': 'Please stop the xArm by pressing the Emergency Stop Button on the Control Box and then contact technical support',
            'severity': ErrorSeverity.CRITICAL,
            'recovery': RecoveryAction.EMERGENCY_STOP
        }
    }
    
    # Joint Error Code Map
    JOINT_ERROR_CODES = {
        21: {
            'title': 'Driver IC Initialization Error',
            'description': 'Driver IC initialization failed',
            'action': 'Please restart the xArm with the Emergency Stop Button on the xArm Controller. If multiple reboots are not working, please contact technical support',
            'severity': ErrorSeverity.HIGH,
            'recovery': RecoveryAction.RESTART_ROBOT
        }
    }
    
    def __init__(self):
        """Initialize the error handler."""
        self.error_history = []
        self.retry_count = {}
        self.max_retries = 3
    
    def handle_error(self, error_code: int, warn_code: int = 0, context: str = "") -> Tuple[bool, str, RecoveryAction]:
        """
        Handle a robot error and return recovery information.
        
        Args:
            error_code: The controller error code
            warn_code: The controller warning code
            context: Additional context about the error
            
        Returns:
            Tuple of (can_auto_recover, message, recovery_action)
        """
        if error_code == 0:
            return True, "No error", RecoveryAction.AUTO_RETRY
        
        # Get error info
        error_info = self.CONTROLLER_ERROR_CODES.get(error_code, {})
        if not error_info:
            error_info = self.JOINT_ERROR_CODES.get(error_code, {})
        
        if not error_info:
            # Unknown error
            return False, f"Unknown error code: {error_code}", RecoveryAction.CONTACT_SUPPORT
        
        # Log error
        self.error_history.append({
            'error_code': error_code,
            'warn_code': warn_code,
            'context': context,
            'timestamp': __import__('time').time()
        })
        
        # Get recovery action
        recovery_action = error_info.get('recovery', RecoveryAction.MANUAL_INTERVENTION)
        severity = error_info.get('severity', ErrorSeverity.MEDIUM)
        
        # Build message
        title = error_info.get('title', f'Error {error_code}')
        description = error_info.get('description', '')
        action = error_info.get('action', '')
        
        message = f"❌ {title}"
        if description:
            message += f"\n   Description: {description}"
        if action:
            message += f"\n   Action: {action}"
        if context:
            message += f"\n   Context: {context}"
        
        # Determine if we can auto-recover
        can_auto_recover = self._can_auto_recover(error_code, severity, recovery_action)
        
        return can_auto_recover, message, recovery_action
    
    def _can_auto_recover(self, error_code: int, severity: ErrorSeverity, recovery_action: RecoveryAction) -> bool:
        """Determine if the error can be automatically recovered."""
        if severity == ErrorSeverity.CRITICAL:
            return False
        
        if recovery_action in [RecoveryAction.AUTO_RETRY, RecoveryAction.REDUCE_SPEED, RecoveryAction.RE_PLAN_PATH]:
            # Check retry count
            retry_key = f"{error_code}_{recovery_action.value}"
            current_retries = self.retry_count.get(retry_key, 0)
            return current_retries < self.max_retries
        
        return False
    
    def increment_retry_count(self, error_code: int, recovery_action: RecoveryAction):
        """Increment the retry count for an error."""
        retry_key = f"{error_code}_{recovery_action.value}"
        self.retry_count[retry_key] = self.retry_count.get(retry_key, 0) + 1
    
    def reset_retry_count(self, error_code: int = None, recovery_action: RecoveryAction = None):
        """Reset retry counts."""
        if error_code is None and recovery_action is None:
            self.retry_count.clear()
        elif error_code is not None and recovery_action is not None:
            retry_key = f"{error_code}_{recovery_action.value}"
            self.retry_count.pop(retry_key, None)
    
    def get_error_summary(self) -> str:
        """Get a summary of recent errors."""
        if not self.error_history:
            return "No errors recorded"
        
        recent_errors = self.error_history[-5:]  # Last 5 errors
        summary = "Recent Errors:\n"
        
        for error in recent_errors:
            error_info = self.CONTROLLER_ERROR_CODES.get(error['error_code'], {})
            title = error_info.get('title', f'Error {error["error_code"]}')
            summary += f"  - {title} (Code: {error['error_code']})\n"
        
        return summary
