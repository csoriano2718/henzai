"""System action tools for henzai.

Implements all system-level actions that the AI can perform.
"""

import logging
import subprocess
import os
from typing import Any, Dict
import gi

gi.require_version('Gio', '2.0')
from gi.repository import Gio

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes system actions based on tool calls from the LLM."""
    
    def __init__(self):
        """Initialize the tool executor."""
        logger.info("Tool executor initialized")
    
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Dictionary of parameters for the tool
            
        Returns:
            Result string from tool execution
            
        Raises:
            ValueError: If tool name is unknown
            Exception: If tool execution fails
        """
        tool_map = {
            'launch_app': self.launch_app,
            'adjust_setting': self.adjust_setting,
            'execute_command': self.execute_command,
            'get_system_info': self.get_system_info,
        }
        
        if tool_name not in tool_map:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        logger.info(f"Executing tool: {tool_name} with params: {parameters}")
        
        try:
            result = tool_map[tool_name](**parameters)
            logger.info(f"Tool {tool_name} succeeded: {result}")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
            raise
    
    def launch_app(self, app_name: str) -> str:
        """
        Launch a GNOME application.
        
        Args:
            app_name: Application name or desktop file ID
                     Examples: "firefox", "org.gnome.Nautilus", "terminal"
        
        Returns:
            Success message
            
        Raises:
            Exception: If app cannot be launched
        """
        try:
            # Try to find the application
            app_info = None
            
            # Try as desktop file ID first
            app_info = Gio.DesktopAppInfo.new(f"{app_name}.desktop")
            
            # If not found, try common variations
            if not app_info:
                variations = [
                    app_name,
                    f"org.gnome.{app_name.capitalize()}",
                    f"{app_name.lower()}",
                ]
                
                for variant in variations:
                    app_info = Gio.DesktopAppInfo.new(f"{variant}.desktop")
                    if app_info:
                        break
            
            # If still not found, search all apps
            if not app_info:
                all_apps = Gio.AppInfo.get_all()
                app_name_lower = app_name.lower()
                
                for app in all_apps:
                    name = app.get_name().lower()
                    display_name = app.get_display_name().lower()
                    
                    if app_name_lower in name or app_name_lower in display_name:
                        app_info = app
                        break
            
            if not app_info:
                return f"Could not find application: {app_name}"
            
            # Launch the application
            success = app_info.launch([], None)
            
            if success:
                app_display_name = app_info.get_display_name()
                return f"Launched {app_display_name}"
            else:
                return f"Failed to launch {app_name}"
                
        except Exception as e:
            logger.error(f"Error launching app {app_name}: {e}", exc_info=True)
            raise Exception(f"Failed to launch {app_name}: {str(e)}")
    
    def adjust_setting(self, schema: str, key: str, value: str) -> str:
        """
        Change a GNOME system setting using gsettings.
        
        Args:
            schema: GSettings schema (e.g., "org.gnome.desktop.interface")
            key: Setting key (e.g., "color-scheme", "gtk-theme")
            value: New value for the setting
            
        Returns:
            Success message
            
        Raises:
            Exception: If setting cannot be changed
        """
        try:
            # Use gsettings command
            result = subprocess.run(
                ['gsettings', 'set', schema, key, value],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                error = result.stderr or "Unknown error"
                raise Exception(f"gsettings error: {error}")
            
            return f"Set {schema} {key} to {value}"
            
        except subprocess.TimeoutExpired:
            raise Exception("Setting change timed out")
        except FileNotFoundError:
            raise Exception("gsettings command not found")
        except Exception as e:
            logger.error(f"Error adjusting setting: {e}", exc_info=True)
            raise Exception(f"Failed to adjust setting: {str(e)}")
    
    def execute_command(self, command: str) -> str:
        """
        Execute a shell command (with safety restrictions).
        
        Args:
            command: Shell command to execute
            
        Returns:
            Command output
            
        Raises:
            Exception: If command execution fails or is unsafe
        """
        # Safety check: block potentially dangerous commands
        dangerous_patterns = [
            'rm -rf /',
            'mkfs',
            'dd if=',
            '> /dev/',
            'chmod 777',
            'chown root',
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                raise Exception(f"Dangerous command blocked: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = result.stdout.strip()
            if result.returncode != 0:
                error = result.stderr.strip()
                return f"Command failed (exit {result.returncode}): {error}"
            
            return output or "Command executed successfully"
            
        except subprocess.TimeoutExpired:
            raise Exception("Command execution timed out")
        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            raise Exception(f"Failed to execute command: {str(e)}")
    
    def get_system_info(self) -> str:
        """
        Get information about the system.
        
        Returns:
            System information string
        """
        try:
            info_parts = []
            
            # OS information
            try:
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            os_name = line.split('=')[1].strip().strip('"')
                            info_parts.append(f"OS: {os_name}")
                            break
            except:
                info_parts.append("OS: Unknown Linux")
            
            # Desktop session
            desktop = os.environ.get('DESKTOP_SESSION', 'unknown')
            info_parts.append(f"Desktop: {desktop}")
            
            # Currently running apps
            try:
                all_apps = Gio.AppInfo.get_all()
                # This is a simplified approach - in reality, you'd need to query
                # the window manager for actually running apps
                info_parts.append(f"Installed applications: {len(all_apps)}")
            except:
                pass
            
            # Uptime
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                    uptime_hours = int(uptime_seconds / 3600)
                    info_parts.append(f"System uptime: {uptime_hours} hours")
            except:
                pass
            
            return "\n".join(info_parts)
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}", exc_info=True)
            return f"Error retrieving system information: {str(e)}"


# Helper functions for common settings

def enable_dark_mode():
    """Enable GNOME dark mode."""
    executor = ToolExecutor()
    return executor.adjust_setting(
        "org.gnome.desktop.interface",
        "color-scheme",
        "prefer-dark"
    )


def disable_dark_mode():
    """Disable GNOME dark mode."""
    executor = ToolExecutor()
    return executor.adjust_setting(
        "org.gnome.desktop.interface",
        "color-scheme",
        "prefer-light"
    )


def set_volume(level: int):
    """
    Set system volume level.
    
    Args:
        level: Volume level (0-100)
    """
    executor = ToolExecutor()
    # Volume is 0.0 to 1.0 in GNOME
    volume_decimal = max(0.0, min(1.0, level / 100.0))
    return executor.execute_command(f"pactl set-sink-volume @DEFAULT_SINK@ {level}%")










