from colorama import Back, Fore, Style

MENU_OPTIONS = {
    1: "Download single book (enter URL/ID)",
    2: "Batch download - auto scan local folders",
    3: "Batch download - from queue list",
    4: "ADB mode - auto scan device books",
    5: "ADB mode - manual book ID list",
    6: "Manual book (JSON config)",
    0: "Exit",
}


def _input_styled(prompt: str) -> str:
    return input(Back.LIGHTWHITE_EX + Fore.BLACK + Style.BRIGHT + prompt + Style.RESET_ALL)


def _select(valid_range: range, prompt: str) -> int:
    while True:
        try:
            raw = _input_styled(prompt)
            if not raw.strip():
                continue
            val = int(raw.strip())
            if val in valid_range:
                return val
        except ValueError:
            pass


def show_main_menu() -> int:
    print()
    print(Style.BRIGHT + "=" * 52 + Style.RESET_ALL)
    print(Style.BRIGHT + Fore.CYAN + "  Ciweimao Downloader" + Style.RESET_ALL)
    print(Style.BRIGHT + "=" * 52 + Style.RESET_ALL)
    for idx, label in MENU_OPTIONS.items():
        num = str(idx).rjust(2)
        print(f"  {Fore.YELLOW}{num}{Style.RESET_ALL}. {label}")
    print(Style.BRIGHT + "=" * 52 + Style.RESET_ALL)
    return _select(range(0, 7), "Please select [0-6]: ")


def input_book_url() -> str:
    return _input_styled("Enter book URL or numeric ID: ").strip()


def input_book_id_list() -> list[str]:
    raw = _input_styled("Enter book IDs separated by commas: ")
    return [s.strip() for s in raw.split(",") if s.strip().isdigit()]


def confirm(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        answer = _input_styled(prompt + suffix).strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
