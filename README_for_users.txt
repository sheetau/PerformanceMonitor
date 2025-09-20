Performance Monitor for Wallpaper Engine – Safety Information
(The installation is complete so you don't necessarily need to read this.)

Performance Monitor is a lightweight application designed specifically for Wallpaper Engine web wallpapers. It collects system performance data and serves it locally so that your web wallpapers can access real-time metrics. When installed, it runs as a Windows service, operating in the background and automatically starting when the system boots.

- Built using Python and Flask for a simple, local performance monitoring environment.
- The tool runs entirely on your machine and does not send any data over the internet or access external servers.
- Performance statistics are collected locally and served only on localhost.
- The default endpoint (http://127.0.0.1:5000/performance) is only accessible from your own computer.
- Fully open-source: you can inspect the code at any time: https://github.com/sheetau/PerformanceMonitor.

Note on Security Warnings:
This executable is not code-signed, so some antivirus software may flag it as suspicious.
It is safe to run. If you are concerned, you can review the source code in the GitHub repository or uninstall using the steps below. Please understand this is a personal, free project.

Stopping the Service:
1. Press Win + R, type services.msc, and press Enter.
2. Locate Performance Monitor Service in the list.
3. Right-click > Stop

Changing the Port:
1. Create a config.json file in the same folder as PerformanceMonitor.exe with:
{
  "port": 5000
}
2. Modify the port number as needed.
3. Restart the service in services.msc.

Uninstalling:
Run the included uninstaller.bat as Administrator (This will stop and delete Performance Monitor service, Kill any remaining PerformanceMonitor.exe processes, and Delete PerformanceMonitor.exe itself).
