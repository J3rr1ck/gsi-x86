# Prerequisites (Arch Linux host)

Install standard build tools and Android’s dependencies.  At minimum, ensure you have **git**, **python3** (for `repo`), **openjdk11+** (for Bazel), **bazel** (available in Arch Extra), **clang**, and kernel-build tools: `bc`, `libelf`, `kmod`, `cpio`, `perl`, `xz` (for LZ4), etc.  For example: 
```bash
sudo pacman -S base-devel git python3 openjdk clang bc libelf kmod cpio perl xz wget repo
```
(You can install `repo` via `sudo pacman -S repo` or `pip install repo`.) These match Arch’s kernel build requirements (bc, libelf, git, cpio, etc. from the ArchWiki ([Build kernels  |  Android Open Source Project](https://source.android.com/docs/setup/build/building-kernels#:~:text=mkdir%20android))).  Also ensure `mkbootimg` or `mkbootfs` is available (Android’s `platform/system/tools/mkbootimg` is included in the repo manifest).

# Fetch the AOSP Mainline Kernel

Use Google’s kernel manifest with `repo`.  For the latest Android Common Kernel (“mainline”) branch, do:
```bash
mkdir android-kernel && cd android-kernel
repo init -u https://android.googlesource.com/kernel/manifest -b common-android-mainline
repo sync
```
This will clone all necessary kernel repos (the superproject and common/common-modules, etc.) as defined in the manifest ([Build kernels  |  Android Open Source Project](https://source.android.com/docs/setup/build/building-kernels#:~:text=mkdir%20android)) ([Build kernels  |  Android Open Source Project](https://source.android.com/docs/setup/build/building-kernels#:~:text=Note%3A%20You%20can%20switch%20among,mainline%20%26%26%20repo%20sync)).  The `common-android-mainline` branch tracks the newest Android-mainline kernel (currently Linux v6.15-rc).  

# Build the Kernel

Android’s “common-android-mainline” **requires Bazel** (“Kleaf”) – the old `build/build.sh` is **not supported** on this branch ([Kernel branches and their build systems  |  Android Open Source Project](https://source.android.com/docs/setup/reference/bazel-support#:~:text=common,5.10%20%E2%9D%8C%20%E2%9C%85)).  For example, to build a generic x86_64 GKI kernel, select a build config like:
```
BUILD_CONFIG=common-modules/virtual-device/build.config.virtual_device.x86_64
```
(which uses the `vd_x86_64_gki_defconfig`).  Then invoke Bazel from the root of the repo, e.g.:
```bash
bazel run //common-modules/virtual-device:virtual_device_x86_64_dist -- --destdir=out/dist
```
This tells Bazel to build the kernel and vendor modules for the generic (virtual-device) x86_64 target.  After the build completes, the kernel image (e.g. `Image.lz4-dtb` or `bzImage`) and modules will be in the output directory.  By default, Android’s build copies artifacts under `out/<branch>/dist` (or the `--destdir` you specify).  For example:
```bash
# (example outputs; actual names may vary)
ls out/dist
Image.lz4-dtb    modules/   System.map    vmlinux
```
As the Android docs note, “The kernel binary, modules, and corresponding image are located in the `out/BRANCH/dist` directory” ([Build kernels  |  Android Open Source Project](https://source.android.com/docs/setup/build/building-kernels#:~:text=The%20kernel%20binary%2C%20modules%2C%20and,directory)).  You can verify that an `Image.lz4-dtb` (GKI image with initramfs omitted) or `bzImage` is produced.  Rename or copy the kernel binary as needed for GRUB (e.g. `/boot/vmlinuz-android-mainline`).  

# Create a Minimal Android Initramfs (RAM disk)

Android’s boot ramdisk typically contains the first-stage `init` and `init.rc` scripts, and mount points for system, vendor, etc.  From AOSP docs (Android 10/11 style ramdisk):

```
ramdisk.img:
  /
    init             (first-stage init binary)
    init.rc          (init script)
    etc -> /system/etc  (symlink)
    system/          (mount point for system.img)
    vendor/          (mount point for vendor.img)
    odm/             (mount point for odm.img)
    ... 
```

 ([Ramdisk partitions  |  Android Open Source Project](https://source.android.com/docs/core/architecture/partitions/ramdisk-partitions#:~:text=Contains%20a%20kernel%20and%20a,img)) ([Ramdisk partitions  |  Android Open Source Project](https://source.android.com/docs/core/architecture/partitions/ramdisk-partitions#:~:text=)).  In our minimal initramfs, include at least:

- **/init** – a tiny init executable or script (must be executable).  This could be Android’s `init` binary (built from AOSP `system/core/init` for x86_64) or a simple shell script.  
- **/init.rc** – an init script that does early mounting.  For example, it might mount `proc`, `sysfs`, `devtmpfs`, then mount the system image.  
- **Empty dirs**: `/system`, `/vendor`, `/odm`, `/mnt` (etc). These serve as mount points for Android partitions.  
- **/fstab*.txt** (optional) – vendor or generic fstab files if you have them, but not strictly needed for a simple boot.  
- **/sepolicy/** (optional) – if you want SELinux enabled; for permissive, you can omit full policy and just pass `androidboot.selinux=permissive` (see below).  
- **(Optionally)** Symlink `etc -> /system/etc` to mimic Android’s layout.

For **mount logic**, your `/init` (or `/init.rc`) should do something like:

```bash
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
# Now mount Android partitions (assuming disk images or partitions are available)
mount -o loop /path/to/system.img /system
# If needed:
mount -o loop /path/to/vendor.img /vendor
mount -o loop /path/to/odm.img /odm

# Finally, exec the main init (from system):
exec /system/bin/init
```

(If using a script `/init`, start with `#!/bin/sh`).  Ensure `/init` has executable permissions.  Then package the initramfs:

```bash
cd initramfs/               # directory containing init, init.rc, etc.
find . | cpio --create --format newc | gzip > /boot/android-initrd.cpio.gz
```

This creates a gzipped cpio archive of your minimal ramdisk.  (Alternatively use Android’s `mkbootfs` tool to generate the cpio if you want proper file contexts – but if booting SELinux-permissive, it’s not required.)

Because Android’s `init` by default enforces SELinux, it’s simplest to boot with SELinux *permissive*. Add `androidboot.selinux=permissive` to the kernel command line (in GRUB config).  This disables enforcement on boot and avoids missing policy issues ([Ramdisk partitions  |  Android Open Source Project](https://source.android.com/docs/core/architecture/partitions/ramdisk-partitions#:~:text=Contains%20a%20kernel%20and%20a,img)) ([Ramdisk partitions  |  Android Open Source Project](https://source.android.com/docs/core/architecture/partitions/ramdisk-partitions#:~:text=)).  

# Grub Boot Setup

Finally, copy the kernel and ramdisk into your boot setup and update GRUB.  For example, place `vmlinuz-android` and `android-initrd.cpio.gz` in `/boot/`, then add a GRUB entry:

``` 
menuentry "Android GSI (x86_64)" {
    linux   /boot/vmlinuz-android root=/dev/ram0 rw androidboot.hardware=generic_x86_64 androidboot.selinux=permissive ...
    initrd  /boot/android-initrd.cpio.gz
}
```

Adjust `root=` and any other `androidboot.` parameters as needed.  The key is that GRUB will load the kernel and our initramfs, eliminating the need for a prebuilt `boot.img`.  On boot, the kernel will use our initramfs (with permissive SELinux) to mount the system image and start Android just as a normal GSI boot ([Ramdisk partitions  |  Android Open Source Project](https://source.android.com/docs/core/architecture/partitions/ramdisk-partitions#:~:text=Contains%20a%20kernel%20and%20a,img)).

**References:** Android kernel build docs ([Build kernels  |  Android Open Source Project](https://source.android.com/docs/setup/build/building-kernels#:~:text=mkdir%20android)) ([Build kernels  |  Android Open Source Project](https://source.android.com/docs/setup/build/building-kernels#:~:text=Note%3A%20You%20can%20switch%20among,mainline%20%26%26%20repo%20sync)); AOSP boot ramdisk layout ([Ramdisk partitions  |  Android Open Source Project](https://source.android.com/docs/core/architecture/partitions/ramdisk-partitions#:~:text=Contains%20a%20kernel%20and%20a,img)) ([Build kernels  |  Android Open Source Project](https://source.android.com/docs/setup/build/building-kernels#:~:text=The%20kernel%20binary%2C%20modules%2C%20and,directory)).
