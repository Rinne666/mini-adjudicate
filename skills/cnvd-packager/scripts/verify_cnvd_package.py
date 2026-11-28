#!/usr/bin/env python3
"""CNVD package and reproduction video verification gate (stdlib + ffmpeg/ffprobe).

Enforces deterministic quality invariants aligned with the JFlow-精简版 standard
without requiring third-party Python imaging or numerical packages:

  1. Package structure: 报告.docx (3-section), PoC.md, executable PoC.sh,
     复现视频.mp4 (or 实测响应.txt when --allow-no-video), and 截图/*.png
     with 1:1 SHA-256 parity against images embedded in 报告.docx.
  2. Report hygiene: rejects CVSS tables, standalone PoC chapters, and
     subjective severity-grading terms inside 报告.docx.
  3. Video technical floor: H.264 + AAC, fps >= 24, audio sample rate >= 24 kHz,
     audio/video duration alignment, active speech presence.
  4. Motion & anti-freeze check: rejects "2fps instant finish + 30s frozen frame"
     by verifying multiple distinct transitions and late-video visual activity.
  5. Blank / calibration / cross-video contamination check: rejects pure solid
     green/blue/white/black boundary frames and, in --batch mode, detects when
     video i starts (0.0s) with another vulnerability's frame.
  6. Optional storyboard/align checks: rejects batch numbering ("第1项"/"第一条")
     in narration, flags raw technical tokens in TTS text, and checks audio-step
     envelope sync at step anchors.
  7. Web-track visual checks: zero-overlay and real browser toolbar
     (supports both Dark Mode and Light Mode Chrome, even with long URLs).
"""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

REQUIRED_SECTIONS = [
    "一、源码成因",
    "二、复现步骤与关键截图",
    "三、修复建议",
]
REQUIRED_META_PREFIXES = [
    "源码地址：",
    "影响版本：",
    "受影响端点：",
    "所需权限：",
]
FORBIDDEN_HEADING_PATTERNS = [
    re.compile(r"CVSS", re.IGNORECASE),
    re.compile(r"^(?:[一二三四五六七八九十]+、|\d+[\.、])\s*(?:独立\s*)?(?:漏洞\s*)?PoC\b", re.IGNORECASE),
]
FORBIDDEN_GRADING_PATTERNS = [
    re.compile(r"风险等级|定级|危险等级|严重性|危害等级"),
    re.compile(r"高危|中危|低危|严重"),
    re.compile(r"(?:^|[^A-Za-z])Critical(?:[^A-Za-z]|$)"),
]
BATCH_PREFIX_RE = re.compile(r"^\s*第\s*[一二三四五六七八九十百零0-9]+\s*[条项个篇]")
RAW_TTS_TOKEN_RE = re.compile(
    r"(?:[a-z]+-[a-z0-9-]+|[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*|[a-z]+_[a-z0-9_]+|[A-Z]{2,}-[A-Za-z0-9-]+)"
)


def _run(cmd: list[str], *, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=text, check=False)


def _require_tooling() -> tuple[str, str]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required on PATH to verify CNVD packages")
    return ffmpeg, ffprobe


def _parse_rate(rate_str: str) -> float:
    if not rate_str or rate_str == "0/0":
        return 0.0
    if "/" in rate_str:
        num, den = rate_str.split("/", 1)
        d = float(den)
        return float(num) / d if d else 0.0
    return float(rate_str)


def probe_media(ffprobe: str, video: Path) -> dict:
    proc = _run([
        ffprobe, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(video),
    ])
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"ffprobe failed for {video}: {proc.stderr.strip()}")
    data = json.loads(proc.stdout)
    v_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    a_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    fmt = data.get("format", {})
    return {
        "format_duration": float(fmt.get("duration") or 0.0),
        "size_bytes": int(fmt.get("size") or 0),
        "video": v_streams[0] if v_streams else None,
        "audio": a_streams[0] if a_streams else None,
    }


def extract_rgb_frame(ffmpeg: str, video: Path, timestamp: float, width: int, height: int) -> bytes:
    proc = _run([
        ffmpeg, "-v", "error", "-ss", f"{max(0.0, timestamp):.3f}",
        "-i", str(video), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ], text=False)
    expected = width * height * 3
    if proc.returncode != 0 or len(proc.stdout) < expected:
        raise RuntimeError(f"failed extracting RGB frame at {timestamp:.2f}s from {video}")
    return proc.stdout[:expected]


