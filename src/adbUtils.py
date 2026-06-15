import subprocess
from pathlib import Path
import models
import config

DEVICE_KEY_DIR = "/data/data/com.kuangxiangciweimao.novel/files/Y2hlcy8"
DEVICE_BOOKS_DIR = "/data/data/com.kuangxiangciweimao.novel/files/novelCiwei/reader/booksnew"
APP_DATA_DIR = "/data/data/com.kuangxiangciweimao.novel"
SDCARD_TMP = "/sdcard/cwmd_adb_tmp"

_device_serial: str = ""


def _adb(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run adb command with device serial if known."""
    if _device_serial:
        cmd = ["adb", "-s", _device_serial] + cmd
    else:
        cmd = ["adb"] + cmd
    return subprocess.run(cmd, capture_output=True, text=True)


def adb_su(cmd: str) -> subprocess.CompletedProcess:
    return _adb(["shell", f"su -c '{cmd}'"])


def _detect_device() -> str:
    """Find the device that has the ciweimao app installed."""
    r = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = r.stdout.strip().split("\n")[1:]  # skip header
    devices = [l.split("\t")[0] for l in lines if "\tdevice" in l]

    if not devices:
        return ""

    if len(devices) == 1:
        return devices[0]

    # Multiple devices: find the one with the ciweimao app
    for serial in devices:
        r = subprocess.run(
            ["adb", "-s", serial, "shell", f"su -c 'test -d \"{APP_DATA_DIR}\" && echo ok'"],
            capture_output=True, text=True
        )
        if "ok" in r.stdout:
            return serial

    return devices[0]  # fallback


def check_adb():
    global _device_serial

    specified = config.setting.adb.device if hasattr(config.setting.adb, "device") else ""
    if specified:
        _device_serial = specified
    else:
        _device_serial = _detect_device()

    if not _device_serial:
        models.Print.err("[ERR] 未检测到 adb 设备，请确认模拟器已开启 adb 调试")
        raise RuntimeError("adb device not found")

    models.Print.info(f"[INFO] adb 设备已连接：{_device_serial}")

    r = adb_su("id")
    if "uid=0" not in r.stdout:
        models.Print.err("[ERR] 模拟器未获取 root 权限")
        raise RuntimeError("root not available")
    models.Print.info(f"[INFO] root 权限正常")


def pull_keys():
    local_key = Path("data/key")
    # Key files are session-specific and must be re-pulled each run.
    if local_key.exists():
        import shutil
        shutil.rmtree(local_key)

    models.Print.info("[INFO] 正在从设备拉取密钥文件...")
    local_key.mkdir(parents=True, exist_ok=True)

    adb_su(f"cp -r '{DEVICE_KEY_DIR}' '{SDCARD_TMP}_key'")
    r = _adb(["pull", f"{SDCARD_TMP}_key/.", str(local_key)])
    adb_su(f"rm -rf '{SDCARD_TMP}_key'")

    if r.returncode != 0:
        models.Print.err(f"[ERR] 拉取密钥文件失败：{r.stderr}")
        raise RuntimeError("pull keys failed")
    models.Print.info(f"[INFO] 密钥文件拉取完成")


def pull_book(book_id: int):
    local_dir = Path("data") / str(book_id)
    if local_dir.exists() and (local_dir / "done").exists():
        models.Print.info(f"[INFO] data/{book_id}/ 已存在且已处理，跳过拉取")
        return

    models.Print.info(f"[INFO] 正在从设备拉取 {book_id} 的加密章节...")
    local_dir.mkdir(parents=True, exist_ok=True)

    src = f"{DEVICE_BOOKS_DIR}/{book_id}"
    tmp = f"{SDCARD_TMP}_{book_id}"
    adb_su(f"cp -r '{src}' '{tmp}'")
    r = _adb(["pull", f"{tmp}/.", str(local_dir)])
    adb_su(f"rm -rf '{tmp}'")

    if r.returncode != 0:
        models.Print.err(f"[ERR] 拉取 {book_id} 失败：{r.stderr}")
        raise RuntimeError(f"pull book {book_id} failed")
    models.Print.info(f"[INFO] {book_id} 章节拉取完成")


def list_books():
    r = adb_su(f"ls '{DEVICE_BOOKS_DIR}'")
    if r.returncode != 0:
        models.Print.err(f"[ERR] 无法列出设备上的书籍目录：{r.stderr}")
        return []
    ids = [line.strip() for line in r.stdout.split("\n") if line.strip().isdigit()]
    return ids
