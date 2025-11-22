import os
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

TARGET_DIR = "source"
OUTPUT_ROOT = "diff_output"
ZIP_NAME = "diff_output.zip"

# GitHub upload settings
REPO_OWNER = os.environ.get("REPO_OWNER", "matanki-saito")
REPO_NAME = os.environ.get("REPO_NAME", "eu5jpplus")

GITHUB_REPO = f"{REPO_OWNER}/{REPO_NAME}"  # ← ここを変更
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")


def run_git(args):
    return subprocess.check_output(args, encoding="utf-8", errors="ignore")


def main():
    # 🔹タグの動的取得
    print("🔍 最新タグを取得中...")
    tags = run_git(["git", "tag", "--sort=-creatordate"]).splitlines()

    if len(tags) < 2:
        print("❌ タグが2つ以上必要です（差分を取れません）")
        sys.exit(1)

    TAG_NEW = tags[0]
    TAG_OLD = tags[1]
    print(f"TAG_NEW = {TAG_NEW}")
    print(f"TAG_OLD = {TAG_OLD}")

    print("🔍 差分ファイルの取得中...")
    diff_files = run_git(["git", "diff", "--name-only", TAG_OLD, TAG_NEW, TARGET_DIR]).splitlines()

    if not diff_files:
        print("差分なし → 終了")
        exit(0)

    # 差分抽出
    for file_path in diff_files:
        diff = run_git(["git", "diff", TAG_OLD, TAG_NEW, "--", file_path])
        added_lines = []
        for line in diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])

        if not added_lines:
            continue

        out_file = Path(OUTPUT_ROOT) / file_path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(added_lines))

    print("📁 差分抽出完了")

    # ZIP化
    print("📦 ZIP作成中...")
    if Path(ZIP_NAME).exists():
        os.remove(ZIP_NAME)

    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in Path(OUTPUT_ROOT).rglob("*"):
            zipf.write(file, file.relative_to(OUTPUT_ROOT))

    print(f"ZIP 作成完了 → {ZIP_NAME}")

    # Release upload
    if not GITHUB_TOKEN:
        print("⚠ GITHUB_TOKEN が設定されていないためアップロードをスキップします")
        exit(0)

    print("☁ GitHub Release にアップロード中...")

    # release 情報取得
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    release_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{TAG_NEW}"
    release = requests.get(release_url, headers=headers)

    if release.status_code != 200:
        raise RuntimeError(f"リリース取得に失敗しました。タグ {TAG_NEW} が存在しているか確認してください。")

    upload_url = release.json()["upload_url"].split("{")[0] + f"?name={ZIP_NAME}"

    # ファイル送信
    with open(ZIP_NAME, "rb") as f:
        r = requests.post(upload_url, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/zip"
        }, data=f)

    if r.status_code >= 200 and r.status_code < 300:
        print("🎉 アップロード成功")
    else:
        print("❌ アップロード失敗")
        print(r.status_code, r.text)


if __name__ == "__main__":
    main()