def extract_last_rgb_frame(
    ffmpeg: str, video: Path, v_dur: float, avg_fps: float, width: int, height: int
) -> bytes:
    # For low-fps videos (e.g. 2fps), seeking to dur - 0.15s can overshoot the final frame PTS.
    back = max(0.25, 1.5 / max(1.0, avg_fps))
    target_ts = max(0.0, v_dur - back)
    try:
        return extract_rgb_frame(ffmpeg, video, target_ts, width, height)
    except RuntimeError:
        proc = _run([
            ffmpeg, "-v", "error", "-sseof", "-1.5",
            "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ], text=False)
        expected = width * height * 3
        if proc.returncode == 0 and len(proc.stdout) >= expected:
            offset = (len(proc.stdout) // expected - 1) * expected
            return proc.stdout[offset:offset + expected]
        raise


def extract_gray_timeline(
    ffmpeg: str, video: Path, sample_fps: float = 2.0, tw: int = 320, th: int = 180
) -> list[bytes]:
    proc = _run([
        ffmpeg, "-v", "error", "-i", str(video),
        "-vf", f"fps={sample_fps},scale={tw}:{th}",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ], text=False)
    if proc.returncode != 0:
        raise RuntimeError(f"failed extracting timeline frames from {video}")
    frame_size = tw * th
    raw = proc.stdout
    count = len(raw) // frame_size
    return [raw[i * frame_size:(i + 1) * frame_size] for i in range(count)]


def extract_audio_envelope(ffmpeg: str, video: Path, win_sec: float = 0.05) -> tuple[list[float], float]:
    proc = _run([
        ffmpeg, "-v", "error", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-",
    ], text=False)
    if proc.returncode != 0 or not proc.stdout:
        return [], win_sec
    samples = array.array("h")
    usable = len(proc.stdout) - (len(proc.stdout) % 2)
    samples.frombytes(proc.stdout[:usable])
    step = max(1, int(win_sec * 16000))
    env: list[float] = []
    for i in range(0, len(samples) - step + 1, step):
        seg = samples[i:i + step]
        sq = sum(v * v for v in seg)
        env.append(math.sqrt(sq / len(seg)))
    return env, win_sec


def gray_stats(buf: bytes) -> tuple[float, float]:
    n = len(buf)
    if not n:
        return 0.0, 0.0
    mean = sum(buf) / n
    var = sum((b - mean) ** 2 for b in buf) / n
    return mean, math.sqrt(var)


def frame_diff_metrics(a: bytes, b: bytes, pixel_thr: int = 18) -> tuple[float, float]:
    n = min(len(a), len(b))
    if not n:
        return 0.0, 0.0
    changed = 0
    mad_sum = 0
    for x, y in zip(a, b):
        d = abs(x - y)
        mad_sum += d
        if d > pixel_thr:
            changed += 1
    return changed / n, mad_sum / n


def region_mean_rgb(buf: bytes, width: int, height: int, frac_box: tuple[float, float, float, float]) -> float:
    x0 = max(0, min(width - 1, int(frac_box[0] * width)))
    y0 = max(0, min(height - 1, int(frac_box[1] * height)))
    x1 = max(x0 + 1, min(width, int(frac_box[2] * width)))
    y1 = max(y0 + 1, min(height, int(frac_box[3] * height)))
    total = 0
    count = 0
    stride = width * 3
    for y in range(y0, y1):
        row_start = y * stride + x0 * 3
        row_end = y * stride + x1 * 3
        row = buf[row_start:row_end]
        total += sum(row)
        count += len(row)
    return total / count if count else 0.0


def region_rgb_channel_means(
    buf: bytes, width: int, height: int, frac_box: tuple[float, float, float, float]
) -> tuple[float, float, float]:
    x0 = max(0, min(width - 1, int(frac_box[0] * width)))
    y0 = max(0, min(height - 1, int(frac_box[1] * height)))
    x1 = max(x0 + 1, min(width, int(frac_box[2] * width)))
    y1 = max(y0 + 1, min(height, int(frac_box[3] * height)))
    r_sum = g_sum = b_sum = px = 0
    stride = width * 3
    for y in range(y0, y1):
        row = buf[y * stride + x0 * 3:y * stride + x1 * 3]
        r_sum += sum(row[0::3])
        g_sum += sum(row[1::3])
        b_sum += sum(row[2::3])
        px += len(row) // 3
    return (r_sum / px, g_sum / px, b_sum / px) if px else (0.0, 0.0, 0.0)


def is_calibration_or_blank(rgb_buf: bytes, width: int, height: int) -> str | None:
    r, g, b = region_rgb_channel_means(rgb_buf, width, height, (0.1, 0.15, 0.9, 0.85))
    # Pure green calibration (#00FF00) or pure blue calibration (#0000FF)
    if g > 180 and r < 50 and b < 50:
        return f"纯绿标定帧残留 (R={r:.0f}, G={g:.0f}, B={b:.0f})"
    if b > 180 and r < 50 and g < 50:
        return f"纯蓝标定帧残留 (R={r:.0f}, G={g:.0f}, B={b:.0f})"
    gray = bytes((rb + gb + bb) // 3 for rb, gb, bb in zip(rgb_buf[0::3], rgb_buf[1::3], rgb_buf[2::3]))
    mean, stdev = gray_stats(gray)
    if stdev < 4.0 and mean > 246:
        return f"纯白空白页 (如 about:blank, mean={mean:.1f}, stdev={stdev:.1f})"
    if stdev < 4.0 and mean < 10:
        return f"纯黑帧 (mean={mean:.1f}, stdev={stdev:.1f})"
    return None


def analyze_motion(gray_frames: list[bytes], sample_fps: float, total_dur: float) -> dict:
    if len(gray_frames) < 2:
        return {
            "transition_times": [],
            "distinct_steps": 0,
            "last_change_t": 0.0,
            "last_change_ratio": 0.0,
            "max_freeze_sec": total_dur,
            "max_freeze_ratio": 1.0,
        }
    changes: list[float] = []
    for i in range(1, len(gray_frames)):
        frac, mad = frame_diff_metrics(gray_frames[i - 1], gray_frames[i])
        # Threshold ignores single-cursor blink (~0.02% pixels) while catching page loads / command output.
        if frac >= 0.008 or mad >= 0.6:
            changes.append(i / sample_fps)

    # Collapse rapid consecutive animation frames (within 1.5s) into distinct logical steps.
    steps: list[float] = []
    for t in changes:
        if not steps or (t - steps[-1]) >= 1.5:
            steps.append(t)

    last_change_t = changes[-1] if changes else 0.0
    boundaries = [0.0, *changes, total_dur]
    max_freeze = max(boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1))
    return {
        "transition_times": changes,
        "distinct_steps": len(steps),
        "last_change_t": last_change_t,
        "last_change_ratio": (last_change_t / total_dur) if total_dur > 0 else 0.0,
        "max_freeze_sec": max_freeze,
        "max_freeze_ratio": (max_freeze / total_dur) if total_dur > 0 else 1.0,
    }


def region_gray_stats(
    buf: bytes, width: int, height: int, frac_box: tuple[float, float, float, float]
) -> tuple[float, float]:
    x0 = max(0, min(width - 1, int(frac_box[0] * width)))
    y0 = max(0, min(height - 1, int(frac_box[1] * height)))
    x1 = max(x0 + 1, min(width, int(frac_box[2] * width)))
    y1 = max(y0 + 1, min(height, int(frac_box[3] * height)))
    vals: list[int] = []
    stride = width * 3
    for y in range(y0, y1):
        row = buf[y * stride + x0 * 3:y * stride + x1 * 3]
        for i in range(0, len(row), 3):
            vals.append((row[i] + row[i + 1] + row[i + 2]) // 3)
    if not vals:
        return 0.0, 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return mean, math.sqrt(var)


def has_browser_toolbar(buf: bytes, width: int, height: int) -> bool:
    """Detect real browser top chrome (supports both Dark Mode and Light Mode Chrome)."""
    tab_mean, _ = region_gray_stats(buf, width, height, (0.05, 0.008, 0.90, 0.042))
    div_mean, div_std = region_gray_stats(buf, width, height, (0.05, 0.043, 0.95, 0.048))
    omni_pad_mean, omni_pad_std = region_gray_stats(buf, width, height, (0.09, 0.047, 0.88, 0.053))
    omni_mean, omni_std = region_gray_stats(buf, width, height, (0.09, 0.050, 0.88, 0.080))
    # Omnibox top strip is uniform padding above URL text (handles arbitrarily long URLs).
    flat_toolbar_strips = omni_pad_std < 14.0 and div_std < 14.0
    # Light Chrome: bright tabbar (>=170) and bright omnibox (>=200);
    # Dark Chrome: dark tabbar (<=80), dark divider (<=80), dark-gray omnibox (25..95) with URL contrast.
    light_chrome = tab_mean >= 170 and omni_pad_mean >= 200 and flat_toolbar_strips
    dark_chrome = (
        tab_mean <= 80
        and div_mean <= 80
        and 25 <= omni_pad_mean <= 95
        and 25 <= omni_mean <= 105
        and flat_toolbar_strips
        and omni_std >= 12.0
    )
    return light_chrome or dark_chrome


def detect_track(rgb_frames: list[bytes], width: int, height: int) -> str:
    browser_hits = sum(1 for buf in rgb_frames if has_browser_toolbar(buf, width, height))
    return "web" if browser_hits >= max(1, len(rgb_frames) // 2) else "cli"


def verify_video(
    ffmpeg: str,
    ffprobe: str,
    video: Path,
    *,
    track: str = "auto",
    storyboard: Path | None = None,
    min_fps: float = 24.0,
    min_sample_rate: int = 24000,
    max_av_skew: float = 1.0,
) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    info: dict = {"video": str(video)}

    if not video.is_file() or video.stat().st_size == 0:
        return [f"视频文件缺失或为空: {video}"], [], info

    meta = probe_media(ffprobe, video)
    vs = meta["video"]
    aus = meta["audio"]
    if not vs:
        errors.append("缺少视频轨")
        return errors, warnings, info
    if not aus:
        errors.append("缺少音频轨（必须配有中文语音旁白）")

    width = int(vs.get("width") or 0)
    height = int(vs.get("height") or 0)
    v_codec = vs.get("codec_name", "")
    avg_fps = _parse_rate(vs.get("avg_frame_rate", "0/0"))
    v_dur = float(vs.get("duration") or meta["format_duration"] or 0.0)
    info.update({"width": width, "height": height, "fps": avg_fps, "v_dur": v_dur})

    if v_codec != "h264":
        warnings.append(f"视频编码为 {v_codec}，推荐使用 H.264 (avc1)")
    if width < 800 or height < 450:
        errors.append(f"视频分辨率过低 ({width}x{height})，难以看清代码与参数")
    if avg_fps < min_fps:
        errors.append(f"视频帧率过低 ({avg_fps:.2f} fps < {min_fps:.0f} fps)，疑似低帧率幻灯片拼凑")

    if aus:
        a_codec = aus.get("codec_name", "")
        sample_rate = int(aus.get("sample_rate") or 0)
        a_dur = float(aus.get("duration") or v_dur)
        av_diff = abs(v_dur - a_dur)
        info.update({"sample_rate": sample_rate, "a_dur": a_dur})
        if a_codec != "aac":
            warnings.append(f"音频编码为 {a_codec}，推荐使用 AAC")
        if sample_rate < min_sample_rate:
            errors.append(f"音频采样率过低 ({sample_rate} Hz < {min_sample_rate} Hz)，建议使用高自然度神经语音")
        if a_dur > v_dur + 0.5:
            errors.append(f"音频长于视频 (视频 {v_dur:.2f}s vs 音频 {a_dur:.2f}s)，末尾画面已耗尽")
        elif av_diff > max(2.0, max_av_skew * 2.0):
            errors.append(f"音视频时长严重不一致 (视频 {v_dur:.2f}s vs 音频 {a_dur:.2f}s，差 {av_diff:.2f}s)")
        elif av_diff > max_av_skew:
            warnings.append(f"音视频时长略有偏差 (视频 {v_dur:.2f}s vs 音频 {a_dur:.2f}s，差 {av_diff:.2f}s)")

    # Extract timeline at 2fps for motion/freeze & cross-contamination hashes.
    gray_frames = extract_gray_timeline(ffmpeg, video, sample_fps=2.0, tw=320, th=180)
    motion = analyze_motion(gray_frames, 2.0, v_dur)
    info["motion"] = motion
    info["first_gray"] = gray_frames[0] if gray_frames else b""
    info["settled_gray"] = gray_frames[-1] if gray_frames else b""

    if v_dur < 6.0:
        errors.append(f"视频过短 ({v_dur:.2f}s < 6s)，无法完整讲解操作与结果")
    if motion["distinct_steps"] < 2:
        errors.append(
            f"有效画面步骤切换过少 (仅 {motion['distinct_steps']} 次)，疑似一次性跑完脚本后全程定格"
        )
    if v_dur >= 10.0 and motion["last_change_ratio"] < 0.40:
        errors.append(
            f"画面过早停止变化：最后一次有效变动在 {motion['last_change_t']:.1f}s / {v_dur:.1f}s "
            f"({motion['last_change_ratio'] * 100:.0f}%)，后半段处于纯静态定格"
        )
    if v_dur >= 10.0 and motion["max_freeze_ratio"] > 0.60:
        errors.append(
            f"存在超长静止画面：{motion['max_freeze_sec']:.1f}s ({motion['max_freeze_ratio'] * 100:.0f}%)"
        )

    # Check start & end boundary frames for blank / calibration leftover.
    start_rgb = extract_rgb_frame(ffmpeg, video, 0.0, width, height)
    end_rgb = extract_last_rgb_frame(ffmpeg, video, v_dur, avg_fps, width, height)
    start_issue = is_calibration_or_blank(start_rgb, width, height)
    if start_issue:
        errors.append(f"视频首帧异常: {start_issue}")
    end_issue = is_calibration_or_blank(end_rgb, width, height)
    if end_issue:
        errors.append(f"视频末帧异常: {end_issue}")

    # Sample 7 intermediate frames for track / overlay / blank checks.
    sample_times = [round(v_dur * f, 2) for f in (0.08, 0.20, 0.35, 0.50, 0.65, 0.80, 0.92)]
    sampled_rgb = [(t, extract_rgb_frame(ffmpeg, video, t, width, height)) for t in sample_times]

    for t, buf in sampled_rgb:
        issue = is_calibration_or_blank(buf, width, height)
        if issue:
            warnings.append(f"t={t:.1f}s 画面异常: {issue}")

    effective_track = detect_track([b for _, b in sampled_rgb], width, height) if track == "auto" else track
    info["effective_track"] = effective_track

    if effective_track == "web":
        for t, buf in sampled_rgb:
            above_bottom = region_mean_rgb(buf, width, height, (0.05, 0.72, 0.95, 0.82))
            bottom = region_mean_rgb(buf, width, height, (0.05, 0.86, 0.95, 0.98))
            if bottom < 80 and (above_bottom - bottom) > 45:
                errors.append(f"t={t:.1f}s 底部存在深色字幕条/Overlay (底部均值 {bottom:.0f} vs 上方 {above_bottom:.0f})")
            badge = region_mean_rgb(buf, width, height, (0.78, 0.11, 0.97, 0.18))
            if badge < 35:
                warnings.append(f"t={t:.1f}s 右上角区域较暗，请确认无 Overlay 角标残留 (均值 {badge:.0f})")
            if not has_browser_toolbar(buf, width, height):
                errors.append(f"t={t:.1f}s 缺失真实浏览器标签栏或 URL 地址栏")

    # Audio activity & silence gap checks.
    if aus:
        env, win = extract_audio_envelope(ffmpeg, video)
        if not env:
            errors.append("音频解码后无有效波形")
        else:
            sorted_env = sorted(env)
            thr = max(8.0, sorted_env[int(len(sorted_env) * 0.92)] * 0.15)
            active_ratio = sum(1 for v in env if v > thr) / len(env)
            if active_ratio < 0.20:
                errors.append(f"有效解说语音占比过低 ({active_ratio * 100:.0f}% < 20%)")
            # Detect long continuous silence (> 6.0s).
            silent_run = 0
            max_silent_sec = 0.0
            for v in env:
                if v <= thr:
                    silent_run += 1
                    max_silent_sec = max(max_silent_sec, silent_run * win)
                else:
                    silent_run = 0
            if max_silent_sec > 6.5:
                warnings.append(f"存在长达 {max_silent_sec:.1f}s 的连续静音段")

            if storyboard and storyboard.is_file():
                sb = json.loads(storyboard.read_text(encoding="utf-8"))
                steps = sb.get("steps") or []
                for idx, s in enumerate(steps, 1):
                    text = s.get("narration") or s.get("text") or ""
                    if text:
                        if BATCH_PREFIX_RE.search(text):
                            errors.append(f"分镜第 {idx} 步口播包含跨漏洞批号 ('{text[:24]}...')")
                        bad_tokens = RAW_TTS_TOKEN_RE.findall(text)
                        if bad_tokens:
                            warnings.append(
                                f"分镜第 {idx} 步口播含可能被 TTS 误读的英文/缩写: {', '.join(bad_tokens[:4])}"
                            )
                    if "anchor" in s and "dur" in s:
                        a = float(s["anchor"])
                        d = float(s["dur"])
                        i0 = max(0, int((a - 0.10) / win))
                        i1 = min(len(env), int((a + min(d, 1.2)) / win))
                        p0 = max(0, int((a - 0.45) / win))
                        p1 = max(0, int((a - 0.10) / win))
                        seg = env[i0:i1]
                        pre = env[p0:p1]
                        if not seg:
                            errors.append(f"分镜第 {idx} 步锚点 {a:.2f}s 超出音频长度")
                        else:
                            peak = max(seg)
                            base = max(pre) if pre else 0.0
                            if not (peak > thr and peak > max(base * 2.2, thr)):
                                errors.append(
                                    f"分镜第 {idx} 步锚点 {a:.2f}s 处未检测到音频起音 "
                                    f"(peak={peak:.0f}, pre={base:.0f}, thr={thr:.0f})"
                                )

    return errors, warnings, info


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_docx_structure(docx_path: Path, *, shots_dir: Path | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not docx_path.is_file():
        return [f"缺失 Word 报告: {docx_path}"], []

    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            if zf.testzip() is not None:
                return [f".docx 内部 ZIP 校验失败: {docx_path}"], []
            names = set(zf.namelist())
            if "word/document.xml" not in names:
                return [f"无效的 .docx 结构（缺少 word/document.xml）: {docx_path}"], []
            doc_xml = zf.read("word/document.xml")
            media_files = [n for n in names if n.startswith("word/media/")]
            media_hashes = {_sha256_bytes(zf.read(n)) for n in media_files}
    except zipfile.BadZipFile:
        return [f".docx 文件损坏（非有效 ZIP）: {docx_path}"], []

    root = ET.fromstring(doc_xml)
    paragraphs: list[str] = []
    has_blip = False
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag in ("blip", "imagedata"):
            has_blip = True
        if tag == "p":
            texts = [t.text for t in elem.iter() if t.tag.rsplit("}", 1)[-1] == "t" and t.text]
            line = "".join(texts).strip()
            if line:
                paragraphs.append(line)

    full_text = "\n".join(paragraphs)
    for meta in REQUIRED_META_PREFIXES:
        if meta not in full_text:
            errors.append(f"报告.docx 缺少必需元信息行: {meta}")

    positions: list[int] = []
    for sec in REQUIRED_SECTIONS:
        idx = next((i for i, p in enumerate(paragraphs) if sec in p), -1)
        if idx < 0:
            errors.append(f"报告.docx 缺少必需章节: {sec}")
        else:
            positions.append(idx)
    if len(positions) == len(REQUIRED_SECTIONS) and positions != sorted(positions):
        errors.append("报告.docx 3 段式章节顺序不正确")

    for p in paragraphs:
        for pat in FORBIDDEN_HEADING_PATTERNS:
            if pat.search(p):
                errors.append(f"报告.docx 包含规范禁止的章节/内容 ('{p[:40]}')")
                break
        for pat in FORBIDDEN_GRADING_PATTERNS:
            m = pat.search(p)
            if m:
                errors.append(f"报告.docx 正文包含禁止的定级/评级词 '{m.group(0).strip()}' ('{p[:40]}')")
                break

    if not media_files or not has_blip:
        errors.append("报告.docx 未嵌入任何截图（word/media 为空或无图片引用）")

    if shots_dir is not None and shots_dir.is_dir():
        disk_hashes: dict[str, list[str]] = {}
        for png in sorted(shots_dir.glob("*.png")):
            h = _sha256_bytes(png.read_bytes())
            disk_hashes.setdefault(h, []).append(png.name)
        dup_files = [names_list for names_list in disk_hashes.values() if len(names_list) > 1]
        if dup_files:
            errors.append(f"截图/ 目录存在内容重复的图片: {dup_files}")
        missing_on_disk = media_hashes - set(disk_hashes.keys())
        if missing_on_disk:
            errors.append(f"报告.docx 中有 {len(missing_on_disk)} 张嵌入图在 截图/ 目录中找不到对应原图")
        extra_on_disk = set(disk_hashes.keys()) - media_hashes
        if extra_on_disk:
            extra_names = [disk_hashes[h][0] for h in extra_on_disk]
            warnings.append(f"截图/ 目录中有 {len(extra_names)} 张图未被 报告.docx 引用: {', '.join(extra_names[:4])}")

    return errors, warnings


def verify_package(
    ffmpeg: str,
    ffprobe: str,
    pkg_dir: Path,
    *,
    track: str = "auto",
    storyboard: Path | None = None,
    allow_no_video: bool = False,
) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    if not pkg_dir.is_dir():
        return [f"交付目录不存在: {pkg_dir}"], [], {}

    shots_dir = pkg_dir / "截图"
    if not shots_dir.is_dir():
        errors.append("缺少 截图/ 目录")
    else:
        pngs = list(shots_dir.glob("*.png"))
        if not pngs:
            errors.append("截图/ 目录中没有 .png 截图")

    report_docx = pkg_dir / "报告.docx"
    if not report_docx.is_file():
        other_docx = [p.name for p in pkg_dir.glob("*.docx") if not p.name.startswith("~$")]
        if other_docx:
            errors.append(f"缺少标准报告文件 报告.docx（当前存在: {', '.join(other_docx)}）")
        else:
            errors.append("缺少 报告.docx")
    else:
        d_err, d_warn = verify_docx_structure(report_docx, shots_dir=shots_dir if shots_dir.is_dir() else None)
        errors.extend(d_err)
        warnings.extend(d_warn)

    poc_md = pkg_dir / "PoC.md"
    if not poc_md.is_file():
        errors.append("缺少 PoC.md")
    else:
        poc_txt = poc_md.read_text(encoding="utf-8")
        for sec in ("## 复现步骤", "## 修复建议"):
            if sec not in poc_txt:
                errors.append(f"PoC.md 缺少必需章节: {sec}")

    poc_sh = pkg_dir / "PoC.sh"
    if not poc_sh.is_file():
        errors.append("缺少 PoC.sh")
    else:
        if os.name != "nt" and not os.access(poc_sh, os.X_OK):
            errors.append("PoC.sh 缺少可执行权限 (+x)")
        if shutil.which("bash"):
            chk = _run(["bash", "-n", str(poc_sh)])
            if chk.returncode != 0:
                errors.append(f"PoC.sh 语法错误: {chk.stderr.strip()}")

    # Reject stray intermediate media files left in final package root.
    stray = [
        p.name for p in pkg_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".mov", ".wav", ".mp3", ".tmp", ".log"}
    ]
    if stray:
        errors.append(f"交付目录残留过程垃圾文件: {', '.join(stray)}")
    if (pkg_dir / ".DS_Store").exists():
        warnings.append("交付目录包含 .DS_Store（打包压缩前建议剔除）")

    sb_path = storyboard
    if sb_path is None:
        for candidate in ("storyboard.json", "align.json"):
            if (pkg_dir / candidate).is_file():
                sb_path = pkg_dir / candidate
                break

    vid_path = pkg_dir / "复现视频.mp4"
    resp_path = pkg_dir / "实测响应.txt"
    if not vid_path.is_file():
        if allow_no_video and resp_path.is_file():
            warnings.append("未提供 复现视频.mp4，已按 --allow-no-video 凭 实测响应.txt 放行")
            return errors, warnings, {"video": None}
        errors.append("缺少 复现视频.mp4")
        return errors, warnings, {"video": None}

    v_err, v_warn, v_info = verify_video(ffmpeg, ffprobe, vid_path, track=track, storyboard=sb_path)
    errors.extend(v_err)
    warnings.extend(v_warn)
    return errors, warnings, v_info


def verify_batch(
    ffmpeg: str,
    ffprobe: str,
    root_dir: Path,
    *,
    track: str = "auto",
    allow_no_video: bool = False,
) -> tuple[bool, list[tuple[str, list[str], list[str], dict]]]:
    pkg_dirs = sorted(
        p for p in root_dir.iterdir()
        if p.is_dir() and not p.name.startswith(("_", "."))
    )
    results: list[tuple[str, list[str], list[str], dict]] = []
    video_frames: list[tuple[str, bytes, bytes]] = []

    for pkg in pkg_dirs:
        err, warn, info = verify_package(
            ffmpeg, ffprobe, pkg, track=track, allow_no_video=allow_no_video
        )
        results.append((pkg.name, err, warn, info))
        if info.get("first_gray") and info.get("settled_gray"):
            video_frames.append((pkg.name, info["first_gray"], info["settled_gray"]))

    # Cross-package contamination check: 0.0s first frame must not match another package's settled frame.
    if len(video_frames) >= 2:
        by_name = {name: (err, warn) for name, err, warn, _ in results}
        for name_i, first_i, _ in video_frames:
            for name_j, _, settled_j in video_frames:
                if name_i == name_j:
                    continue
                _, mad = frame_diff_metrics(first_i, settled_j)
                if mad < 3.5:
                    by_name[name_i][0].append(
                        f"首帧串帧污染：0.0s 首帧与「{name_j}」的末尾画面高度一致 (MAD={mad:.2f} < 3.5)"
                    )
                    break

    overall_ok = all(not err for _, err, _, _ in results)
    return overall_ok, results


def _print_result(label: str, errors: list[str], warnings: list[str], info: dict, *, strict: bool) -> bool:
    passed = not errors and (not strict or not warnings)
    status = "PASS" if passed else "FAIL"
    meta_str = ""
    if "fps" in info:
        m = info.get("motion", {})
        meta_str = (
            f" [{info.get('width')}x{info.get('height')} {info.get('fps', 0):.1f}fps "
            f"v={info.get('v_dur', 0):.1f}s a={info.get('a_dur', 0):.1f}s@{info.get('sample_rate', 0)}Hz "
            f"track={info.get('effective_track')} steps={m.get('distinct_steps', 0)} "
            f"last_chg={m.get('last_change_ratio', 0) * 100:.0f}%]"
        )
    print(f"[{status}] {label}{meta_str}")
    for e in errors:
        print(f"  ERROR: {e}")
    for w in warnings:
        print(f"  WARN : {w}")
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify CNVD submission package(s) and reproduction video(s).")
    parser.add_argument("target", type=Path, help="Package directory, batch root (--batch), or .mp4 (--video-only).")
    parser.add_argument("--batch", action="store_true", help="Verify every package directory under target + cross-video checks.")
    parser.add_argument("--video-only", action="store_true", help="Verify only the specified .mp4 file.")
    parser.add_argument("--track", choices=["auto", "web", "cli"], default="auto", help="Capture track mode.")
    parser.add_argument("--storyboard", type=Path, default=None, help="Optional storyboard.json / align.json for sync & narration checks.")
    parser.add_argument("--allow-no-video", action="store_true", help="Allow missing 复现视频.mp4 when 实测响应.txt is present.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args(argv)

    try:
        ffmpeg, ffprobe = _require_tooling()
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if args.video_only:
        err, warn, info = verify_video(ffmpeg, ffprobe, args.target, track=args.track, storyboard=args.storyboard)
        ok = _print_result(args.target.name, err, warn, info, strict=args.strict)
        return 0 if ok else 1

    if args.batch:
        if not args.target.is_dir():
            print(f"FAIL: batch root is not a directory: {args.target}", file=sys.stderr)
            return 2
        _, results = verify_batch(
            ffmpeg, ffprobe, args.target, track=args.track, allow_no_video=args.allow_no_video
        )
        if not results:
            print(f"FAIL: no package subdirectories found under {args.target}", file=sys.stderr)
            return 2
        all_ok = True
        for name, err, warn, info in results:
            if not _print_result(name, err, warn, info, strict=args.strict):
                all_ok = False
        return 0 if all_ok else 1

    err, warn, info = verify_package(
        ffmpeg, ffprobe, args.target, track=args.track, storyboard=args.storyboard,
        allow_no_video=args.allow_no_video,
    )
    ok = _print_result(args.target.name, err, warn, info, strict=args.strict)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
