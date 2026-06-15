from urllib.parse import urlparse
from pathlib import Path
from tqdm import tqdm
import json

import models
import requestUtils
import fileUtils
import epubUtils
import config
import tools
import decrypt


def _config_resolve():
    """Build queue from config. Returns None if config is incomplete."""
    s = config.setting

    if s.adb.enable:
        import adbUtils
        if s.adb.auto:
            ids = adbUtils.list_books()
            if not ids:
                return None
            return ids
        else:
            if not s.adb.books:
                return None
            return [str(b) for b in s.adb.books]

    if s.manualBook.enable:
        try:
            json.loads(s.manualBook.jsonString)
        except (json.JSONDecodeError, TypeError):
            return None
        return ["1000000"]

    if s.batch.enable:
        if s.batch.auto:
            data_dir = Path("data")
            folders = []
            if data_dir.exists():
                for folder in data_dir.iterdir():
                    if folder.is_dir() and folder.name.isdigit():
                        folders.append(folder.name)
            return folders
        else:
            if not s.batch.queue:
                return None
            return [str(b) for b in s.batch.queue]

    # single book: batch.enable == False
    if s.batch.url:
        return [s.batch.url]

    return None


def _interactive_resolve():
    """Show menu and return queue. Returns None if user exits."""
    import menu

    choice = menu.show_main_menu()

    if choice == 0:
        return None
    elif choice == 1:
        url = menu.input_book_url()
        return [url] if url else _interactive_resolve()
    elif choice == 2:
        data_dir = Path("data")
        folders = []
        if data_dir.exists():
            folders = [f.name for f in data_dir.iterdir()
                       if f.is_dir() and f.name.isdigit()]
        if not folders:
            models.Print.warn("[WARN] data/ 目录下没有找到以数字命名的文件夹")
        return folders
    elif choice == 3:
        ids = menu.input_book_id_list()
        return ids if ids else _interactive_resolve()
    elif choice == 4:
        import adbUtils
        try:
            adbUtils.check_adb()
            adbUtils.pull_keys()
            fileUtils.TransformFilename("data/key")
            ids = adbUtils.list_books()
            if not ids:
                models.Print.warn("[WARN] 设备上未找到已下载的书籍")
                return _interactive_resolve()
            return ids
        except RuntimeError as e:
            models.Print.err(f"[ERR] ADB: {e}")
            return _interactive_resolve()
    elif choice == 5:
        ids = menu.input_book_id_list()
        if not ids:
            return _interactive_resolve()
        import adbUtils
        try:
            adbUtils.check_adb()
            adbUtils.pull_keys()
            fileUtils.TransformFilename("data/key")
            return ids
        except RuntimeError as e:
            models.Print.err(f"[ERR] ADB: {e}")
            return _interactive_resolve()
    elif choice == 6:
        s = config.setting
        try:
            json.loads(s.manualBook.jsonString)
        except (json.JSONDecodeError, TypeError):
            models.Print.err("[ERR] manualBook.jsonString 不是有效的 JSON")
            return _interactive_resolve()
        return ["1000000"]


def resolve_queue():
    mode = config.setting.interactive.mode

    if mode == "always":
        return _interactive_resolve()

    if mode == "never":
        q = _config_resolve()
        if q is None:
            models.Print.err("[ERR] 配置不完整且交互模式为 never，退出")
            exit(1)
        return q

    # mode == "auto"
    q = _config_resolve()
    if q is not None:
        return q
    return _interactive_resolve()


def _process_manual_book(book, bookJson):
    book.id = int(bookJson["bookID"])
    book.name = bookJson["bookName"]
    book.author = bookJson["authorName"]
    book.description = bookJson["bookDescription"]
    try:
        with open(Path(bookJson["coverPath"]), "rb") as f:
            book.cover = f.read()
    except Exception as e:
        models.Print.err(f"[ERR] coverPath 读取失败：{e}")
    chapter_dir = Path("data") / str(book.id)
    autoExtend = config.setting.manualBook.autoExtend
    if chapter_dir.exists():
        for file in chapter_dir.iterdir():
            if file.is_file() and file.stem.isdigit():
                title = bookJson.get("contents", {}).get(file.stem, file.stem)
                book.chapters.append(models.Chapters(id=int(file.stem), title=title))
    elif not autoExtend:
        models.Print.err(f"[ERR] 找不到书籍目录 {chapter_dir.resolve()}")
        return False
    return True


