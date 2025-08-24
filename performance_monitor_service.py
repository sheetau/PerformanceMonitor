#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Monitor Windows Service
"""

import os
import sys
import json
import time
import threading
import logging
import traceback
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

# Optional GPUtil import
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# Logging setup
LOG_DIR = Path(os.path.expandvars(r'%PROGRAMDATA%\\PerformanceMonitor'))
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'performance_monitor.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('PerformanceMonitor')

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
        
        logger.info(f"Performance Monitor Service initialized (Port: {self.port})")
    
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
                    logger.info(f"Port configuration loaded from {config_file}: {port}")
                    return port
            else:
                logger.info(f"No config file found at {config_file}, using default port 5000")
                return 5000
        except Exception as e:
            logger.warning(f"Error loading port config: {e}, using default port 5000")
            return 5000

    def SvcStop(self):
        logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False

        if self.flask_thread and self.flask_thread.is_alive():
            logger.info("Stopping Flask application...")

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
        """Create Flask app"""
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
            return jsonify({
                'status': 'running',
                'service': self._svc_display_name_,
                'port': self.port,
                'gpu_available': GPU_AVAILABLE,
                'timestamp': time.time()
            })
        
        return app

    def get_default_data(self):
        """Default performance data"""
        return {
            'cpu': 0,
            'memory': 0,
            'gpu_usage': 0,
            'vram_usage': 0,
            'upload_speed': 0,
            'download_speed': 0,
            'timestamp': time.time()
        }

    def get_performance_data(self):
        """Collect performance data"""
        try:
            gpu_usage, vram_usage, gpu_temp = 0, 0, None
            if GPU_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu = gpus[0]
                        gpu_usage = round(gpu.load * 100, 1)
                        vram_usage = round(gpu.memoryUsed / gpu.memoryTotal * 100, 1)
                        gpu_temp = gpu.temperature
                except Exception as e:
                    logger.debug(f"GPU data unavailable: {e}")

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
                'gpu_temp': gpu_temp,
                'upload_speed': upload_speed,
                'download_speed': download_speed,
                'timestamp': time.time()
            }

            # CPU and drive temperatures
            try:
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    cpu_temps = temps['coretemp']
                    for t in cpu_temps:
                        if 'Package' in t.label or 'Tctl' in t.label:
                            data['cpu_temp'] = t.current
                    for i, t in enumerate(cpu_temps):
                        if t.label.startswith('Core'):
                            data[f'cpu_core{i}_temp'] = t.current
                for name, entries in temps.items():
                    if 'nvme' in name or 'disk' in name:
                        for i, t in enumerate(entries):
                            data[f'{name}_{i}_temp'] = t.current
            except Exception as e:
                logger.debug(f"Temperature data unavailable: {e}")

            # Disk usage
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
                    except Exception as e:
                        logger.debug(f"Disk {disk.device} error: {e}")
            except Exception as e:
                logger.debug(f"Error getting disk info: {e}")

            return data
            
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return self.get_default_data()

    def update_performance_loop(self):
        """Performance update loop"""
        logger.info("Performance monitoring started")
        
        while self.running:
            try:
                data = self.get_performance_data()
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.performance_data = data
                logger.debug(f"Performance data updated: CPU={data['cpu']}%, Memory={data['memory']}%")
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
        """Main loop"""
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
    """Check if running with admin rights"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin_rights():
    """Request admin rights"""
    if check_admin_rights():
        return True
    
    # Re-run as administrator
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
    """Install the service"""
    try:
        logger.info("Installing Performance Monitor Service...")
        
        # Get current executable path
        if getattr(sys, 'frozen', False):
            # If packaged with PyInstaller
            exe_path = sys.executable
        else:
            # Normal Python execution
            exe_path = os.path.abspath(__file__)
        
        logger.info(f"Service executable path: {exe_path}")
        
        # Remove existing service (if exists)
        try:
            win32serviceutil.RemoveService(PerformanceMonitorService._svc_name_)
            logger.info("Existing service removed")
            time.sleep(2)  # Wait for removal to complete
        except Exception as e:
            logger.debug(f"No existing service to remove: {e}")
        
        # Open service manager
        hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        try:
            # Service execution command (with debug argument)
            service_cmd = f'"{exe_path}" debug'
            
            # Create service
            hs = win32service.CreateService(
                hscm,
                PerformanceMonitorService._svc_name_,
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
            
            # Set service description
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
        
        # Open service manager
        hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        try:
            # Open service
            hs = win32service.OpenService(hscm, PerformanceMonitorService._svc_name_, win32service.SERVICE_ALL_ACCESS)
            try:
                # Start service
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


def main():
    """Main function"""
    # Create log directory
    LOG_DIR.mkdir(exist_ok=True)
    
    # Check if running with PyInstaller package
    if getattr(sys, 'frozen', False):
        # Special handling when running as exe
        if len(sys.argv) == 1:
            # No arguments → run in installer mode
            logger.info("Running in service control mode")
            
            # Installer mode
            print("Performance Monitor Service Installer")
            print("====================================")
            
            if not check_admin_rights():
                print("Administrator privileges are required. Re-running as administrator...")
                if not request_admin_rights():
                    input("Failed to obtain administrator rights. Press Enter to exit...")
                    return
                else:
                    return  # Relaunched as administrator
            
            print("Running with administrator rights...")
            
            # Install and start service
            if install_service():
                print("Service installation completed.")
                time.sleep(3)  # Wait for installation to complete
                if start_service():
                    port = PerformanceMonitorService(['dummy']).port  # Get port setting
                    print("Service started successfully.")
                    print(f"Log file: {LOG_FILE}")
                    print(f"Performance data: http://127.0.0.1:{port}/performance")
                    print(f"Service status: http://127.0.0.1:{port}/status")
                else:
                    print("Failed to start service. Please check the logs.")
            else:
                print("Failed to install service. Please check the logs.")
            
            input("\nPress Enter to exit...")
            return
        else:
            # If arguments are provided
            arg = sys.argv[1].lower()
            
            if not check_admin_rights():
                print("Administrator privileges are required.")
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
                    pass  # Already stopped
                try:
                    win32serviceutil.RemoveService(PerformanceMonitorService._svc_name_)
                    print("Service removed.")
                except Exception as e:
                    print(f"Service removal error: {e}")
                return
            elif arg in ['debug', '--debug']:
                # Debug mode - run as service
                logger.info("Running in debug mode")
                servicemanager.Initialize()
                servicemanager.PrepareToHostSingle(PerformanceMonitorService)
                servicemanager.StartServiceCtrlDispatcher()
                return
            else:
                # Delegate to win32serviceutil
                try:
                    win32serviceutil.HandleCommandLine(PerformanceMonitorService)
                except SystemExit:
                    pass  # Normal exit
                return
    else:
        # Development mode (direct Python execution)
        if len(sys.argv) > 1:
            # Handle service-related CLI args
            win32serviceutil.HandleCommandLine(PerformanceMonitorService)
        else:
            # Direct execution mode (testing)
            print("Development mode - running service directly")
            service = PerformanceMonitorService([''])
            service.main()
    
    # Run as Windows Service (when started by Service Manager)
    logger.info("Starting as Windows Service")
    servicemanager.Initialize()
    servicemanager.PrepareToHostSingle(PerformanceMonitorService)
    servicemanager.StartServiceCtrlDispatcher()


if __name__ == '__main__':
    main()