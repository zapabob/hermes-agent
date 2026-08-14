Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinAPI2 {
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    public static IntPtr HWND_TOP = new IntPtr(0);
    public static uint SWP_SHOWWINDOW = 0x0040;
    public static uint SWP_NOACTIVATE = 0x0010;
    public static uint SWP_NOZORDER = 0x0004;
    public static int SW_RESTORE = 9;
    public static int SW_SHOW = 5;
}
'@

# Window handles (decimal from list_windows)
$xHwnd = [IntPtr]8718300   # X/Twitter window
$ytHwnd = [IntPtr]788182   # YouTube window

$screenW = 1920
$screenH = 1080
$topH = [int]($screenH / 2)   # 540
$botH = $screenH - $topH      # 540

# Restore windows first
[WinAPI2]::ShowWindow($xHwnd, [WinAPI2]::SW_RESTORE)
[WinAPI2]::ShowWindow($ytHwnd, [WinAPI2]::SW_RESTORE)

# Position X at top half
[WinAPI2]::MoveWindow($xHwnd, 0, 0, $screenW, $topH, $true)

# Position YouTube at bottom half
[WinAPI2]::MoveWindow($ytHwnd, 0, $topH, $screenW, $botH, $true)

Write-Host "Done! X top: 0,0 ${screenW}x${topH} | YouTube bottom: 0,${topH} ${screenW}x${botH}"
