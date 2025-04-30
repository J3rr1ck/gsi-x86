# 🧰 Android GSI USB Builder (x86_64) This script automates the full process of building a mainline AOSP kernel, generating a bootable initramfs, and writing both (plus a GSI system image) to a USB device using GRUB — resulting in a bootable Android USB stick for x86_64 systems. 
--- 
## ✅ Features 
- Fetches and builds the **AOSP mainline kernel** for x86_64 using Bazel. 
- Generates a **minimal initramfs** compatible with Android's system-as-root. 
- Automatically **extracts a GSI ZIP** and installs it onto the USB. 
- Fully sets up **GRUB** for booting Android directly from USB. - Supports **AOSP and Lineage-based GSIs**. 
--- 
## 📦 Requirements 
- Arch Linux (or an Arch-based distro) 
- AOSP GSI `.zip` file containing at least: - `system.img` - `vbmeta.img` 
- ~10GB USB drive (⚠️ all data will be erased) 
- Internet connection (for kernel source + dependencies) 
--- 
## 🛠️ Installation 
```bash git clone https://github.com/yourname/android-usb-builder.git cd android-usb-builder chmod +x build_android_usb.py ``` 
--- 
## ⚙️ Configuration Edit these variables inside the script: ```python USB_DEVICE = "/dev/sdX" # Your USB device (e.g., /dev/sdb) GSI_ZIP = "aosp_gsi.zip" # Path to your downloaded GSI ZIP ``` 
> ⚠️ **Warning:** Double check that `USB_DEVICE` is correct. This script will reformat it. 
--- 
## 🚀 Usage ```bash sudo ./build_android_usb.py ``` This will: 1. Install required packages 2. Download and build the AOSP mainline kernel 3. Generate a simple Android-compatible initramfs 4. Partition and format your USB stick 5. Extract your GSI and copy it to the USB 6. Install GRUB and configure it to boot Android ---
## 🧪 Tested With 
- AOSP x86_64 GSIs from [ci.android.com](https://ci.android.com/) 
- LineageOS-based GSIs (phhusson treble) 
- QEMU and physical laptops 
--- 
## 📂 USB Layout 
``` /boot/ ├── vmlinuz-android ├── android-initrd.cpio.gz └── grub/grub.cfg /android/ ├── system.img └── vbmeta.img ``` 
--- 
## 🔧 Troubleshooting 
- **Boot hangs on init:** Try different GSIs, or verify `system.img` format. 
- **Black screen after GRUB:** Some hardware may need specific kernel parameters (e.g. `nomodeset`). 
- **Kernel won't build:** Ensure your Arch system is fully updated. 
--- 
## 📜 License MIT — use it, hack it, fork it. 
--- 
## 🤝 Contributions Welcome Pull requests to add more initrd logic, A/B slot support, NVIDIA patches, or kernel config options are appreciated!