def process_book(entry: str):
    s = config.setting
    book = models.Book()

    # --- Manual book mode ---
    if s.manualBook.enable:
        try:
            bookJson = json.loads(s.manualBook.jsonString)
        except (json.JSONDecodeError, TypeError) as e:
            models.Print.err(f"[ERR] manualBook.jsonString 解析失败：{e}")
            return
        if not _process_manual_book(book, bookJson):
            return
        # manual mode builds chapter list from local files; skip network fetch
    else:
        # --- Parse book ID ---
        book.url = entry
        try:
            book.id = int(urlparse(str(book.url)).path.split('/')[-1])
        except (ValueError, IndexError):
            try:
                book.id = int(str(entry).strip())
            except ValueError:
                models.Print.err(f"[ERR] 无效的书籍标识：{entry}")
                return

    if not isinstance(book.id, int):
        models.Print.err(f"[ERR] 错误的输入：{entry}，这一项会被忽略")
        return

    # --- ADB pull ---
    if s.adb.enable:
        import adbUtils
        try:
            adbUtils.pull_book(book.id)
        except RuntimeError as e:
            models.Print.err(f"[ERR] ADB 拉取 {book.id} 失败：{e}")
            return

    # --- Preprocess ---
    fileUtils.RemoveNewlinesInEachFile(Path("data") / str(book.id))

    # --- Fetch metadata (skip in manual mode) ---
    if not s.manualBook.enable:
        try:
            if requestUtils.GetName(book) != 0:
                models.Print.err(f"[ERR] 无法获取 {book.id} 的书籍信息，跳过")
                return
            models.Print.info(f"[INFO] 获取到：标题: {book.name}， 作者： {book.author}")
        except Exception as e:
            models.Print.err(f"[ERR] GetName 异常 {book.id}: {e}")
            return

        try:
            if requestUtils.GetContents(book) != 0:
                models.Print.err(f"[ERR] 无法获取 {book.id} 的目录，跳过")
                return
        except Exception as e:
            models.Print.err(f"[ERR] GetContents 异常 {book.id}: {e}")
            return

    # --- Set up cache folders ---
    if s.cache.text:
        try:
            config.textFolder = tools.ProcessString(s.cache.textFolder, book)
            Path(config.textFolder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            models.Print.err(f"[ERR] textFolder 无效：{e}")

    if s.cache.image:
        try:
            config.imageFolder = tools.ProcessString(s.cache.imageFolder, book)
            Path(config.imageFolder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            models.Print.err(f"[ERR] imageFolder 无效：{e}")

    # --- Calculate derived paths ---
    config.CalculateParama(book)

    if book.decryptedTxt.exists():
        book.decryptedTxt.unlink(missing_ok=True)

    Path("output").mkdir(parents=True, exist_ok=True)

    # --- Decrypt chapters ---
    for chapter in tqdm(book.chapters, desc=models.Print.processingLabel("[PROCESSING] 解码中")):
        if chapter.isVolIntro:
            try:
                with open(book.decryptedTxt, "a", encoding="utf-8") as f:
                    f.write(f"{chapter.title}\n\n")
            except Exception as e:
                models.Print.err(f"[ERR] 保存卷介绍时出错：{e}")
            continue

        if chapter.decrypted.exists():
            try:
                with open(chapter.decrypted, "r", encoding="utf-8") as f:
                    txt = f.read()
                chapter.content = txt
                with open(book.decryptedTxt, "a", encoding="utf-8") as f:
                    f.write(chapter.title + "\n" + txt + "\n\n")
            except Exception as e:
                models.Print.err(f"[ERR] 读取缓存 {chapter.decrypted} 失败：{e}")
            continue

        try:
            with open(chapter.key, 'r', encoding="utf-8") as f:
                seed = f.read()
            with open(chapter.encryptedTxt, 'r', encoding="utf-8") as f:
                encryptedTxt = f.read()
            try:
                txt = decrypt.decrypt(encryptedTxt, seed)
                chapter.content = txt
                if s.cache.text:
                    with open(chapter.decrypted, "w", encoding="utf-8") as f:
                        f.write(txt)
                with open(book.decryptedTxt, "a", encoding="utf-8") as f:
                    f.write(f"{chapter.title}\n{txt}\n")
            except Exception as e:
                models.Print.err(f"[ERR] 解密 {chapter.encryptedTxt} 失败：{e}")
                continue
        except FileNotFoundError:
            if s.log.notFoundWarn:
                models.Print.warn(f"[WARN] {chapter.title} 未购买")
            chapter.content = "本章未购买"
        except Exception as e:
            models.Print.warn(f"[WARN] {e}")

    models.Print.info(f"[INFO] txt文件已生成：{book.safeName}")
    models.Print.info(f"[INFO] 正在打包Epub...")

    if s.homePage.enable:
        models.Print.warn("[INFO] 检测到书籍主页选项打开")
        hp = models.Chapters(isVolIntro=False, id=0, title=book.name)
        hp.content = tools.ProcessString(s.homePage.style, book)
        hp.isVolIntro = False
        book.chapters.insert(0, hp)

    epubUtils.GenerateEpub(book, str(Path("output") / f"{book.safeName}.epub"))


def main():
    config.init()

    # ADB init
    if config.setting.adb.enable:
        import adbUtils
        try:
            adbUtils.check_adb()
            adbUtils.pull_keys()
        except RuntimeError as e:
            models.Print.err(f"[ERR] ADB 初始化失败：{e}")
            if config.setting.interactive.mode == "never":
                exit(1)

    fileUtils.TransformFilename("data/key")

    models.Print.info(
        "[INFO] 本程序基于Zn90107UlKa/CiweimaoDownloader@github.com\n"
        "[INFO] 如果您是通过被售卖的渠道获得的本软件，请您立刻申请退款。\n"
        "[INFO] 仅供个人学习与技术研究\n"
        "[INFO] 禁止任何形式的商业用途\n"
        "[INFO] 所有内容版权归原作者及刺猬猫平台所有\n"
        "[INFO] 请在 24 小时内学习后立即删除文件\n"
        "[INFO] 作者不承担因不当使用导致的损失及法律后果"
    )

    queue = resolve_queue()
    if queue is None:
        return

    for entry in queue:
        try:
            process_book(entry)
        except Exception as e:
            models.Print.err(f"[ERR] 处理 {entry} 时发生未预期错误：{e}")


if __name__ == "__main__":
    main()
