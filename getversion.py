import os
import re
import subprocess
import tempfile

STEAMCMD_PATH = r"C:\steamcmd\steamcmd.exe"  # steamcmd.exe のパス
APPID = 3450310  # 調べたい AppID（例：Dota2）


def run_steamcmd(appid: int) -> str:
    """
    SteamCMD を実行して app_info_print の出力を取得する
    """

    # 一時ファイルに出力させる
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    temp_path = temp_file.name
    temp_file.close()

    cmd = [
        STEAMCMD_PATH,
        "+login", "anonymous",
        "+app_info_update", "1",
        "+app_info_print", str(appid),
        "+quit"
    ]

    # SteamCMD の標準出力をファイルに保存
    with open(temp_path, "w", encoding="utf-8", errors="ignore") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)

    # 読み込み
    with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()

    # 一時ファイル削除
    os.remove(temp_path)
    return data


def parse_buildids(text: str):
    """
    SteamCMD app_info_print の出力から buildid を抽出
    """

    depot_pattern = re.compile(
        r'"(?P<depot_id>\d+)"\s*\{[^}]*?"buildid"\s*"(?P<buildid>\d+)"',
        re.DOTALL
    )

    branch_block_pattern = re.compile(
        r'"branches"\s*\{(?P<block>.*?)\}',
        re.DOTALL
    )

    single_branch_pattern = re.compile(
        r'"(?P<branch>[^"]+)"\s*\{[^}]*?"buildid"\s*"(?P<buildid>\d+)"',
        re.DOTALL
    )

    result = {
        "depots": {},
        "branches": {}
    }

    # depot buildID の抽出
    for m in depot_pattern.finditer(text):
        d = m.group("depot_id")
        b = int(m.group("buildid"))
        result["depots"][d] = b

    # branch buildID の抽出
    m = branch_block_pattern.search(text)
    if m:
        block = m.group("block")
        for b in single_branch_pattern.finditer(block):
            branch = b.group("branch")
            buildid = int(b.group("buildid"))
            result["branches"][branch] = buildid

    return result


def main():
    print(f"SteamCMD を使用して AppID {APPID} の buildID を取得します…")

    output = run_steamcmd(APPID)
    parsed = parse_buildids(output)

    print("\n=== Depot buildIDs ===")
    for d, b in parsed["depots"].items():
        print(f"  Depot {d}: {b}")

    print("\n=== Branch buildIDs ===")
    for name, b in parsed["branches"].items():
        print(f"  Branch {name}: {b}")


if __name__ == "__main__":
    main()
