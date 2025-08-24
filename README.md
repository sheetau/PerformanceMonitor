## Performance Monitor for Wallpaper Engine Web Wallpapers

**Performance Monitor** is a lightweight application designed specifically for [Wallpaper Engine web wallpapers](https://docs.wallpaperengine.io/en/web/overview.html). It collects system performance data and serves it locally so that your web wallpapers can access real-time metrics. When installed, it runs as a Windows service, operating in the background and automatically starting when the system boots.

### Features

- Collects performance information every second, such as:
  - CPU usage and temperature
  - GPU usage and temperature (NVIDIA GPUs only)
  - RAM and VRAM usage (VRAM metrics for NVIDIA GPUs only)
  - Disk usage and temperature
  - Network upload and download speeds

> Note: Temperature readings (CPU, GPU, Disk) are only provided if your hardware supports it **and** your wallpaper is designed to utilize them.

- Uses the following Python libraries to gather data: `GPUtil` for GPU-related metrics and `psutil` for others.
- Runs a local Flask server to make performance data accessible to Wallpaper Engine web wallpapers.

![Screenshot](screenshot.jpg?raw=true)

### Supported Wallpapers

- [[sheeta](https://steamcommunity.com/profiles/76561198383102380/)] [UI toggle wallpaper](https://steamcommunity.com/sharedfiles/filedetails/?id=3115349801)
- [[sheeta](https://steamcommunity.com/profiles/76561198383102380/)] [Widget Wallpaper](https://steamcommunity.com/sharedfiles/filedetails/?id=3470738721)
- [[sheeta](https://steamcommunity.com/profiles/76561198383102380/)] [weather + performance monitor widget](https://steamcommunity.com/sharedfiles/filedetails/?id=3343374776)

Only the wallpapers that I am aware of are listed here.

### Installation & Usage

1. Download the latest `PerformanceMonitor.exe` from [Latest Release](https://github.com/sheetau/PerformanceMonitor/releases/latest).
2. Run the executable **once with administrator privileges**.
   - This sets up the service so it runs in the background automatically after every system restart.
3. By default, performance data is accessible at: http://127.0.0.1:5000/performance

### Stopping the Service

1. Press `Win + R` and type `services.msc`.
2. Locate **Performance Monitor Service** in the list.
3. Right-click the service and select **Stop**.

### Changing the Port

1. Download [config.json](https://github.com/sheetau/PerformanceMonitor/blob/main/config.json).
2. Place it in the same folder as `PerformanceMonitor.exe`.
3. Modify the port number inside `config.json`.
4. Restart the service by right-clicking **Performance Monitor Service** in `services.msc` and selecting **Restart**.

### Uninstalling

Run the following command in command prompt:

```bat
taskkill /f /im PerformanceMonitor.exe
sc delete PerformanceMonitor
```

### Security & Privacy

- Built using Python and Flask for a **simple, local performance monitoring environment**.
- The tool runs entirely on your machine and **does not send any data over the internet** or access external servers.
- Performance statistics are collected locally and served only on `localhost`.
- The default endpoint (`http://127.0.0.1:5000/performance`) is only accessible from your own computer.
- Fully open-source, allowing you to inspect and verify the code at any time.

### Dependencies and References

- [Python 3.11+](https://www.python.org/)
- [Flask](https://github.com/pallets/flask)
- [Flask-CORS](https://github.com/corydolphin/flask-cors)
- [psutil](https://github.com/giampaolo/psutil)
- [GPUtil](https://github.com/anderskm/gputil)
- [pywin32](https://github.com/mhammond/pywin32)
- [PyInstaller](https://github.com/pyinstaller/pyinstaller)
- [Windows Services](https://docs.microsoft.com/en-us/windows/win32/services/services)
- [Wallpaper Engine](https://www.wallpaperengine.io/en)

### Contributing

- Create wallpapers compatible with this monitor by referring to the [next section](#accessing-performance-data-in-your-web-wallpaper).
- If you like my work, please consider:
  - Starring this project on GitHub
  - [![ko-fi](https://www.ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/sheeta)
- Stay tuned in [Sheeta's Discord Server](https://discord.gg/2dXs5HwXuW)

---

### Accessing Performance Data in Your Web Wallpaper

The Performance Monitor exposes system metrics via a local Flask server (default: `http://127.0.0.1:5000/performance`). You can fetch these metrics in your web wallpaper using standard JavaScript `fetch`.

#### Available Keys

| Key                                 | Description                             | Unit / Format |
| ----------------------------------- | --------------------------------------- | ------------- |
| `cpu`                               | Overall CPU usage percentage            | %             |
| `cpu_temp`                          | CPU package temperature (if available)  | °C            |
| `cpu_core0_temp` … `cpu_coreN_temp` | Temperature per CPU core (if available) | °C            |
| `memory`                            | RAM usage percentage                    | %             |
| `gpu_usage`                         | GPU usage percentage                    | %             |
| `vram_usage`                        | GPU memory usage percentage             | %             |
| `gpu_temp`                          | GPU temperature                         | °C            |
| `upload_speed`                      | Network upload speed                    | MB/s          |
| `download_speed`                    | Network download speed                  | MB/s          |
| `c_disk`, `d_disk`, …               | Disk usage in format "used GB/total GB" | GB            |
| `nvme_0_temp`, `disk_1_temp`, …     | Drive temperatures (if available)       | °C            |
| `timestamp`                         | UNIX timestamp of measurement           | seconds       |

#### Example Usage

```javascript
const port = 5000; // default port
const diskKeys = ["c", "d"]; // optional disks to check

async function fetchPerformance() {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/performance`);
    const data = await response.json();

    // CPU and RAM
    const cpuUsage = data.cpu; // e.g., 12.3
    const ramUsage = data.memory; // e.g., 68.4

    // GPU
    const gpuUsage = data.gpu_usage; // e.g., 6.0
    const vramUsage = data.vram_usage; // e.g., 11.0
    const gpuTemp = data.gpu_temp; // e.g., 47.0°C

    // Disk usage example
    diskKeys.forEach((disk) => {
      const key = `${disk}_disk`; // e.g., "c_disk"
      const usageText = data[key]; // "407.5 GB/488.4 GB"
      if (usageText) {
        const [used, total] = usageText.split("/").map((s) => parseFloat(s));
        const percent = Math.round((used / total) * 100);
        console.log(`${disk.toUpperCase()} usage: ${percent}% (${usageText})`);
      }
    });

    // Network speeds
    const download = data.download_speed; // MB/s
    const upload = data.upload_speed; // MB/s

    console.log({
      cpuUsage,
      ramUsage,
      gpuUsage,
      vramUsage,
      gpuTemp,
      download,
      upload,
    });
  } catch (err) {
    console.error("Failed to fetch performance data:", err);
  }
}

// Call periodically
setInterval(fetchPerformance, 1000);
```
