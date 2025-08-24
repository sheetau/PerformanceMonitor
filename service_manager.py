#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Monitor Service Manager
Utility for managing the service
"""

import sys
import ctypes
import subprocess
from pathlib import Path

def check_admin_rights():
    """Check for administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin_rights():
    """Request administrator privileges"""
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
        return False  # The script will be re-run as admin
    except Exception as e:
        print(f"Failed to acquire administrator rights: {e}")
        return False

def run_service_command(exe_path, command):
    """Run a service command"""
    try:
        cmd = [exe_path, command]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print(f"✓ '{command}' command executed successfully")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"✗ Failed to execute '{command}' command")
            if result.stderr:
                print(f"Error: {result.stderr}")
        
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Command execution error: {e}")
        return False

def main():
    print("Performance Monitor Service Manager")
    print("==================================")
    print()
    
    if not check_admin_rights():
        print("Administrator privileges are required. Re-running as admin...")
        if not request_admin_rights():
            input("Failed to acquire administrator privileges. Press Enter to exit...")
        return
    
    # Path to executable
    exe_path = Path("PerformanceMonitor.exe")
    if not exe_path.exists():
        print("PerformanceMonitor.exe not found.")
        print("Please build it first.")
        input("Press Enter to exit...")
        return
    
    while True:
        print("\nAvailable commands:")
        print("1. Install service")
        print("2. Start service")
        print("3. Stop service") 
        print("4. Remove service")
        print("5. Check service status")
        print("6. Show logs")
        print("0. Exit")
        print()
        
        choice = input("Please select (0-6): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            print("\nInstalling service...")
            run_service_command(str(exe_path), "install")
        elif choice == '2':
            print("\nStarting service...")
            run_service_command(str(exe_path), "start")
        elif choice == '3':
            print("\nStopping service...")
            run_service_command(str(exe_path), "stop")
        elif choice == '4':
            print("\nRemoving service...")
            run_service_command(str(exe_path), "remove")
        elif choice == '5':
            print("\nChecking service status...")
            try:
                result = subprocess.run(
                    ["sc", "query", "PerformanceMonitor"], 
                    capture_output=True, 
                    text=True, 
                    encoding='cp932'
                )
                if result.returncode == 0:
                    print(result.stdout)
                else:
                    print("Service not found or access denied.")
            except Exception as e:
                print(f"Status check error: {e}")
        elif choice == '6':
            print("\nShowing logs...")
            log_path = Path(r"C:\ProgramData\PerformanceMonitor\performance_monitor.log")
            if log_path.exists():
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # Show the last 50 lines
                        for line in lines[-50:]:
                            print(line.rstrip())
                except Exception as e:
                    print(f"Log read error: {e}")
            else:
                print("Log file not found.")
        else:
            print("Invalid selection.")
    
    print("\nExiting service manager.")

if __name__ == '__main__':
    main()
