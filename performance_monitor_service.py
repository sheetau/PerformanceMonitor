#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Monitor Windows Service
Enhanced with CPU and GPU temperature monitoring
"""

import os
import sys
import json
import time
import threading
import logging
import traceback
import subprocess
from pathlib import Path
import ctypes
from ctypes import wintypes

import win32service
import win32serviceutil
import win32event
import servicemanager
from flask import Flask, jsonify
from flask_cors import CORS
import psutil

# Optionally import GPUtil
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# Logging configuration
LOG_DIR = Path(os.path.expandvars(r'%PROGRAMDATA%\PerformanceMonitor'))
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'performance_monitor.log'

logger = logging.getLogger('PerformanceMonitor')
logger.setLevel(logging.INFO)

# console log and log file handler (INFO and above)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)


class PerformanceMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PerformanceMonitor"
    _svc_display_name_ = "Performance Monitor Service"
    _svc_description_ = "System performance monitoring service for Wallpaper Engine"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.app = None
        self.flask_thread = None
        self.monitor_thread = None
        self.running = False
        self.performance_data = {}
        self.data_file = LOG_DIR / 'performance.json'
        self.port = self.load_port_config()
        
        logger.warning(f"Performance Monitor Service initialized (Port: {self.port})")
    
    def load_port_config(self):
        """Load port configuration"""
        try:
            if getattr(sys, 'frozen', False):
                config_dir = Path(sys.executable).parent
            else:
                config_dir = Path(__file__).parent
            
            config_file = config_dir / 'config.json'
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    port = config.get('port', 5000)
                    logger.warning(f"Port configuration loaded from {config_file}: {port}")
                    return port
            else:
                return 5000
        except Exception as e:
            logger.warning(f"Error loading port config: {e}, using default port 5000")
            return 5000

    def get_cpu_temperature(self):
        """Get CPU temperature using multiple methods"""
        try:
            # Method 1: Try psutil sensors (works on some systems)
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Try different sensor names
                    for sensor_name in ['coretemp', 'k10temp', 'acpi', 'thermal']:
                        if sensor_name in temps:
                            for entry in temps[sensor_name]:
                                if entry.current and entry.current > 0:
                                    return round(entry.current, 1)
            
            # Method 2: Try WMI through subprocess (Windows specific)
            try:
                result = subprocess.run([
                    'powershell', '-Command',
                    'Get-WmiObject -Namespace "root/OpenHardwareMonitor" -Class Sensor | Where-Object {$_.SensorType -eq "Temperature" -and $_.Name -like "*CPU*"} | Select-Object -First 1 -ExpandProperty Value'
                ], capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0 and result.stdout.strip():
                    temp = float(result.stdout.strip())
                    if temp > 0:
                        return round(temp, 1)
            except:
                pass
            
            # Method 3: Try alternative WMI query
            try:
                result = subprocess.run([
                    'powershell', '-Command',
                    'Get-WmiObject -Class MSAcpi_ThermalZoneTemperature -Namespace "root/wmi" | Select-Object -First 1 -ExpandProperty CurrentTemperature'
                ], capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0 and result.stdout.strip():
                    # Convert from tenths of Kelvin to Celsius
                    temp_kelvin = float(result.stdout.strip()) / 10
                    temp_celsius = temp_kelvin - 273.15
                    if temp_celsius > 0 and temp_celsius < 150:  # Sanity check
                        return round(temp_celsius, 1)
            except:
                pass
            
        except Exception as e:
            logger.debug(f"CPU temperature unavailable: {e}")
        
        return None

    def get_gpu_temperature(self):
        """Get GPU temperature"""
        try:
            if GPU_AVAILABLE:
                gpus = GPUtil.getGPUs()
                if gpus and gpus[0].temperature is not None:
                    return round(gpus[0].temperature, 1)
            
            # Alternative method using nvidia-ml-py or subprocess
            try:
                result = subprocess.run([
                    'nvidia-smi', '--query-gpu=temperature.gpu', 
                    '--format=csv,noheader,nounits'
                ], capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0 and result.stdout.strip():
                    temp = float(result.stdout.strip())
                    if temp > 0:
                        return round(temp, 1)
            except:
                pass
            
        except Exception as e:
            logger.debug(f"GPU temperature unavailable: {e}")
        
        return None

    def SvcStop(self):
        logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False
        
        if self.flask_thread and self.flask_thread.is_alive():
            logger.info("Stopping Flask application...")
            # Note: Graceful shutdown of Flask is complex; relies on process exit
        
        logger.info("Service stopped")

    def SvcDoRun(self):
        logger.info("Performance Monitor Service starting...")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.running = True
            self.main()
        except Exception as e:
            logger.error(f"Service error: {e}")
            logger.error(traceback.format_exc())
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, str(e))
            )

    def create_flask_app(self):
        """Create Flask application"""
        app = Flask(__name__)
        CORS(app, origins="*")
        
        app.logger.setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        
        @app.route('/performance', methods=['GET'])
        def get_performance():
            try:
                if self.data_file.exists():
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = self.get_default_data()
                return jsonify(data)
            except Exception as e:
                logger.error(f"Error serving performance data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @app.route('/status', methods=['GET'])
        def get_status():
            """Return service status"""
            return jsonify({
                'status': 'running',
                'service': self._svc_display_name_,
                'port': self.port,
                'gpu_available': GPU_AVAILABLE,
                'timestamp': time.time()
            })
        
        return app

    def get_default_data(self):
        """Return default performance data"""
        return {
            'cpu': 0,
            'memory': 0,
            'gpu_usage': 0,
            'vram_usage': 0,
            'cpu_temp': None,
            'gpu_temp': None,
            'upload_speed': 0,
            'download_speed': 0,
            'timestamp': time.time()
        }

    def get_performance_data(self):
        """Collect performance data"""
        try:
            gpu_usage, vram_usage = 0, 0
            if GPU_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu = gpus[0]
                        gpu_usage = round(gpu.load * 100, 1)
                        vram_usage = round(gpu.memoryUsed / gpu.memoryTotal * 100, 1)
                except Exception as e:
                    logger.debug(f"GPU data unavailable: {e}")

            # Get temperature data
            cpu_temp = self.get_cpu_temperature()
            gpu_temp = self.get_gpu_temperature()

            net_io_before = psutil.net_io_counters()
            time.sleep(1)
            net_io_after = psutil.net_io_counters()
            
            upload_speed = round((net_io_after.bytes_sent - net_io_before.bytes_sent) * 8 / 1000, 1)
            download_speed = round((net_io_after.bytes_recv - net_io_before.bytes_recv) * 8 / 1000, 1)

            data = {
                'cpu': round(psutil.cpu_percent(), 1),
                'memory': round(psutil.virtual_memory().percent, 1),
                'gpu_usage': gpu_usage,
                'vram_usage': vram_usage,
                'cpu_temp': cpu_temp,
                'gpu_temp': gpu_temp,
                'upload_speed': upload_speed,
                'download_speed': download_speed,
                'timestamp': time.time()
            }

            try:
                for disk in psutil.disk_partitions():
                    if 'cdrom' in disk.opts or disk.fstype == '':
                        continue
                    try:
                        usage = psutil.disk_usage(disk.mountpoint)
                        drive_letter = disk.device[0].lower()
                        data[f'{drive_letter}_disk'] = f"{usage.used / (1024**3):.1f} GB/{usage.total / (1024**3):.1f} GB"
                    except PermissionError:
                        continue
                    except Exception:
                        continue
            except Exception:
                pass

            return data
            
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return self.get_default_data()

    def update_performance_loop(self):
        """Loop to update performance data"""
        logger.info("Performance monitoring started")
        
        while self.running:
            try:
                data = self.get_performance_data()
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.performance_data = data
                
                # Log with temperature info
                temp_info = ""
                if data.get('cpu_temp'):
                    temp_info += f", CPU Temp={data['cpu_temp']}°C"
                if data.get('gpu_temp'):
                    temp_info += f", GPU Temp={data['gpu_temp']}°C"
                
                logger.debug(f"Performance data updated: CPU={data['cpu']}%, Memory={data['memory']}%{temp_info}")
                
            except Exception as e:
                logger.error(f"Error updating performance data: {e}")
                logger.error(traceback.format_exc())
            
            time.sleep(1)
        
        logger.info("Performance monitoring stopped")

    def run_flask(self):
        """Run Flask server"""
        try:
            logger.info(f"Starting Flask server on http://127.0.0.1:{self.port}")
            self.app.run(
                host='127.0.0.1', 
                port=self.port, 
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Flask server error: {e}")
            logger.error(traceback.format_exc())

    def main(self):
        """Main processing"""
        try:
            self.app = self.create_flask_app()
            self.monitor_thread = threading.Thread(target=self.update_performance_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring thread started")
            
            self.flask_thread = threading.Thread(target=self.run_flask, daemon=True)
            self.flask_thread.start()
            logger.info("Flask server thread started")
            
            logger.info("Performance Monitor Service is running")
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            
        except Exception as e:
            logger.error(f"Main thread error: {e}")
            logger.error(traceback.format_exc())


def check_admin_rights():
    """Check for admin rights"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin_rights():
    """Request admin rights"""
    if check_admin_rights():
        return True
    
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas", 
            sys.executable, 
            " ".join(sys.argv), 
            None, 
            1
        )
    except Exception as e:
        logger.error(f"Failed to request admin rights: {e}")
        return False
    
    return False

