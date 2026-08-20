#!/usr/bin/env python3
"""Home-network baseline probe for before/after comparison.

Windows-first. Collects Wi-Fi, IPv6, latency, traceroute, DNS,
single vs parallel throughput, and a bufferbloat/RPM proxy.

Usage:
  py -3 scripts/standalone/net_home_probe.py --label baseline
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ipaddress
import json
import os
import re
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = REPO_ROOT / "results"
PING_COUNT = 20
TRACEROUTE_HOPS = 4
DNS_ROUNDS = 5
THROUGHPUT_BYTES = 25_000_000
THROUGHPUT_PARALLEL = 6
HTTP_TIMEOUT_S = 30
DOWNLOAD_URL = "https://speed.cloudflare.com/__down?bytes={bytes}"
RPM_PROBE_URL = "https://1.1.1.1/cdn-cgi/trace"
NETWORKQUALITY_CMD = "networkQuality"
BUFFERBLOAT_LOAD_BYTES = 200_000_000
BUFFERBLOAT_WINDOW_S = 8.0


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_cmd(args: list[str], timeout: int = 60) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "cmd": args,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = _decode(exc.stdout)
        stderr = _decode(exc.stderr)
        return {
            "cmd": args,
            "ok": False,
            "returncode": None,
            "stdout": stdout,
            "stderr": (stderr + "\nTIMEOUT").strip(),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    return {
        "cmd": args,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": _decode(proc.stdout),
        "stderr": _decode(proc.stderr),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def _decode(raw: bytes | None) -> str:
    if not raw:
        return ""
    for enc in ("utf-8", "cp932", "utf-16le"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def run_ps(script: str, timeout: int = 60) -> dict[str, Any]:
    return run_cmd(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        timeout=timeout,
    )


def parse_kv_block(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key:
            out[key] = value
    return out


def quality_to_rssi_dbm(quality: int | None) -> int | None:
    if quality is None:
        return None
    quality = max(0, min(100, quality))
    return int((quality / 2) - 100)


def collect_wifi() -> dict[str, Any]:
    interfaces = run_cmd(["netsh", "wlan", "show", "interfaces"], timeout=30)
    networks = run_cmd(
        ["netsh", "wlan", "show", "networks", "mode=bssid"],
        timeout=40,
    )
    kv = parse_kv_block(interfaces.get("stdout", ""))
    signal_raw = kv.get("Signal") or kv.get("信号")
    signal_pct = None
    if signal_raw:
        m = re.search(r"(\d+)", signal_raw)
        if m:
            signal_pct = int(m.group(1))
    rssi = quality_to_rssi_dbm(signal_pct)
    rx = _parse_mbps(kv.get("Receive rate (Mbps)") or kv.get("受信速度 (Mbps)"))
    tx = _parse_mbps(kv.get("Transmit rate (Mbps)") or kv.get("送信速度 (Mbps)"))
    channel = _parse_int(kv.get("Channel") or kv.get("チャネル"))
    radio = kv.get("Radio type") or kv.get("無線の種類")
    ssid = kv.get("SSID")
    bssid = kv.get("BSSID")
    state = kv.get("State") or kv.get("状態")
    band_mhz = _infer_channel_width_mhz(rx, radio)
    # Windows netsh does not expose noise floor. Leave explicit null.
    noise_dbm = None
    snr_db = None
    if rssi is not None and noise_dbm is not None:
        snr_db = rssi - noise_dbm
    connected_bssid_info = _match_bssid_from_scan(networks.get("stdout", ""), bssid)
    if channel is None:
        channel = connected_bssid_info.get("channel")
    return {
        "available": bool(ssid or state),
        "state": state,
        "ssid": ssid,
        "bssid": bssid,
        "radio_type": radio,
        "channel": channel,
        "channel_width_mhz": band_mhz,
        "channel_width_source": "inferred_from_link_rate" if band_mhz else None,
        "signal_pct": signal_pct,
        "rssi_dbm_estimated": rssi,
        "rssi_method": "microsoft_quality_to_rssi" if rssi is not None else None,
        "noise_dbm": noise_dbm,
        "snr_db": snr_db,
        "noise_snr_note": "Windows netsh does not expose noise/SNR; left null.",
        "rx_mbps": rx,
        "tx_mbps": tx,
        "profile": kv.get("Profile") or kv.get("プロファイル"),
        "authentication": kv.get("Authentication") or kv.get("認証"),
        "cipher": kv.get("Cipher") or kv.get("暗号化"),
        "scan_match": connected_bssid_info,
        "raw_interfaces": interfaces.get("stdout", "")[:4000],
        "cmd_ok": interfaces.get("ok"),
    }


def _parse_mbps(value: str | None) -> float | None:
    if not value:
        return None
    m = re.search(r"([\d.]+)", value.replace(",", ""))
    return float(m.group(1)) if m else None


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    m = re.search(r"(-?\d+)", value)
    return int(m.group(1)) if m else None


def _infer_channel_width_mhz(rx_mbps: float | None, radio: str | None) -> int | None:
    if rx_mbps is None:
        return None
    radio_l = (radio or "").lower()
    if "ax" in radio_l or "be" in radio_l or "ac" in radio_l:
        if rx_mbps >= 1700:
            return 160
        if rx_mbps >= 800:
            return 80
        if rx_mbps >= 300:
            return 40
        return 20
    if "n" in radio_l:
        return 40 if rx_mbps >= 150 else 20
    return None


def _match_bssid_from_scan(text: str, bssid: str | None) -> dict[str, Any]:
    if not text or not bssid:
        return {}
    target = bssid.lower()
    current: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("BSSID") or stripped.startswith("BSSID"):
            if current.get("bssid", "").lower() == target:
                return current
            current = {"bssid": stripped.split(":", 1)[-1].strip()}
        elif ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip().lower()] = value.strip()
            if key.strip().lower() in {"channel", "チャネル"}:
                current["channel"] = _parse_int(value)
            if "mhz" in value.lower() and "channel" in key.lower():
                current["channel_width_mhz"] = _parse_int(value)
    if current.get("bssid", "").lower() == target:
        return current
    return {}


def collect_ipv6_and_routes() -> dict[str, Any]:
    ipconfig = run_cmd(["ipconfig", "/all"], timeout=20)
    route_print = run_cmd(["route", "print"], timeout=20)
    v6_addrs_cmd = run_cmd(["netsh", "interface", "ipv6", "show", "addresses"], timeout=20)
    v6_routes_cmd = run_cmd(["netsh", "interface", "ipv6", "show", "route"], timeout=20)
    text = ipconfig.get("stdout", "")

    adapters = _parse_ipconfig(text)
    global_v6 = []
    ula_v6 = []
    link_v6 = []
    ipv4s = []
    dns_servers: list[dict[str, Any]] = []
    for adapter in adapters:
        name = adapter.get("name")
        for ip in adapter.get("ipv6", []):
            rec = {"interface": name, "ip": ip}
            try:
                parsed = ipaddress.ip_address(ip.split("%")[0])
            except Exception:
                continue
            if parsed.is_loopback:
                continue
            if parsed.is_link_local:
                link_v6.append(rec)
            elif parsed.is_private:
                ula_v6.append(rec)
            elif parsed.is_global or str(parsed).startswith(("2", "3")):
                global_v6.append(rec)
        for ip in adapter.get("ipv4", []):
            if not ip.startswith("127."):
                ipv4s.append({"interface": name, "ip": ip})
        if adapter.get("dns"):
            dns_servers.append({"interface": name, "servers": adapter.get("dns")})

    default_v4 = _parse_route_print_defaults(route_print.get("stdout", ""))
    default_v6 = _parse_netsh_v6_default(v6_routes_cmd.get("stdout", ""))

    return {
        "global_ipv6_present": bool(global_v6),
        "global_ipv6": global_v6,
        "ula_ipv6": ula_v6,
        "linklocal_ipv6": link_v6,
        "default_route_v4": default_v4,
        "default_route_v6": default_v6,
        "default_route_v6_present": bool(default_v6),
        "ipv4_addresses": ipv4s,
        "dns_servers": dns_servers,
        "adapters": adapters,
        "cmd_ok": ipconfig.get("ok"),
        "raw_ipconfig": text[:6000],
        "raw_v6_addrs": (v6_addrs_cmd.get("stdout") or "")[:2000],
        "raw_v6_routes": (v6_routes_cmd.get("stdout") or "")[:2000],
    }


def _parse_ipconfig(text: str) -> list[dict[str, Any]]:
    adapters: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        header = re.match(r"^(.+?アダプター|.+?adapter)\s+(.+):\s*$", line, flags=re.I)
        if header or (line.endswith(":") and line.strip() and not line.startswith(" ")):
            if current:
                adapters.append(current)
            name = header.group(2).strip() if header else line.strip().rstrip(":")
            current = {
                "name": name,
                "header": line.strip(),
                "ipv4": [],
                "ipv6": [],
                "dns": [],
                "gateway": [],
                "dns_suffix": None,
                "media_state": None,
                "description": None,
            }
            continue
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key_s = key.strip()
        value = value.strip()
        if not value:
            continue
        key_l = key_s.lower()
        if "IPv4" in key_s or "ip address" in key_l and "v6" not in key_l:
            ip = value.split("(")[0].strip()
            if re.match(r"\d+\.\d+\.\d+\.\d+", ip):
                current["ipv4"].append(ip)
        elif "IPv6" in key_s or "ipv6 address" in key_l:
            current["ipv6"].append(value.split("(")[0].strip())
        elif "DNS サフィックス" in key_s or "dns suffix" in key_l:
            current["dns_suffix"] = value
        elif "DNS サーバー" in key_s or "dns server" in key_l:
            current["dns"].append(value)
        elif "デフォルト ゲートウェイ" in key_s or "default gateway" in key_l:
            current["gateway"].append(value)
        elif "メディアの状態" in key_s or "media state" in key_l:
            current["media_state"] = value
        elif key_s in {"説明", "Description"}:
            current["description"] = value
        elif re.match(r"^\s+\S", line) and current["dns"] and re.search(r"[:0-9a-fA-F.]", value):
            # continuation line for extra DNS servers
            if ":" in value or re.match(r"\d+\.\d+\.\d+\.\d+", value):
                current["dns"].append(value)
    if current:
        adapters.append(current)
    return adapters


def _parse_route_print_defaults(text: str) -> list[dict[str, Any]]:
    defaults = []
    in_v4 = False
    for line in text.splitlines():
        if "IPv4 ルート" in line or "IPv4 Route" in line:
            in_v4 = True
            continue
        if "IPv6 ルート" in line or "IPv6 Route" in line:
            in_v4 = False
        if not in_v4:
            continue
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
            defaults.append(
                {
                    "interface": None,
                    "destination": "0.0.0.0/0",
                    "nexthop": parts[2],
                    "metric": parts[-1],
                    "raw": line.strip(),
                }
            )
    return defaults


def _parse_netsh_v6_default(text: str) -> list[dict[str, Any]]:
    defaults = []
    for line in text.splitlines():
        if "::/0" not in line:
            continue
        parts = line.split()
        hop = None
        for token in parts:
            if ":" in token and token not in {"::/0"} and not token.endswith("/0"):
                hop = token
                break
        defaults.append({"destination": "::/0", "nexthop": hop, "raw": line.strip()})
    return defaults


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _ping_stats(host: str, count: int = PING_COUNT, timeout_ms: int = 1000) -> dict[str, Any]:
    # Windows ping
    result = run_cmd(
        ["ping", "-n", str(count), "-w", str(timeout_ms), host],
        timeout=max(30, count * 2 + 10),
    )
    text = result.get("stdout", "")
    rtts = [
        float(x)
        for x in re.findall(r"(?:時間|time)\s*[=<]\s*(\d+)\s*ms", text, flags=re.I)
    ]
    if not rtts:
        summary = re.search(r"(?:平均|Average)\s*=\s*(\d+)\s*ms", text, flags=re.I)
        mx = re.search(r"(?:最大|Maximum)\s*=\s*(\d+)\s*ms", text, flags=re.I)
        mn = re.search(r"(?:最小|Minimum)\s*=\s*(\d+)\s*ms", text, flags=re.I)
        if summary:
            rtts = [float(summary.group(1))]
            if mx:
                rtts.append(float(mx.group(1)))
            if mn:
                rtts.append(float(mn.group(1)))
    sent = count
    recv_m = re.search(r"(?:受信|Received)\s*=\s*(\d+)", text, flags=re.I)
    lost_m = re.search(r"(?:損失|Lost)\s*=\s*(\d+)", text, flags=re.I)
    received = int(recv_m.group(1)) if recv_m else len(rtts)
    lost = int(lost_m.group(1)) if lost_m else max(0, sent - received)
    loss_pct = (lost / sent * 100.0) if sent else None
    return {
        "host": host,
        "sent": sent,
        "received": received,
        "lost": lost,
        "loss_pct": round(loss_pct, 2) if loss_pct is not None else None,
        "avg_ms": round(statistics.mean(rtts), 2) if rtts else None,
        "max_ms": max(rtts) if rtts else None,
        "min_ms": min(rtts) if rtts else None,
        "stdev_ms": round(statistics.pstdev(rtts), 2) if len(rtts) >= 2 else (0.0 if rtts else None),
        "samples_ms": rtts,
        "cmd_ok": result.get("ok"),
        "raw_tail": "\n".join(text.splitlines()[-8:]),
    }


def collect_latency(gateway: str | None) -> dict[str, Any]:
    targets = []
    if gateway:
        targets.append(("default_gateway", gateway))
    targets.extend(
        [
            ("cloudflare_1.1.1.1", "1.1.1.1"),
            ("google_8.8.8.8", "8.8.8.8"),
            ("cloudflare_v6", "2606:4700:4700::1111"),
        ]
    )
    out = {}
    for name, host in targets:
        out[name] = _ping_stats(host)
    return out


def collect_link_speed() -> dict[str, Any]:
    wmic = run_cmd(
        [
            "wmic",
            "nic",
            "where",
            "NetEnabled=true",
            "get",
            "Name,Speed,MACAddress,AdapterType",
            "/format:list",
        ],
        timeout=25,
    )
    nics = []
    current: dict[str, Any] = {}
    for line in (wmic.get("stdout") or "").splitlines():
        if "=" not in line:
            if current:
                nics.append(current)
                current = {}
            continue
        key, value = line.split("=", 1)
        current[key.strip()] = value.strip()
    if current:
        nics.append(current)
    for nic in nics:
        try:
            spd = int(nic.get("Speed") or 0)
        except ValueError:
            spd = 0
        nic["speed_mbps"] = round(spd / 1_000_000, 1) if spd else None
    return {"nics": nics, "cmd_ok": wmic.get("ok"), "raw": (wmic.get("stdout") or "")[:2000]}


def collect_traceroute() -> dict[str, Any]:
    result = run_cmd(
        ["tracert", "-d", "-h", str(TRACEROUTE_HOPS), "-w", "3000", "1.1.1.1"],
        timeout=50,
    )
    named = run_cmd(
        ["tracert", "-h", "6", "-w", "2000", "1.1.1.1"],
        timeout=50,
    )
    v6 = run_cmd(
        ["tracert", "-6", "-d", "-h", str(TRACEROUTE_HOPS), "-w", "3000", "2606:4700:4700::1111"],
        timeout=50,
    )
    hops = []
    for line in result.get("stdout", "").splitlines():
        m = re.match(r"\s*(\d+)\s+(.+)$", line)
        if not m:
            continue
        hop_n = int(m.group(1))
        rest = m.group(2)
        times = re.findall(r"(\d+)\s*ms", rest)
        ip_m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", rest)
        hops.append(
            {
                "hop": hop_n,
                "ip": ip_m.group(1) if ip_m else None,
                "rtts_ms": [int(x) for x in times],
                "avg_ms": round(sum(int(x) for x in times) / len(times), 1) if times else None,
                "timeout": "*" in rest and not times,
                "raw": line.strip(),
            }
        )
        if hop_n >= TRACEROUTE_HOPS:
            break
    named_hops = []
    for line in named.get("stdout", "").splitlines():
        m = re.match(r"\s*(\d+)\s+(.+)$", line)
        if not m:
            continue
        named_hops.append({"hop": int(m.group(1)), "raw": line.strip()})
        if int(m.group(1)) >= 6:
            break
    v6_hops = []
    for line in v6.get("stdout", "").splitlines():
        m = re.match(r"\s*(\d+)\s+(.+)$", line)
        if not m:
            continue
        hop_n = int(m.group(1))
        rest = m.group(2)
        times = re.findall(r"(\d+)\s*ms", rest)
        ip_m = re.search(r"([0-9a-fA-F:]+:+[0-9a-fA-F:]+)", rest)
        v6_hops.append(
            {
                "hop": hop_n,
                "ip": ip_m.group(1) if ip_m else None,
                "rtts_ms": [int(x) for x in times],
                "avg_ms": round(sum(int(x) for x in times) / len(times), 1) if times else None,
                "timeout": "*" in rest and not times,
                "raw": line.strip(),
            }
        )
        if hop_n >= TRACEROUTE_HOPS:
            break
    return {
        "target": "1.1.1.1",
        "max_hops": TRACEROUTE_HOPS,
        "hops": hops[:TRACEROUTE_HOPS],
        "named_hops": named_hops,
        "ipv6_target": "2606:4700:4700::1111",
        "ipv6_hops": v6_hops[:TRACEROUTE_HOPS],
        "cmd_ok": result.get("ok"),
        "raw": result.get("stdout", "")[:3000],
        "raw_named": named.get("stdout", "")[:2500],
        "raw_ipv6": v6.get("stdout", "")[:2500],
    }


def _dns_query_once(resolver: str, name: str) -> dict[str, Any]:
    started = time.perf_counter()
    # nslookup server-specific query
    result = run_cmd(["nslookup", "-timeout=3", name, resolver], timeout=12)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    text = result.get("stdout", "") + "\n" + result.get("stderr", "")
    addrs = re.findall(r"Addresses?:\s*([0-9a-fA-F:.]+)", text)
    extra = re.findall(r"^\s+([0-9a-fA-F:.]+)\s*$", text, flags=re.M)
    answers = [a for a in addrs + extra if a != resolver and a.lower() not in {"::1", "127.0.0.1"}]
    # drop resolver echo if nslookup printed it as Address:
    timed_out = "timed out" in text.lower() or "タイムアウト" in text
    ok = (bool(answers) or ("名前:" in text) or ("Name:" in text)) and not timed_out
    if ok and not answers:
        answers = ["resolved_but_unparsed"]
    return {
        "ok": ok,
        "elapsed_ms": elapsed_ms,
        "answers": answers[:6],
        "timeout": timed_out,
        "raw_tail": "\n".join(text.splitlines()[:12]),
    }


def collect_dns(router: str | None) -> dict[str, Any]:
    resolvers = []
    if router:
        resolvers.append(("router", router))
    resolvers.extend([("cloudflare", "1.1.1.1"), ("google", "8.8.8.8")])
    name = "www.cloudflare.com"
    out: dict[str, Any] = {"query_name": name, "rounds": DNS_ROUNDS, "resolvers": {}}
    for label, server in resolvers:
        samples = [_dns_query_once(server, name) for _ in range(DNS_ROUNDS)]
        ok_ms = [s["elapsed_ms"] for s in samples if s["ok"]]
        out["resolvers"][label] = {
            "server": server,
            "avg_ms": round(statistics.mean(ok_ms), 1) if ok_ms else None,
            "max_ms": max(ok_ms) if ok_ms else None,
            "min_ms": min(ok_ms) if ok_ms else None,
            "successes": len(ok_ms),
            "failures": len(samples) - len(ok_ms),
            "samples": samples,
        }
    return out


def _download_once(url: str, timeout: int = HTTP_TIMEOUT_S) -> dict[str, Any]:
    started = time.perf_counter()
    bytes_got = 0
    status = None
    err = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "net-home-probe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None)
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                bytes_got += len(chunk)
    except Exception as exc:  # noqa: BLE001 - probe must record any failure
        err = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - started
    mbps = (bytes_got * 8 / elapsed / 1_000_000) if elapsed > 0 and bytes_got else None
    return {
        "url": url,
        "bytes": bytes_got,
        "elapsed_s": round(elapsed, 3),
        "mbps": round(mbps, 2) if mbps is not None else None,
        "http_status": status,
        "error": err,
    }


def collect_upload() -> dict[str, Any]:
    url = "https://speed.cloudflare.com/__up"
    payload = b"x" * 20_000_000
    started = time.perf_counter()
    status = None
    err = None
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "User-Agent": "net-home-probe/1.0",
                "Content-Type": "application/octet-stream",
            },
        )
        with urllib.request.urlopen(req, timeout=40) as resp:
            status = getattr(resp, "status", None)
            resp.read(256)
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - started
    mbps = (len(payload) * 8 / elapsed / 1_000_000) if elapsed > 0 and err is None else None
    return {
        "url": url,
        "bytes": len(payload),
        "elapsed_s": round(elapsed, 3),
        "mbps": round(mbps, 2) if mbps is not None else None,
        "http_status": status,
        "error": err,
    }


def collect_throughput() -> dict[str, Any]:
    url = DOWNLOAD_URL.format(bytes=THROUGHPUT_BYTES)
    single = _download_once(url, timeout=60)
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=THROUGHPUT_PARALLEL) as pool:
        futs = [pool.submit(_download_once, url, 60) for _ in range(THROUGHPUT_PARALLEL)]
        parts = [f.result() for f in futs]
    wall = time.perf_counter() - started
    total_bytes = sum(p["bytes"] for p in parts)
    agg_mbps = (total_bytes * 8 / wall / 1_000_000) if wall > 0 else None
    return {
        "url": url,
        "requested_bytes_each": THROUGHPUT_BYTES,
        "single": single,
        "parallel": {
            "workers": THROUGHPUT_PARALLEL,
            "wall_s": round(wall, 3),
            "total_bytes": total_bytes,
            "aggregate_mbps": round(agg_mbps, 2) if agg_mbps is not None else None,
            "per_connection": parts,
        },
    }


def collect_bufferbloat(idle_avg_ms: float | None) -> dict[str, Any]:
    nq = run_cmd([NETWORKQUALITY_CMD, "-s"], timeout=45)
    network_quality: dict[str, Any] = {
        "available": nq.get("ok") and "not recognized" not in (nq.get("stderr") or "").lower(),
        "stdout": nq.get("stdout", "")[:3000],
        "stderr": nq.get("stderr", "")[:1000],
        "note": "macOS networkQuality; expected unavailable on Windows.",
    }
    rpm_from_nq = None
    idle_from_nq = None
    if network_quality["available"]:
        text = nq.get("stdout") or ""
        m_rpm = re.search(r"Responsiveness:\s*(\d+(?:\.\d+)?)\s*RPM", text, re.I)
        m_idle = re.search(r"Idle Latency:\s*(\d+(?:\.\d+)?)\s*ms", text, re.I)
        rpm_from_nq = float(m_rpm.group(1)) if m_rpm else None
        idle_from_nq = float(m_idle.group(1)) if m_idle else None

    # Cross-platform RPM proxy: HTTP GETs while a download saturates the path.
    load_url = DOWNLOAD_URL.format(bytes=BUFFERBLOAT_LOAD_BYTES)

    def _loader() -> dict[str, Any]:
        return _download_once(load_url, timeout=60)

    loader_fut: concurrent.futures.Future[dict[str, Any]]
    probe_rtts: list[float] = []
    probe_errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        loader_fut = pool.submit(_loader)
        time.sleep(0.2)
        deadline = time.perf_counter() + BUFFERBLOAT_WINDOW_S
        while time.perf_counter() < deadline:
            if loader_fut.done() and time.perf_counter() > deadline - BUFFERBLOAT_WINDOW_S + 1:
                break
            t0 = time.perf_counter()
            try:
                req = urllib.request.Request(
                    RPM_PROBE_URL,
                    headers={"User-Agent": "net-home-probe/1.0"},
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    resp.read(256)
                probe_rtts.append((time.perf_counter() - t0) * 1000)
            except Exception:
                probe_errors += 1
            if loader_fut.done() and len(probe_rtts) >= 8:
                break
        load_result = loader_fut.result(timeout=70)

    loaded_avg = round(statistics.mean(probe_rtts), 2) if probe_rtts else None
    loaded_max = max(probe_rtts) if probe_rtts else None
    # Apple RPM ≈ successful small transactions per minute under working-load.
    rpm_proxy = None
    if probe_rtts:
        mean_s = statistics.mean(probe_rtts) / 1000.0
        if mean_s > 0:
            rpm_proxy = round(60.0 / mean_s, 1)
    delta = None
    if loaded_avg is not None and idle_avg_ms is not None:
        delta = round(loaded_avg - idle_avg_ms, 2)

    return {
        "networkQuality": {
            **network_quality,
            "rpm": rpm_from_nq,
            "idle_latency_ms": idle_from_nq,
        },
        "loaded_http_probe": {
            "probe_url": RPM_PROBE_URL,
            "samples_ms": [round(x, 1) for x in probe_rtts],
            "successes": len(probe_rtts),
            "errors": probe_errors,
            "loaded_avg_ms": loaded_avg,
            "loaded_max_ms": loaded_max,
            "idle_avg_ms": idle_avg_ms,
            "loaded_minus_idle_ms": delta,
            "rpm_proxy": rpm_proxy,
            "rpm_proxy_definition": "60 / mean_loaded_http_rtt_s while a single 40MB download is in flight",
            "load_download": load_result,
        },
    }


def pick_gateway(netinfo: dict[str, Any]) -> str | None:
    for rec in netinfo.get("default_route_v4") or []:
        hop = rec.get("nexthop")
        if hop and hop not in {"0.0.0.0", "On-link"}:
            if hop.startswith("192.168.") or hop.startswith("10.") or hop.startswith("172."):
                return hop
    for rec in netinfo.get("default_route_v4") or []:
        hop = rec.get("nexthop")
        if hop and hop not in {"0.0.0.0", "On-link"}:
            return hop
    for adapter in netinfo.get("adapters") or []:
        name = str(adapter.get("name") or "")
        if "Tailscale" in name or "WSL" in name or "Loopback" in name:
            continue
        for gw in adapter.get("gateway") or []:
            if re.match(r"\d+\.\d+\.\d+\.\d+", gw):
                return gw
    return None


def public_ip_hints() -> dict[str, Any]:
    hints = {}
    for label, url in (
        ("ipv4", "https://1.1.1.1/cdn-cgi/trace"),
        ("cloudflare_meta", "https://speed.cloudflare.com/meta"),
    ):
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "net-home-probe/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read(4000).decode("utf-8", errors="replace")
            hints[label] = {
                "ok": True,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                "body": body[:1500],
            }
        except Exception as exc:  # noqa: BLE001
            hints[label] = {
                "ok": False,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                "error": f"{type(exc).__name__}: {exc}",
            }
    return hints


def build_report(label: str) -> dict[str, Any]:
    started = time.perf_counter()
    wifi = collect_wifi()
    netinfo = collect_ipv6_and_routes()
    link = collect_link_speed()
    gateway = pick_gateway(netinfo)
    latency = collect_latency(gateway)
    traceroute = collect_traceroute()
    dns = collect_dns(gateway)
    throughput = collect_throughput()
    upload = collect_upload()
    idle_inet = None
    if latency.get("cloudflare_1.1.1.1", {}).get("avg_ms") is not None:
        idle_inet = latency["cloudflare_1.1.1.1"]["avg_ms"]
    bufferbloat = collect_bufferbloat(idle_inet)
    public = public_ip_hints()
    elapsed = round(time.perf_counter() - started, 2)
    return {
        "schema": "net_home_probe/v1",
        "label": label,
        "captured_at": now_iso(),
        "hostname": socket.gethostname(),
        "platform": sys.platform,
        "probe_seconds": elapsed,
        "wifi": wifi,
        "ipv6": {
            "global_address_present": netinfo.get("global_ipv6_present"),
            "default_route_present": netinfo.get("default_route_v6_present"),
            "global_addresses": netinfo.get("global_ipv6"),
            "default_routes": netinfo.get("default_route_v6"),
        },
        "l3": {
            "gateway_v4": gateway,
            "default_routes_v4": netinfo.get("default_route_v4"),
            "ipv4_addresses": netinfo.get("ipv4_addresses"),
            "adapters": netinfo.get("adapters"),
            "dns_servers": netinfo.get("dns_servers"),
            "link_speed": link,
        },
        "latency": latency,
        "traceroute_first4": traceroute,
        "dns": dns,
        "throughput": throughput,
        "upload": upload,
        "bufferbloat": bufferbloat,
        "public_hints": public,
    }


def save_report(report: dict[str, Any], results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    safe_label = re.sub(r"[^A-Za-z0-9._-]+", "-", report["label"]).strip("-") or "unlabeled"
    path = results_dir / f"net_home_probe_{safe_label}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = results_dir / f"net_home_probe_{safe_label}_latest.json"
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Home network baseline probe")
    parser.add_argument("--label", default="baseline", help="Comparison label, e.g. before-move / after-channel")
    parser.add_argument(
        "--results-dir",
        default=str(DEFAULT_RESULTS),
        help="Directory for JSON output",
    )
    args = parser.parse_args()
    report = build_report(args.label)
    path = save_report(report, Path(args.results_dir))
    summary = {
        "saved": str(path),
        "label": report["label"],
        "captured_at": report["captured_at"],
        "wifi_signal_pct": report["wifi"].get("signal_pct"),
        "wifi_rx_mbps": report["wifi"].get("rx_mbps"),
        "ipv6_global": report["ipv6"].get("global_address_present"),
        "ipv6_default_route": report["ipv6"].get("default_route_present"),
        "gw_avg_ms": (report["latency"].get("default_gateway") or {}).get("avg_ms"),
        "cf_avg_ms": (report["latency"].get("cloudflare_1.1.1.1") or {}).get("avg_ms"),
        "single_mbps": report["throughput"]["single"].get("mbps"),
        "parallel_mbps": report["throughput"]["parallel"].get("aggregate_mbps"),
        "upload_mbps": (report.get("upload") or {}).get("mbps"),
        "rpm_proxy": report["bufferbloat"]["loaded_http_probe"].get("rpm_proxy"),
        "nq_available": report["bufferbloat"]["networkQuality"].get("available"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"FULL_JSON={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
