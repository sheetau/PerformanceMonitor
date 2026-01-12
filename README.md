## Performance Monitor for Wallpaper Engine Web Wallpapers

**Performance Monitor** is a lightweight application designed specifically for [Wallpaper Engine web wallpapers](https://docs.wallpaperengine.io/en/web/overview.html). It collects system performance data and serves it locally so that your web wallpapers can access real-time metrics. When installed, it runs as a Windows service, operating in the background and automatically starting when the system boots.

### Features

- Collects system performance data every second via **psutil / GPUtil** and/or **[HWiNFO](https://www.hwinfo.com/)**, and runs a local Flask server so the data can be accessed from Wallpaper Engine web wallpapers.
- When using **psutil / GPUtil**, the following metrics are available:
  - CPU usage and temperature
  - GPU usage and temperature (NVIDIA GPUs only)
  - RAM and VRAM usage (VRAM metrics for NVIDIA GPUs only)
  - Disk usage
  - Network upload and download speeds

> Note: Temperature readings obtained via **psutil** are only provided if your hardware supports it **and** your wallpaper is designed to utilize them.

> If your CPU temperature via psutil is inaccurate or unavailable, running [OpenHardwareMonitor](https://openhardwaremonitor.org/downloads/) as a Windows service as described [here](https://github.com/openhardwaremonitor/openhardwaremonitor/issues/838#issuecomment-2370917648) may allow the program to access precise readings (save the code with `.ps1` extension in the same folder as `OpenHardwareMonitor.exe`, run it as admin, and start OpenHardwareMonitor service from `services.msc`). However, for the most reliable and detailed temperature data, using the **HWiNFO backend is strongly recommended**.

- When **[HWiNFO](https://www.hwinfo.com/)** is available, all sensors with **“Report value in Gadget”** enabled are collected automatically, providing more accurate clocks, temperatures, and advanced hardware metrics.

> This method provides the most precise and real-time hardware information and is recommended if you require accurate clock speeds or temperature data. Check [Data Sources](#data-sources) for more detailed instructions.

![Screenshot](screenshot.jpg?raw=true)

### Supported Wallpapers

- [[sheeta](https://steamcommunity.com/profiles/76561198383102380/)] [TERMINAL 02](https://steamcommunity.com/sharedfiles/filedetails/?id=3639973107)
- [[sheeta](https://steamcommunity.com/profiles/76561198383102380/)] [UI toggle wallpaper](https://steamcommunity.com/sharedfiles/filedetails/?id=3115349801)
- [[sheeta](https://steamcommunity.com/profiles/76561198383102380/)] [Widget Wallpaper](https://steamcommunity.com/sharedfiles/filedetails/?id=3470738721)
- [[sheeta](https://steamcommunity.com/profiles/76561198383102380/)] [weather + performance monitor widget](https://steamcommunity.com/sharedfiles/filedetails/?id=3343374776)

Only the wallpapers that I am aware of are listed here.

### Installation & Usage

1. Download the latest `PerformanceMonitor.exe` from [Latest Release](https://github.com/sheetau/PerformanceMonitor/releases/latest).
   > This will uninstall any older versions of Performance Monitor if exists and install the latest version.
2. Run the executable **once with administrator privileges**.
   - This sets up the service so it runs in the background automatically after every system restart.
3. By default, performance data is accessible at: http://127.0.0.1:5000/performance

#### Data Sources

- **Default (psutil / GPUtil)**  
  The application works out of the box using `psutil` and `GPUtil`.  
  This provides basic system metrics such as CPU, memory, disk, network, GPU usage, and supported temperature data.

- **Advanced (HWiNFO)**  
  For more detailed and accurate hardware sensors (temperatures, voltages, fan speeds, etc.), HWiNFO can be used.

  To enable it:

  1. Install and launch **[HWiNFO](https://www.hwinfo.com/)**.
  2. In **Settings**, enable all options starting with **“Minimize …”** and **Auto Start**.
  3. Open **Sensor Settings → HWiNFO Gadget**.
  4. Enable **"Enable reporting to Gadget"**, and enable **“Report value in gadget”** for the sensors you want to use.

  Sensors marked this way can be accessed by supported wallpapers by referencing their sensor label names or ids.

#### Changing the Port & Data Sources

1. Download [config.json](https://github.com/sheetau/PerformanceMonitor/blob/main/config.json).
2. Place it in the same folder as `PerformanceMonitor.exe`.
3. Open `config.json` and edit the following options as needed:

   - **Port**

     - Change the `port` value to use a different local server port.

   - **Data source control**

     - Inside the `collect` section, you can enable or disable data sources:
       - Set `psutil` to `true` or `false`
       - Set `hwinfo` to `true` or `false`
     - This allows you to limit which backend is used to collect performance data.

   - **HWiNFO registry fallback**
     - Set `hwinfo_allow_user_hive_fallback` to `true` to enable a fallback mechanism for HWiNFO sensor data.
     - When enabled, the service will resolve the current user’s SID and attempt to read sensor values from:  
       `HKEY_CURRENT_USER\SOFTWARE\HWiNFO64\VSB`
     - By default, data is read from  
       `HKEY_LOCAL_MACHINE\SOFTWARE\HWiNFO64\VSB`
     - This option is intended **only as a fallback** and should be considered **after** confirming that no data is available from the default registry path. You can also verify the data's presence by running `reg query` followed by the registry path in the Command Prompt.

4. Restart the service by right-clicking **Performance Monitor Service** in `services.msc` and selecting **Restart**.

#### Stopping the Service

1. Press `Win + R` and type `services.msc`.
2. Locate **Performance Monitor Service** in the list.
3. Right-click the service and select **Stop**.

#### Uninstalling

Run the included `uninstaller.bat` as Administrator (This will stop and delete Performance Monitor service, Kill any remaining `PerformanceMonitor.exe` processes, and Delete `PerformanceMonitor.exe` itself).

### Security & Privacy

- Built using Python and Flask for a **simple, local performance monitoring environment**.
- The tool runs entirely on your machine and **does not send any data over the internet** or access external servers.
- Performance statistics are collected locally and served only on `localhost`.
- The default endpoint (`http://127.0.0.1:5000/performance`) is only accessible from your own computer.
- Fully open-source, allowing you to inspect and verify the code at any time.

> Note on Security Warnings:
> This executable is not code-signed, so some antivirus software may flag it as suspicious.
> Additionally, because this tool runs as a standard Windows service using legitimate Service APIs, it operates in Session 0. This architecture is necessary for proper system integration and automatic startup, but it can unfortunately cause some user-level diagnostic tools (like Process Explorer or PowerShell's Get-Process) to fail in retrieving standard process metadata (e.g., Path, Company). This behavior is an inherent side effect of the service architecture, not a result of intentional anti-analysis or obfuscation techniques.
> It is safe to run. If you are concerned, you can review the source code in the GitHub repository or uninstall using `uninstaller.bat`. Please understand this is a personal, free project.

### Dependencies and References

- [Python 3.11+](https://www.python.org/)
- [Flask](https://github.com/pallets/flask)
- [Flask-CORS](https://github.com/corydolphin/flask-cors)
- [psutil](https://github.com/giampaolo/psutil)
- [GPUtil](https://github.com/anderskm/gputil)
- [HWiNFO](https://www.hwinfo.com/)
- [pywin32](https://github.com/mhammond/pywin32)
- [PyInstaller](https://github.com/pyinstaller/pyinstaller)
- [Windows Services](https://docs.microsoft.com/en-us/windows/win32/services/services)
- [Wallpaper Engine](https://www.wallpaperengine.io/en)

### Contributing

- Create wallpapers compatible with this monitor by referring to the [next section](#accessing-performance-data-in-your-web-wallpaper).
- Report bugs [here](https://github.com/sheetau/PerformanceMonitor/issues) or in [my server](https://discord.gg/2dXs5HwXuW), including the console output or the contents of the log file, which is usually located at `C:\ProgramData\PerformanceMonitor\performance_monitor.log`.
- If you like my work, please consider:
  - Starring this project on GitHub
  - [![ko-fi](https://www.ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/sheeta)
- Stay tuned in [Sheeta's Discord Server](https://discord.gg/2dXs5HwXuW)

---

### Accessing Performance Data in Your Web Wallpaper

The Performance Monitor exposes system metrics via a local Flask server (default: `http://127.0.0.1:5000/performance`). You can fetch these metrics in your web wallpaper using standard JavaScript `fetch`.

The data is returned in the following JSON format:

```json
{
    "hwinfo": [
        {
            "color": "16375f",
            "id": 1,
            "label": "Total CPU Usage",
            "sensor": "CPU [#0]: AMD Ryzen 9 9900X",
            "value": "3.1 %",
            "valueraw": "3.1"
        },
        {
            "color": "005c80",
            "id": 2,
            "label": "CPU (Tctl/Tdie)",
            "sensor": "CPU [#0]: AMD Ryzen 9 9900X: Enhanced",
            "value": "53.4 °C",
            "valueraw": "53.4"
        },
        ...
    ],
    "psutil": {
        "cpu": 6.1,
        "cpu_temp": 16.9,
		...
    },
    "timestamp": 1767331384.1830423
}
```

#### Available psutil / GPUtil Keys

The following keys are available by default under the `psutil` object:

| Key                   | Description                             | Unit / Format |
| --------------------- | --------------------------------------- | ------------- |
| `cpu`                 | Overall CPU usage percentage            | %             |
| `cpu_temp`            | CPU package temperature (if available)  | °C            |
| `memory`              | RAM usage percentage                    | %             |
| `memory_gb`           | RAM usage in GB                         | GB            |
| `gpu_usage`           | GPU usage percentage                    | %             |
| `vram_usage`          | GPU memory usage percentage             | %             |
| `vram_gb`             | GPU memory usage in GB                  | GB            |
| `gpu_temp`            | GPU temperature                         | °C            |
| `upload_speed`        | Network upload speed                    | KB/s          |
| `download_speed`      | Network download speed                  | KB/s          |
| `c_disk`, `d_disk`, … | Disk usage in format "used GB/total GB" | GB            |
| `timestamp`           | UNIX timestamp of measurement           | seconds       |

#### Handling HWiNFO Data

Since the HWiNFO sensor list is an array and IDs may change depending on your HWiNFO configuration, it is recommended to map the sensors by their label for more reliable access. Labels can also be renamed from within HWiNFO.

You can create a lookup map like this:

```js
const hwinfoMap = Object.create(null);
for (const item of data.hwinfo?.sensors ?? []) {
  hwinfoMap[item.label] = item;
}
```

This allows you to select specific sensors using `hwinfoMap["Label Name"]` and extract values such as `hwinfoMap["Total CPU Usage"].valueraw`. Each sensor object provides the following properties:

- **`color`**: The background color hex code assigned to the tray icon in HWiNFO.
- **`id`**: The index number assigned by HWiNFO.
- **`label`**: The display name (customizable in HWiNFO).
- **`sensor`**: Technical hardware sensor name.
- **`value`**: Formatted value with units (e.g., `"53.4 °C"`).
- **`valueraw`**: Numeric value only (e.g., `"53.4"`).

#### Example Usage

```javascript
const port = 5000; // Default port

async function fetchPerformance() {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/performance`);
    if (!response.ok) throw new Error("Network response was not ok");

    const data = await response.json();
    const psutil = data.psutil ?? {};

    // Map HWiNFO sensors by label for easy access
    const hwinfo = Object.create(null);
    if (data.hwinfo?.available) {
      for (const item of data.hwinfo.sensors) {
        hwinfo[item.label] = item;
      }
    }

    // Prepare log data
    const stats = {
      "CPU Usage": `${psutil.cpu} %`,
      "CPU Temp (HWiNFO)": hwinfo["CPU (Tctl/Tdie)"]?.value ?? `${psutil.cpu_temp} °C`,
      "RAM Usage": `${psutil.memory} %`,
      "GPU Usage": `${psutil.gpu_usage} %`,
      "GPU Temp": hwinfo["GPU Temperature"]?.value ?? `${psutil.gpu_temp} °C`,
      Download: `${psutil.download_speed} KB/s`,
      Upload: `${psutil.upload_speed} KB/s`,
    };

    // Add disk info (any key ending in _disk)
    Object.keys(psutil).forEach((key) => {
      if (key.endsWith("_disk")) {
        stats[`Disk (${key.split("_")[0].toUpperCase()}:)`] = psutil[key];
      }
    });

    console.table(stats);
  } catch (err) {
    console.error("Failed to fetch performance data:", err);
  }
}

// Refresh data every second
setInterval(fetchPerformance, 1000);
```
