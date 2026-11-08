# Stage 191 — historical Android x86_64 GCC 4.9 (PE-Reborn / AOSP 17)

**Date:** 2026-11-08. **Device scope:** POCO F5 Pro / Redmi K60 (mondrian, SM8475). **Baseline:** independently pinned Google AOSP android-17.0.0_r1, NOT LineageOS, CLO or historical PixelExperience Android14 builds.

## Source and historical intent

Archived project: https://github.com/PixelExperience-Reborn/prebuilts_gcc_linux-x86_x86_x86_64-linux-android-4.9

- Historical seventeen branch: commit 5c8aca3781d423cc450c1c05b6ff0813812d65bc (committed 2021-11-08; authored earlier). Root Git tree 37ef73dd2b9fb75749c1cf2180c694283d26050b; original bin tree 033e253524b5e319de336aa96f88e9b814913b24.
- The final historical commit is titled "gcc-4.9: Restore GCC" and reverts earlier removal/moving of the tools to uncover old build consumers. Historical developer work is preserved, not falsely treated as sufficient Android17 dependency evidence.
- Original PixelExperience manifest/seventeen included this checkout in snippets/pixel-extras.xml along with AArch64 and ARM32 GCC49 archives. The independent official AOSP17 source reference does not.
- The tree provides a TARGET toolchain for Android x86_64 (x86_64-linux-android-), including GCC 4.9, binutils, GNU as, ld.bfd, ld.gold, objcopy and x86_64-linux-androidkernel aliases. It is not equivalent to a Linux-host x86_64 compiler simply because both names include x86_64.
- The repo.prop records old toolchain/gcc, toolchain/binutils, GMP/ISL/MPC/MPFR and older host prebuilt inputs. No Android17 compiler provenance is claimed.

## Important source-level defect discovered in the historical archive

Two executable Git paths, bin/x86_64-linux-android-gcc and bin/real-x86_64-linux-android-gcc, contain the SAME 1733-byte Python compiler wrapper: Git blob 54944a2ccbea692fa58d912e74b2514dab7a80f5. That wrapper constructs real_compiler by adding the "real-" prefix to its own executable basename before calling os.execv.

Therefore the normal first name attempts real-x86_64-linux-android-gcc, but that second executable contains the same wrapper logic and would attempt real-real-x86_64-linux-android-gcc. No such path exists in the archived Git bin tree. The actual x86_64-linux-android-gcc-4.9.x ELF is a separate Git blob, not the wrapper's computed target. This is an evidence-based STATIC wrapper-chain defect, NOT a report of a runtime experiment. The CI reads the 1733-byte wrapper blob only; it never executes or downloads old GCC binaries.

**Decision:** never silently put this broken 2021-era archive into an Android17 platform/toolchain PATH. Do not repair old ELF artifacts or change the historical seventeen branch to hide the issue; an approved modern AOSP17 build should use its pinned LLVM/Clang graph.

## Official AOSP17 and hardware architecture

- The independently selected AOSP17 manifest includes the official platform/prebuilts/clang/host/linux-x86 path, and retains a DIFFERENT, official host project platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8. Preserve these official host dependencies if selected by the platform; this audit forbids only the obsolete ANDROID-TARGET x86_64 GCC4.9 repo.
- Current PE-Reborn AOSP17 build_soong pinned to 6215d41c790a463b7795ce81ac77204c238cbf48 specifies platform ClangDefaultVersion clang-r584948. This is NOT a kernel compiler pin.
- Device reference (READ-ONLY): LF52406/mondrian_android_device_xiaomi_sm8450-common, pinned 6e0022f5100e09ac97980095b6ed8528f4ff823f, BoardConfigCommon.mk specifies TARGET_ARCH := arm64, TARGET_CPU_ABI := arm64-v8a, TARGET_KERNEL_SOURCE := kernel/xiaomi/sm8450. No PixelExperience-Reborn independent device-tree or kernel build is implied.
- x86_64 Android targets/emulators are outside the initial mondrian-only ROM scope. If needed in future, toolchain compatibility would require an isolated, separately pinned modern build; do not import this GCC4.9.

## Implemented protection and reproducible verification

1. New Git-metadata/source-only tests verify exact archival HEAD/tree, immutable lib/libexec/bin objects, executable and symlink modes/SHA, original Python wrapper structure and missing real-real target, old repo.prop history, official AOSP17 source and Soong clang-r584948, default manifest entrypoint, and ARM64 mondrian architecture reference.
2. GitHub Actions uses blob-filtered sparse checkout; historical compiler executable blobs are not checked out or run. The old 1733-byte Python wrapper is parsed as source only. External reference files are retrieved from immutable Git commit pins.
3. Companion manifest draft branch must reject the historical checkout path and known repo aliases across active/candidate profiles, with two negative tests; update row 191 in the strict 135-repository matrix. Historical seventeen and clean AOSP17 default.xml are unchanged.

**Not proven / remaining gates:** full AOSP17 sync, Soong bootstrap, x86_64 target builds, kernel Image/DTBO/modules, AVB/VINTF/FCM/GKI/KMI, vendor ABI, recovery/OTA and a physical mondrian boot. All such gates require a separate build/validation project.

**Audit outcome:** preserve history, isolate obsolete target toolchain, avoid adding unnecessary or broken prebuilts to the AOSP17 build graph.
