#!/usr/bin/env python3
import os
import subprocess
import shutil
import sys
from pathlib import Path

# === Config ===
KERNEL_BRANCH = "common-android-mainline"
KERNEL_BUILD_CONFIG = "common-modules/virtual-device/build.config.virtual_device.x86_64"
INITRAMFS_DIR = Path("initrd")
USB_DEVICE = "/dev/sdX"  # <-- Replace this with your actual USB device
USB_MOUNT = "/mnt/android_usb"
USB_BOOT_DIR = f"{USB_MOUNT}/boot"
GSI_ZIP = "aosp_gsi.zip"  # Path to the GSI zip file

# === Helpers ===
def run(cmd, cwd=None):
    print(f"[RUN] {cmd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

def ensure_dirs():
    INITRAMFS_DIR.mkdir(parents=True, exist_ok=True)
    os.makedirs(USB_BOOT_DIR, exist_ok=True)

def install_dependencies():
    deps = [
        "base-devel", "git", "python", "jdk21-openjdk ", "clang", "bc", "libelf", "kmod",
        "cpio", "perl", "xz", "wget", "repo", "bazel", "unzip"
    ]
    run(f"sudo pacman -Sy --needed {' '.join(deps)}")

def fetch_kernel():
    if not Path("android-kernel").exists():
        run(f"mkdir android-kernel && cd android-kernel && repo init -u https://android.googlesource.com/kernel/manifest -b {KERNEL_BRANCH} && repo sync")

def build_kernel():
    os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-21-openjdk"
    os.chdir("android-kernel")
    run(f"bazel run //common-modules/virtual-device:virtual_device_x86_64_dist -- --destdir=out/dist")
    os.chdir("..")

def copy_kernel():
    src_img = Path("android-kernel/out/dist/Image.lz4-dtb")
    if not src_img.exists():
        raise FileNotFoundError("Kernel image not found.")
    shutil.copy(src_img, f"{USB_BOOT_DIR}/vmlinuz-android")

def build_initramfs():
    (INITRAMFS_DIR / "init").write_text("""#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /system /vendor /odm /mnt
mount -o loop /android/system.img /system
exec /system/bin/init
""")
    os.chmod(INITRAMFS_DIR / "init", 0o755)
    (INITRAMFS_DIR / "init.rc").write_text("on early-init\n    mount all\n")
    for d in ["system", "vendor", "odm", "mnt"]:
        (INITRAMFS_DIR / d).mkdir(exist_ok=True)
    run(f"cd {INITRAMFS_DIR} && find . | cpio --create --format newc | gzip > ../android-initrd.cpio.gz")
    shutil.move("android-initrd.cpio.gz", f"{USB_BOOT_DIR}/android-initrd.cpio.gz")

def extract_gsi():
    run(f"unzip -o {GSI_ZIP} -d extracted_gsi")
    os.makedirs(f"{USB_MOUNT}/android", exist_ok=True)
    shutil.copy("extracted_gsi/system.img", f"{USB_MOUNT}/android/system.img")
    shutil.copy("extracted_gsi/vbmeta.img", f"{USB_MOUNT}/android/vbmeta.img")

def partition_usb():
    print("Partitioning USB device...\n⚠️ Make sure USB_DEVICE is correct: " + USB_DEVICE)
    run(f"sudo parted -s {USB_DEVICE} mklabel gpt")
    run(f"sudo parted -s -a optimal {USB_DEVICE} mkpart primary fat32 1MiB 100%")
    run(f"sudo mkfs.vfat -F32 -n ANDROID_USB {USB_DEVICE}1")
    run(f"sudo mount {USB_DEVICE}1 {USB_MOUNT}")
    os.makedirs(f"{USB_BOOT_DIR}", exist_ok=True)

def install_grub():
    run(f"sudo grub-install --target=i386-pc --boot-directory={USB_MOUNT}/boot {USB_DEVICE}")

def write_grub_cfg():
    grub_cfg = f"""
menuentry 'Android GSI (x86_64)' {{
    linux /boot/vmlinuz-android root=/dev/ram0 rw androidboot.selinux=permissive androidboot.hardware=generic_x86_64
    initrd /boot/android-initrd.cpio.gz
}}
"""
    os.makedirs(f"{USB_MOUNT}/boot/grub", exist_ok=True)
    with open(f"{USB_MOUNT}/boot/grub/grub.cfg", "w") as f:
        f.write(grub_cfg)

def main():
    ensure_dirs()
    install_dependencies()
    fetch_kernel()
    build_kernel()
    partition_usb()
    install_grub()
    copy_kernel()
    build_initramfs()
    extract_gsi()
    write_grub_cfg()
    print("\n✅ Fully bootable Android USB prepared!")

if __name__ == "__main__":
    main()
