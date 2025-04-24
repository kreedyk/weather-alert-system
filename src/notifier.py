import logging
from typing import Dict, Any
import json
import os
import subprocess
import tempfile
import sys
import time

logger = logging.getLogger(__name__)

class Notifier:
    """
    Windows notification system using winotify for modern toast notifications.
    """
    
    def __init__(self, config_path: str):
        """Initialize with configuration file path."""
        self.config_path = config_path
        self.config = self._load_config()
        self._check_winotify()
    
    def _check_winotify(self):
        """Check if winotify is installed and install if not."""
        try:
            import winotify
            logger.debug("winotify is already installed")
        except ImportError:
            logger.info("Installing winotify package...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "winotify"])
                logger.info("winotify installed successfully")
            except Exception as e:
                logger.error(f"Failed to install winotify: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def refresh_config(self):
        """Reload configuration from file."""
        self.config = self._load_config()
    
    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send a desktop notification for a weather alert."""
        # Format alert message
        title = alert.get('message', 'Weather alert')
        message = self._format_alert_message(alert)
        
        # Try winotify first, then fall back to other methods
        methods = [
            self._try_winotify,
            self._try_powershell_toast,
            self._try_balloon_tip
        ]
        
        for method in methods:
            try:
                success = method(title, message)
                if success:
                    return True
            except Exception as e:
                logger.warning(f"Notification method failed: {e}")
        
        logger.warning("All notification methods failed")
        return False
    
    def _format_alert_message(self, alert: Dict[str, Any]) -> str:
        """Format alert data into a readable message."""
        location = alert.get('location', 'Unknown location')
        condition = alert.get('condition', 'Unknown condition')
        current_value = alert.get('current_value', 'N/A')
        threshold = alert.get('threshold', 'N/A')
        
        # Format condition name for display
        condition_name = condition.replace('_', ' ').title()
        
        # Add units based on condition type
        units = self._get_condition_units(condition)
        current_value_str = f"{current_value}{units}"
        threshold_str = f"{threshold}{units}"
        
        alert_text = f"{condition_name} is {current_value_str} (Threshold: {threshold_str})"
        return alert_text
    
    def _get_condition_units(self, condition: str) -> str:
        """Get the appropriate units for a weather condition."""
        units_config = self.config.get('api', {}).get('units', 'metric')
        
        if condition in ['temperature', 'feels_like']:
            return '°C' if units_config == 'metric' else '°F'
        elif condition == 'pressure':
            return ' hPa'
        elif condition == 'humidity':
            return '%'
        elif condition in ['wind']:
            return ' m/s' if units_config == 'metric' else ' mph'
        elif condition in ['precipitation', 'rain', 'snow']:
            return ' mm' if units_config == 'metric' else ' in'
        else:
            return ''
    
    def _try_winotify(self, title: str, message: str) -> bool:
        """Try to send a toast notification using winotify."""
        try:
            from winotify import Notification, audio
            
            # Create notification
            toast = Notification(
                app_id="Weather Alert System",
                title=title,
                msg=message,
                duration="short"
            )
            
            # Set icon if available (uses weather icon from Windows)
            icon_path = os.path.expandvars("%SystemRoot%\\System32\\SHELL32.dll")
            if os.path.exists(icon_path):
                toast.icon = icon_path + ",16"  # Weather icon index
            
            # Set sound
            toast.set_audio(audio.Default, loop=False)
            
            # Show notification
            toast.show()
            
            logger.info(f"Winotify notification sent: {title}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to send winotify notification: {e}")
            return False
    
    def _try_powershell_toast(self, title: str, message: str) -> bool:
        """Try to show a toast notification using PowerShell."""
        try:
            # Use direct BurntToast module if available
            ps_script = f'''
            Import-Module -Name BurntToast -ErrorAction SilentlyContinue
            if (Get-Module -Name BurntToast) {{
                New-BurntToastNotification -Text "{title}", "{message}" -Silent:$false
            }} else {{
                # Fallback to Windows.UI.Notifications API
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

                $APP_ID = 'Weather Alert System'

                $template = @"
                <toast>
                    <visual>
                        <binding template="ToastGeneric">
                            <text>{title}</text>
                            <text>{message}</text>
                        </binding>
                    </visual>
                    <audio src="ms-winsoundevent:Notification.Default" loop="false"/>
                </toast>
                "@

                $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
                $xml.LoadXml($template)
                $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
            }}
            '''
            
            # Save to temp file
            fd, path = tempfile.mkstemp(suffix='.ps1')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(ps_script)
            
            # Run PowerShell with appropriate flags
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-File', path],
                capture_output=True,
                text=True
            )
            
            # Clean up
            try:
                os.unlink(path)
            except:
                pass
            
            if result.returncode == 0:
                logger.info(f"PowerShell toast notification sent: {title}")
                return True
            else:
                logger.warning(f"PowerShell error: {result.stderr}")
                return False
            
        except Exception as e:
            logger.warning(f"Failed to send PowerShell toast: {e}")
            return False
    
    def _try_balloon_tip(self, title: str, message: str) -> bool:
        """Show a balloon tip notification using VBS (non-intrusive fallback)."""
        try:
            vbs_script = f'''
            Set oShell = CreateObject("Wscript.Shell")
            strSystray = oShell.ExpandEnvironmentStrings("%SYSTEMROOT%") & "\\system32\\systray.exe"
            Set objFSO = CreateObject("Scripting.FileSystemObject")
            If objFSO.FileExists(strSystray) Then
                Set objWshShell = CreateObject("WScript.Shell")
                objWshShell.Run strSystray
                WScript.Sleep 100
                objWshShell.SendKeys "%"
                WScript.Sleep 100
                oShell.RegWrite "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\TrayNotify\\BalloonTip", 1, "REG_DWORD"
                oShell.RegWrite "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\TrayNotify\\IconStreams", 1, "REG_BINARY"
                WScript.Sleep 100
                objWshShell.Popup "{message}", 15, "{title}", 0 + 64
            Else
                oShell.Popup "{message}", 15, "{title}", 0 + 64
            End If
            '''
            
            # Save to temp file
            fd, path = tempfile.mkstemp(suffix='.vbs')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(vbs_script)
            
            # Run VBS hidden
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.Popen(
                ['wscript', path],
                startupinfo=startupinfo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give time for process to start
            time.sleep(0.5)
            
            logger.info(f"Balloon tip notification sent: {title}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to send balloon tip: {e}")
            return False
    
    def send_desktop_notification(self, subject: str, message: str) -> bool:
        """Legacy method for compatibility."""
        return self._try_winotify(subject, message)