def install_service():
    """Install the Windows service"""
    try:
        logger.info("Installing Performance Monitor Service...")
        exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        logger.info(f"Service executable path: {exe_path}")
        
        svc_name = PerformanceMonitorService._svc_name_

        try:
            logger.info("Attempting to stop existing service...")
            win32serviceutil.StopService(svc_name)
            logger.info("Existing service stopped.")
        except Exception as e:
            logger.debug(f"Service was not running or stop failed: {e}")

        try:
            logger.info("Attempting to remove existing service...")
            win32serviceutil.RemoveService(svc_name)
            logger.info("Existing service marked for deletion.")

            timeout = 30
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    win32serviceutil.QueryServiceStatus(svc_name)
                    logger.debug("Service still exists. Waiting...")
                    time.sleep(1)
                except Exception:
                    logger.info("Existing service removed successfully.")
                    break
            else:
                logger.error("Timeout waiting for service deletion to complete.")
                return False

        except Exception as e:
            logger.debug(f"No existing service to remove or removal failed: {e}")

        hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        try:
            service_cmd = f'"{exe_path}" debug'
            hs = win32service.CreateService(
                hscm,
                svc_name,
                PerformanceMonitorService._svc_display_name_,
                win32service.SERVICE_ALL_ACCESS,
                win32service.SERVICE_WIN32_OWN_PROCESS,
                win32service.SERVICE_AUTO_START,
                win32service.SERVICE_ERROR_NORMAL,
                service_cmd,
                None,
                0,
                None,
                None,
                None
            )

            try:
                win32service.ChangeServiceConfig2(
                    hs,
                    win32service.SERVICE_CONFIG_DESCRIPTION,
                    PerformanceMonitorService._svc_description_
                )
            except Exception as e:
                logger.warning(f"Failed to set service description: {e}")
            
            win32service.CloseServiceHandle(hs)
            logger.info("Service installed successfully")
            return True

        finally:
            win32service.CloseServiceHandle(hscm)

    except Exception as e:
        logger.error(f"Service installation failed: {e}")
        logger.error(traceback.format_exc())
        return False


