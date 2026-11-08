#!/usr/bin/env python3
"""PE-Reborn stage 191: archived Android-target x86_64 GCC 4.9 source-only audit.

Git metadata and immutable pinned text references only. This intentionally
does NOT execute / download legacy GCC, assembler, linker or other ELF files.
"""
import os
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_COMMIT = "5c8aca3781d423cc450c1c05b6ff0813812d65bc"
ARCHIVE_TREE = "37ef73dd2b9fb75749c1cf2180c694283d26050b"
ARCHIVE_BIN_TREE = "033e253524b5e319de336aa96f88e9b814913b24"
WRAPPER_SHA = "54944a2ccbea692fa58d912e74b2514dab7a80f5"
OLD_TARGET_PATH = "prebuilts/gcc/linux-x86/x86/x86_64-linux-android-4.9"
OLD_TARGET_NAME = "prebuilts_gcc_linux-x86_x86_x86_64-linux-android-4.9"
AOSP_CLANG_OWNER = "platform/prebuilts/clang/host/linux-x86"
AOSP_HOST_GCC = "platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8"
EXPECTED_CLANG = "clang-r584948"


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True,
        capture_output=True, text=True
    ).stdout.strip()


def entry(revision, path):
    data = git("ls-tree", revision, "--", path)
    if not data:
        raise AssertionError("Git entry missing: " + path)
    details, returned = data.split("\t", 1)
    if returned != path:
        raise AssertionError("unexpected Git path: " + returned)
    mode, kind, sha = details.split()
    return (mode, kind, sha)


def pinned_text(key):
    path = os.environ.get(key)
    if not path or not Path(path).is_file():
        raise AssertionError("missing immutable source input " + key)
    return Path(path).read_text(encoding="utf-8")


