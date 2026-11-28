#!/usr/bin/env python3
"""Unit and optional ffmpeg-backed tests for cnvd-packager verification gate."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "cnvd-packager" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import verify_cnvd_package as verifier  # noqa: E402

SAMPLE_META = [
    "源码地址：https://example.com/repo",
    "影响版本：1.0.0",
    "受影响端点：GET /api/demo",
    "所需权限：无需登录",
]


def _make_minimal_docx(
    path: Path,
    paragraphs: list[str],
    *,
    with_image: bool = True,
    image_bytes: bytes = b"\x89PNG\r\n\x1a\nfake",
) -> None:
    p_xml = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    blip_xml = (
        '<w:p><w:r><w:drawing><a:blip xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/></w:drawing></w:r></w:p>'
        if with_image
        else ""
    )
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{p_xml}{blip_xml}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", doc_xml.encode("utf-8"))
        if with_image:
            zf.writestr("word/media/image1.png", image_bytes)


def _populate_poc_and_shots(pkg: Path, *, png_bytes: bytes = b"\x89PNG\r\n\x1a\nfake") -> None:
    (pkg / "截图").mkdir(parents=True, exist_ok=True)
    (pkg / "截图" / "01.png").write_bytes(png_bytes)
    (pkg / "PoC.md").write_text("# PoC\n\n## 复现步骤\n\n## 修复建议\n", encoding="utf-8")
    poc_sh = pkg / "PoC.sh"
    poc_sh.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    poc_sh.chmod(0o755)


class CnvdPackagerPureTests(unittest.TestCase):
    def test_docx_accepts_valid_three_section_report_with_shot_parity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shots = root / "截图"
            shots.mkdir()
            img = b"\x89PNG\r\n\x1a\nvalid-shot"
            (shots / "step1.png").write_bytes(img)
            docx = root / "报告.docx"
            _make_minimal_docx(docx, SAMPLE_META + verifier.REQUIRED_SECTIONS, image_bytes=img)
            err, warn = verifier.verify_docx_structure(docx, shots_dir=shots)
            self.assertEqual(err, [])
            self.assertEqual(warn, [])

    def test_docx_rejects_missing_section_grading_words_cvss_and_shot_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shots = root / "截图"
            shots.mkdir()
            (shots / "other.png").write_bytes(b"\x89PNG\r\n\x1a\nother")
            docx = root / "报告.docx"
            _make_minimal_docx(
                docx,
                ["源码地址：x", "一、源码成因", "二、CVSS高危评分", "三、修复建议"],
                with_image=True,
                image_bytes=b"\x89PNG\r\n\x1a\nembedded",
            )
            err, _ = verifier.verify_docx_structure(docx, shots_dir=shots)
            joined = "\n".join(err)
            self.assertIn("二、复现步骤与关键截图", joined)
            self.assertIn("影响版本：", joined)
            self.assertIn("CVSS", joined)
            self.assertIn("定级/评级词", joined)
            self.assertIn("找不到对应原图", joined)

    def test_motion_rejects_instant_freeze_and_accepts_stepped_activity(self):
        a = bytes([10] * (320 * 180))
        b = bytes([200] * (320 * 180))
        frozen = [a] + [b] * 19
        m_bad = verifier.analyze_motion(frozen, 2.0, 10.0)
        self.assertLess(m_bad["last_change_ratio"], 0.2)
        self.assertGreater(m_bad["max_freeze_ratio"], 0.8)

        c = bytes([50] * (320 * 180))
        d = bytes([140] * (320 * 180))
        stepped = [a] * 4 + [b] * 5 + [c] * 5 + [d] * 6
        m_ok = verifier.analyze_motion(stepped, 2.0, 10.0)
        self.assertEqual(m_ok["distinct_steps"], 3)
        self.assertGreaterEqual(m_ok["last_change_ratio"], 0.65)
        self.assertLessEqual(m_ok["max_freeze_ratio"], 0.35)

    def test_narration_regexes_catch_batch_prefix_and_raw_identifiers(self):
        self.assertIsNotNone(verifier.BATCH_PREFIX_RE.search("第 1 项，未授权访问"))
        self.assertIsNotNone(verifier.BATCH_PREFIX_RE.search("第一条，SQL注入"))
        self.assertIsNone(verifier.BATCH_PREFIX_RE.search("目标系统流程设计器接口存在未授权访问漏洞"))
        self.assertTrue(verifier.RAW_TTS_TOKEN_RE.findall("伪造 ab-inner 调用 getInterFaceImpls"))


class CnvdPackagerMediaTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe unavailable")
    def test_media_gates_catch_2fps_freeze_calibration_and_cross_contamination(self):
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        assert ffmpeg and ffprobe

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            img = b"\x89PNG\r\n\x1a\nshot1"

            # 1) Clean 30fps stepped CLI package (should PASS)
            good_pkg = root / "Prod_SQLi"
            _populate_poc_and_shots(good_pkg, png_bytes=img)
            _make_minimal_docx(good_pkg / "报告.docx", SAMPLE_META + verifier.REQUIRED_SECTIONS, image_bytes=img)
            good_mp4 = good_pkg / "复现视频.mp4"
            subprocess.run([
                ffmpeg, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=#181c22:s=1280x720:r=30:d=3,drawbox=x=80:y=80:w=400:h=40:color=white:t=fill",
                "-f", "lavfi", "-i", "color=c=#181c22:s=1280x720:r=30:d=3,drawbox=x=80:y=180:w=700:h=80:color=green:t=fill",
                "-f", "lavfi", "-i", "color=c=#181c22:s=1280x720:r=30:d=3,drawbox=x=80:y=320:w=900:h=120:color=yellow:t=fill",
                "-f", "lavfi", "-i", "anullsrc=r=32000:cl=mono:d=0.6",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=32000:duration=2.4",
                "-f", "lavfi", "-i", "anullsrc=r=32000:cl=mono:d=0.6",
                "-f", "lavfi", "-i", "sine=frequency=520:sample_rate=32000:duration=2.4",
                "-f", "lavfi", "-i", "anullsrc=r=32000:cl=mono:d=0.6",
                "-f", "lavfi", "-i", "sine=frequency=600:sample_rate=32000:duration=2.4",
                "-filter_complex",
                "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v];[3:a][4:a][5:a][6:a][7:a][8:a]concat=n=6:v=0:a=1[a]",
                "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "32000", str(good_mp4),
            ], check=True)
            sb = good_pkg / "storyboard.json"
            sb.write_text(json.dumps({
                "steps": [
                    {"narration": "目标系统存在接口未鉴权问题。", "anchor": 0.6, "dur": 2.4},
                    {"narration": "发送测试请求验证报错回显。", "anchor": 3.6, "dur": 2.4},
                    {"narration": "确认返回内容并完成验证。", "anchor": 6.6, "dur": 2.4},
                ]
            }, ensure_ascii=False), encoding="utf-8")

            err, warn, _ = verifier.verify_package(ffmpeg, ffprobe, good_pkg, track="cli")
            self.assertEqual(err, [], f"expected clean pass, got errors={err} warnings={warn}")

            # 2) 2fps instant-freeze video starting with pure green calibration leftover (should FAIL)
            bad_pkg = root / "Prod_Leak"
            _populate_poc_and_shots(bad_pkg, png_bytes=img)
            _make_minimal_docx(bad_pkg / "报告.docx", SAMPLE_META + verifier.REQUIRED_SECTIONS, image_bytes=img)
            bad_mp4 = bad_pkg / "复现视频.mp4"
            subprocess.run([
                ffmpeg, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=#00FF00:s=1280x720:r=2:d=1",
                "-f", "lavfi", "-i", "color=c=#181c22:s=1280x720:r=2:d=11,drawbox=x=80:y=80:w=400:h=40:color=white:t=fill",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=22050:duration=12",
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "22050", str(bad_mp4),
            ], check=True)

            err_bad, _, _ = verifier.verify_package(ffmpeg, ffprobe, bad_pkg, track="cli")
            joined = "\n".join(err_bad)
            self.assertIn("帧率过低", joined)
            self.assertIn("采样率过低", joined)
            self.assertIn("纯绿标定帧残留", joined)
            self.assertIn("画面过早停止变化", joined)

            # 3) Cross-contamination check: copy good_pkg settled ending frame as 0.0s of pkg3
            leak_pkg = root / "Prod_Contam"
            _populate_poc_and_shots(leak_pkg, png_bytes=img)
            _make_minimal_docx(leak_pkg / "报告.docx", SAMPLE_META + verifier.REQUIRED_SECTIONS, image_bytes=img)
            subprocess.run([
                ffmpeg, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=#181c22:s=1280x720:r=30:d=2,drawbox=x=80:y=320:w=900:h=120:color=yellow:t=fill",
                "-f", "lavfi", "-i", "color=c=#181c22:s=1280x720:r=30:d=4,drawbox=x=100:y=100:w=500:h=80:color=red:t=fill",
                "-f", "lavfi", "-i", "color=c=#181c22:s=1280x720:r=30:d=4,drawbox=x=100:y=240:w=600:h=80:color=cyan:t=fill",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=32000:duration=10",
                "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
                "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "32000", str(leak_pkg / "复现视频.mp4"),
            ], check=True)
            ok, batch_res = verifier.verify_batch(ffmpeg, ffprobe, root, track="cli")
            self.assertFalse(ok)
            contam_errs = "\n".join(dict((n, e) for n, e, _, _ in batch_res)["Prod_Contam"])
            self.assertIn("首帧串帧污染", contam_errs)


if __name__ == "__main__":
    unittest.main()