def start_service():
    """Start the service"""
    try:
        logger.info("Starting Performance Monitor Service...")
        hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        try:
            hs = win32service.OpenService(hscm, PerformanceMonitorService._svc_name_, win32service.SERVICE_ALL_ACCESS)
            try:
                win32service.StartService(hs, None)
                logger.info("Service started successfully")
                return True
            finally:
                win32service.CloseServiceHandle(hs)
        finally:
            win32service.CloseServiceHandle(hscm)
            
    except Exception as e:
        logger.error(f"Service start failed: {e}")
        logger.error(traceback.format_exc())
        return False


def get_service_port():
    try:
        if getattr(sys, 'frozen', False):
            config_dir = Path(sys.executable).parent
        else:
            config_dir = Path(__file__).parent

        config_file = config_dir / 'config.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f).get('port', 5000)
        else:
            return 5000
    except Exception as e:
        logger.warning(f"Error loading port config: {e}, using default port 5000")
        return 5000

def create_uninstall_bat():
    """Create uninstall batch in the same folder as the exe"""
    try:
        exe_dir = os.path.dirname(sys.executable)
        bat_path = os.path.join(exe_dir, "uninstaller.bat")
        bat_content = f"""@echo off
        :: Check for admin rights
        >nul 2>&1 "%SYSTEMROOT%\\system32\\cacls.exe" "%SYSTEMROOT%\\system32\\config\\system"
        if '%errorlevel%' NEQ '0' (
            echo This script requires Administrator privileges. Please run as Administrator.
            pause
            exit /b
        )

        echo Stopping Performance Monitor service...
        sc stop PerformanceMonitor || echo Failed to stop service. It may not be running.

        timeout /t 2 /nobreak >nul

        echo Deleting Performance Monitor service...
        sc delete PerformanceMonitor || echo Failed to delete service. It may have been already removed.

        echo Killing any remaining PerformanceMonitor.exe processes...
        taskkill /f /im PerformanceMonitor.exe || echo No running process found.

        echo Deleting PerformanceMonitor.exe...
        del "{os.path.join(exe_dir, 'PerformanceMonitor.exe')}" || echo Could not delete exe. It may not exist or be open.

        echo Deleting README_for_users.txt...
        del "{os.path.join(exe_dir, 'README_for_users.txt')}" || echo README file not found or already deleted.

        echo Uninstallation completed.

        echo You can safely delete this uninstaller.bat file if you want.
        pause
        """
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        print(f"\nUninstall script created: {bat_path}")
    except Exception as e:
        print(f"\nFailed to create uninstall script: {e}")