class X8664Gcc49ArchiveBoundary(unittest.TestCase):
    def test_original_git_history_and_root_tree(self):
        p = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
             ARCHIVE_COMMIT, "HEAD"], capture_output=True, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(git("rev-parse", ARCHIVE_COMMIT + "^{tree}"), ARCHIVE_TREE)

    def test_original_compiler_directories_preserved(self):
        self.assertEqual(entry("HEAD", "bin"),
                         ("040000", "tree", ARCHIVE_BIN_TREE))
        self.assertEqual(entry("HEAD", "repo.prop"),
                         ("100644", "blob", "1313a50beba6b8a49eafabcbd07fbb382ad75e05"))
        for path in ("lib", "libexec", "x86_64-linux-android"):
            with self.subTest(path=path):
                self.assertEqual(entry("HEAD", path), entry(ARCHIVE_COMMIT, path))

    def test_original_gcc_executable_and_binutils_object_ids(self):
        # Verify Git modes and hashes, NEVER invoke binary tools.
        fixtures = {
            "bin/x86_64-linux-android-gcc": ("100755", WRAPPER_SHA),
            "bin/real-x86_64-linux-android-gcc": ("100755", WRAPPER_SHA),
            "bin/x86_64-linux-android-gcc-4.9": (
                "120000", "c953618e353df6bffd9a4b7a8127f4a0d30ce990"),
            "bin/x86_64-linux-android-gcc-4.9.x": (
                "100755", "33e6c2797dd911d6fa71085c344a2b8d59a10d13"),
            "bin/x86_64-linux-android-as": (
                "100755", "61c8ea79cdf1d628d1fbe7ef60bfb467ddd44416"),
            "bin/x86_64-linux-android-ld.bfd": (
                "100755", "30c572b0124266ee1f9f0a4a618b59a4e9e6dcf3"),
            "bin/x86_64-linux-android-ld.gold": (
                "100755", "665f3c404422ab56d1c7d052e494d5841493a9f2"),
            "bin/x86_64-linux-android-objcopy": (
                "100755", "06d506e92db3296b099a47c5d759f87a548b6508"),
            "bin/x86_64-linux-androidkernel-gcc": (
                "120000", "c953618e353df6bffd9a4b7a8127f4a0d30ce990"),
        }
        for path, expected in fixtures.items():
            with self.subTest(path=path):
                mode, kind, sha = entry("HEAD", path)
                self.assertEqual(kind, "blob")
                self.assertEqual((mode, sha), expected)

    def test_historical_python_gcc_wrapper_has_missing_real_real_target(self):
        # Read only the 1733-byte source blob, no compiler ELF downloads.
        text = git("cat-file", "blob", WRAPPER_SHA)
        self.assertIn('self.real_compiler = os.path.join(', text)
        self.assertIn('"real-" + compiler', text)
        self.assertIn("os.execv(self.argv0, self.execargs)", text)
        # Original gcc points to original real-gcc, but real-gcc itself is
        # the IDENTICAL Python wrapper instead of the expected ELF binary.
        self.assertEqual(entry("HEAD", "bin/x86_64-linux-android-gcc")[2],
                         entry("HEAD", "bin/real-x86_64-linux-android-gcc")[2])
        self.assertEqual(git("ls-tree", "HEAD", "--",
                             "bin/real-real-x86_64-linux-android-gcc"), "")
        # The separate 4.9.x executable exists, but this wrapper chain does
        # not reference it; runtime behavior itself has not been tested.

    def test_legacy_gcc_provenance_is_not_aosp17(self):
        text = (ROOT / "repo.prop").read_text(encoding="utf-8")
        self.assertIn("toolchain/gcc ", text)
        self.assertIn("toolchain/binutils ", text)
        self.assertNotIn("android-17.0.0", text)
        self.assertFalse((ROOT / "Android.bp").exists())

    def test_official_aosp17_manifest_selects_platform_tools(self):
        root = ET.fromstring(pinned_text("PE_AOSP17_REFERENCE"))
        self.assertEqual(root.find("default").get("revision"),
                         "refs/tags/android-17.0.0_r1")
        projects = list(root.iter("project"))
        by_path = {p.get("path"): p.get("name") for p in projects}
        self.assertEqual(by_path["prebuilts/clang/host/linux-x86"],
                         AOSP_CLANG_OWNER)
        self.assertEqual(
            by_path["prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8"],
            AOSP_HOST_GCC)
        self.assertNotIn(OLD_TARGET_PATH, by_path)
        self.assertFalse(any(p.get("name") == OLD_TARGET_NAME for p in projects))
        # Android-target GCC49 and host GCC4.8 are DIFFERENT compilers.

    def test_pinned_platform_soong_uses_clang_not_old_gcc49(self):
        text = pinned_text("PE_AOSP17_SOONG_GLOBAL")
        found = re.findall(
            r'(?m)^\s*ClangDefaultVersion\s*=\s*"([^"]+)"', text)
        self.assertEqual(found, [EXPECTED_CLANG])
        self.assertIn("ReleaseBuildClangVersion(ClangDefaultVersion)", text)
        self.assertNotIn(OLD_TARGET_PATH, text)

    def test_aosp17_default_entrypoint_keeps_archived_gcc_out(self):
        root = ET.fromstring(pinned_text("PE_AOSP17_DEFAULT"))
        self.assertEqual([i.get("name") for i in root.findall("include")],
                         ["aosp17_pe_p2_kernel_configs.xml"])
        self.assertFalse(any(p.get("path") == OLD_TARGET_PATH or
                             p.get("name") == OLD_TARGET_NAME
                             for p in root.iter("project")))

    def test_mondrian_reference_is_arm64_not_x86_64(self):
        board = pinned_text("PE_MONDRIAN_COMMON_BOARD")
        self.assertRegex(board, r"(?m)^TARGET_ARCH\s*:=\s*arm64\s*$")
        self.assertRegex(board, r"(?m)^TARGET_CPU_ABI\s*:=\s*arm64-v8a\s*$")
        self.assertIn("TARGET_KERNEL_SOURCE := kernel/xiaomi/sm8450", board)
        self.assertNotRegex(board, r"(?m)^TARGET_ARCH\s*:=\s*x86_64\s*$")
        # This is an existing Xiaomi reference, NOT PE-Reborn device tree.

if __name__ == "__main__":
    unittest.main(verbosity=2)
