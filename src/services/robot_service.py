import numpy as np
from numpy.typing import NDArray
from xarm.wrapper import XArmAPI
import time

from config.config import Config
from core.models import AttachmentType, SpeedType, RobotState
from utils.robot_error_handler import XArmErrorHandler, RecoveryAction

class RobotService:
    def __init__(self, config: Config):
        self.config = config
        self.arm = None
        self.error_handler = XArmErrorHandler()
        self._connect()

    def _connect(self):
        """
        Establish a connection to the robot.
        """
        self.arm = XArmAPI(self.config.robot.ip)
        self.arm.clean_warn()
        self.arm.clean_error()
        self.arm.motion_enable(True)
        self.arm.set_state(0)
        self.move_centred_position(SpeedType.SLOW)
    
    def _check_and_handle_errors(self, context: str = "") -> bool:
        """
        Check for robot errors and handle them automatically if possible.
        
        Args:
            context: Context about what operation was being performed
            
        Returns:
            True if no errors or errors were handled, False if manual intervention needed
        """
        if self.arm is None:
            return False
            
        # Get error codes
        error_code = self.arm.error_code
        warn_code = self.arm.warn_code
        
        if error_code == 0:
            return True
        
        # Handle the error
        can_auto_recover, message, recovery_action = self.error_handler.handle_error(
            error_code, warn_code, context
        )
        
        print(message)
        
        if not can_auto_recover:
            print("⚠️  Manual intervention required. Please address the issue and restart the robot.")
            return False
        
        # Try to auto-recover
        return self._attempt_recovery(recovery_action, error_code, context)
    
    
    ###REVIEW###
    def _attempt_recovery(self, recovery_action: RecoveryAction, error_code: int, context: str) -> bool:
        """
        Attempt to recover from an error automatically.
        
        Args:
            recovery_action: The recovery action to attempt
            error_code: The error code that occurred
            context: Context about the error
            
        Returns:
            True if recovery was successful, False otherwise
        """
        print(f"🔄 Attempting automatic recovery: {recovery_action.value}")
        
        try:
            if recovery_action == RecoveryAction.AUTO_RETRY:
                # Simple retry - just clean errors and continue
                self.arm.clean_error()
                self.arm.clean_warn()
                time.sleep(1)
                
            elif recovery_action == RecoveryAction.REDUCE_SPEED:
                # Reduce speed and retry
                print("📉 Reducing robot speed and retrying...")
                self.arm.clean_error()
                self.arm.clean_warn()
                time.sleep(1)
                
            elif recovery_action == RecoveryAction.RE_PLAN_PATH:
                # For kinematic errors, try moving to rest position first
                print("🔄 Re-planning path - moving to rest position...")
                self.arm.clean_error()
                self.arm.clean_warn()
                time.sleep(1)
                # Move to rest position to get out of problematic position
                self.move_centred_position(SpeedType.SLOW)
                
            elif recovery_action == RecoveryAction.RESTART_ROBOT:
                # Restart the robot connection
                print("🔄 Restarting robot connection...")
                self.arm.clean_error()
                self.arm.clean_warn()
                self.arm.motion_enable(True)
                self.arm.set_state(0)
                time.sleep(2)
                
            else:
                print(f"❌ Cannot auto-recover from {recovery_action.value}")
                return False
            
            # Increment retry count
            self.error_handler.increment_retry_count(error_code, recovery_action)
            
            # Check if recovery was successful
            if self.arm.error_code == 0:
                print("✅ Recovery successful!")
                return True
            else:
                print("❌ Recovery failed, error still present")
                return False
                
        except Exception as e:
            print(f"❌ Error during recovery attempt: {e}")
            return False
    
    def get_error_summary(self) -> str:
        """Get a summary of recent robot errors."""
        return self.error_handler.get_error_summary()
        
    def change_attachment(self, attachment: AttachmentType):
        """
        Change the robot's attachment.
        """
        self.config.robot.set_attachment(attachment)
        
    def get_attachment(self) -> AttachmentType:
        """
        Get the robot's current attachment.
        """
        return self.config.robot.current_attachment
        
    def set_robot_state(self, state: RobotState):
        """
        Set the robot's current state.
        """
        self.config.robot.current_state = state
        
    def get_robot_state(self) -> RobotState:
        """
        Check the current state of the robot.
        """
        return self.config.robot.current_state
        
    def move_canvas_position(self, _x:float, _y:float, _z:float = None,
                             raised:bool = True, 
                             speed: SpeedType = SpeedType.NORMAL, 
                             roll: float = None, 
                             pitch: float = None, 
                             yaw: float = None,
                             wait:bool = False) -> int:
        """
        Move the robot to a specified position on the canvas.
        """
        
        if (_z is None):
            _z = self.config.robot.z_raised if raised else self.config.robot.z_lowered
        
        if roll is None:
            roll = self.config.robot.roll
        if pitch is None:
            pitch = self.config.robot.pitch
        if yaw is None:
            yaw = self.config.robot.yaw
            
        if self.get_robot_state() == RobotState.UNKNOWN:
            self.set_robot_state(RobotState.CALCULATING)
            self.move_centred_position()
            
        elif self.get_robot_state() == RobotState.DOCKED:
            self.move_centred_position(speed=SpeedType.SLOW)
            
        self.set_robot_state(RobotState.MOVING)
        
        # Check for errors before movement
        if not self._check_and_handle_errors(f"move_canvas_position to ({_x}, {_y}, {_z})"):
            return -1
        
        ret = self.arm.set_position(x=_x, 
                                    y=_y, 
                                    z=_z,
                                    roll = roll,
                                    pitch = pitch,
                                    yaw = yaw,
                                    speed = self.config.robot.get_speed(speed), 
                                    mvacc = self.config.robot.mvacc,
                                    wait = wait
                                    )
        
        self.set_robot_state(RobotState.PAUSED)

        if ret == 0:
            return ret
        else:
            print(f"[ERROR] set_position failed, code: {ret}")
            print(f"Error code: {self.arm.error_code}, Warning code: {self.arm.warn_code}")
            
            # Try to handle the error
            if not self._check_and_handle_errors(f"set_position failed with code {ret}"):
                return ret
            
            # If error was handled, try the movement again
            print("🔄 Retrying movement after error recovery...")
            ret = self.arm.set_position(x=_x, 
                                        y=_y, 
                                        z=_z,
                                        roll = roll,
                                        pitch = pitch,
                                        yaw = yaw,
                                        speed = self.config.robot.get_speed(speed), 
                                        mvacc = self.config.robot.mvacc,
                                        wait = wait
                                        )
            return ret
            
    def move_centred_position(self, speed: SpeedType = SpeedType.NORMAL):
        """
        Move the robot to the centre of the canvas.
        """
        self.move_canvas_position(_x=self.config.robot.centred_position['x'], _y=self.config.robot.centred_position['y'], speed=speed)
        
        self.set_robot_state(RobotState.CENTRED)

                
    def move_change_tool_position(self, speed: SpeedType = SpeedType.NORMAL):
        """
        Move the robot to its position to change the tool.
        """
        self.move_canvas_position(_x=self.config.robot.change_tool_position["x"], _y=self.config.robot.change_tool_position["y"], _z=self.config.robot.change_tool_position["z"], speed=speed)
        
        self.set_robot_state(RobotState.TOOL_CHANGE)
        
        
    def move_docked_position(self, speed: SpeedType = SpeedType.NORMAL):
        """
        Move the robot to its hidden position, away from camera.
        """
        if self.config.robot.current_state != RobotState.CENTRED:
            self.move_centred_position(speed)
        
        self.move_canvas_position(_x=self.config.robot.docked_position["x"], _y=-self.config.robot.docked_position["y"], speed=SpeedType.SLOW, wait=True)
        
        self.set_robot_state(RobotState.DOCKED)
        
    def calibrate_corners(self):
        """
        Calibrate the position of the AprilTags.
        """
        
        self.move_canvas_position(self.config.canvas.min_x, self.config.canvas.max_y)
        self.move_canvas_position(self.config.canvas.min_x, self.config.canvas.max_y, raised=False)
        self.move_canvas_position(self.config.canvas.min_x, self.config.canvas.max_y)
        
        self.move_canvas_position(self.config.canvas.min_x, self.config.canvas.min_y)
        self.move_canvas_position(self.config.canvas.min_x, self.config.canvas.min_y, raised=False)
        self.move_canvas_position(self.config.canvas.min_x, self.config.canvas.min_y)
        
        self.move_canvas_position(self.config.canvas.max_x, self.config.canvas.min_y)
        self.move_canvas_position(self.config.canvas.max_x, self.config.canvas.min_y, raised=False)
        self.move_canvas_position(self.config.canvas.max_x, self.config.canvas.min_y)
        
        self.move_canvas_position(self.config.canvas.max_x, self.config.canvas.max_y)
        self.move_canvas_position(self.config.canvas.max_x, self.config.canvas.max_y, raised=False)
        self.move_canvas_position(self.config.canvas.max_x, self.config.canvas.max_y)
        
        self.move_centred_position()
        