def extract_and_open_readme():
    """Open README"""
    try:
        if getattr(sys, 'frozen', False):
            bundle_dir = sys._MEIPASS
            readme_bundled = os.path.join(bundle_dir, 'README_for_users.txt')
            readme_target = os.path.join(os.path.dirname(sys.executable), 'README_for_users.txt')
            
            if os.path.exists(readme_bundled):
                import shutil
                shutil.copy2(readme_bundled, readme_target)
                
                os.startfile(readme_target)
                print(f"\nREADME file extracted and opened: {readme_target}")
                return True
            else:
                print(f"\nREADME file not found in bundle: {readme_bundled}")
                return False
        else:
            readme_path = os.path.join(os.path.dirname(__file__), 'README_for_users.txt')
            if os.path.exists(readme_path):
                os.startfile(readme_path)
                print(f"\nREADME file opened: {readme_path}")
                return True
            else:
                print(f"\nREADME file not found: {readme_path}")
                return False
                
    except Exception as e:
        print(f"\nError handling README file: {e}")
        return False

def main():
    """Main function"""
    LOG_DIR.mkdir(exist_ok=True)
    
    if getattr(sys, 'frozen', False):
        if len(sys.argv) == 1:
            print("Performance Monitor Service Installer")
            print("====================================")
            
            if not check_admin_rights():
                print("Admin rights are required. Restarting as admin...")
                if not request_admin_rights():
                    input("Failed to obtain admin rights. Press Enter to exit...")
                    return
                else:
                    return
            
            print("Running with admin rights...")
            
            if install_service():
                print("Service installation completed.")
                time.sleep(3)
                if start_service():
                    port = get_service_port()
                    print("Service started successfully.")
                    print(f"Log file: {LOG_FILE}")
                    print(f"Performance data: http://127.0.0.1:{port}/performance")
                    print(f"Service status: http://127.0.0.1:{port}/status")
                    
                    create_uninstall_bat()
                    extract_and_open_readme()
                        
                else:
                    print(f"Failed to start the service. Check logs at {LOG_FILE}")
            else:
                print(f"Failed to install the service. Check logs at {LOG_FILE}")
            
            input("\nPress Enter to exit...")
            return
        else:
            arg = sys.argv[1].lower()
            
            if not check_admin_rights():
                print("Admin rights are required.")
                input("Press Enter to exit...")
                return
                
            if arg == 'install':
                if install_service():
                    print("Service installation completed.")
                    if start_service():
                        print("Service started successfully.")
                return
            elif arg == 'start':
                if start_service():
                    print("Service started successfully.")
                return
            elif arg == 'stop':
                try:
                    win32serviceutil.StopService(PerformanceMonitorService._svc_name_)
                    print("Service stopped.")
                except Exception as e:
                    print(f"Service stop error: {e}")
                return
            elif arg == 'remove':
                try:
                    win32serviceutil.StopService(PerformanceMonitorService._svc_name_)
                    time.sleep(2)
                except:
                    pass
                try:
                    win32serviceutil.RemoveService(PerformanceMonitorService._svc_name_)
                    print("Service removed.")
                except Exception as e:
                    print(f"Service removal error: {e}")
                return
            elif arg in ['debug', '--debug']:
                logger.info("Running in debug mode")
                servicemanager.Initialize()
                servicemanager.PrepareToHostSingle(PerformanceMonitorService)
                servicemanager.StartServiceCtrlDispatcher()
                return
            else:
                try:
                    win32serviceutil.HandleCommandLine(PerformanceMonitorService)
                except SystemExit:
                    pass
                return
    else:
        if len(sys.argv) > 1:
            win32serviceutil.HandleCommandLine(PerformanceMonitorService)
        else:
            print("Development mode - running service directly")
            service = PerformanceMonitorService([''])
            service.main()
    
    logger.info("Starting as Windows Service")
    servicemanager.Initialize()
    servicemanager.PrepareToHostSingle(PerformanceMonitorService)
    servicemanager.StartServiceCtrlDispatcher()


if __name__ == '__main__':
    main()