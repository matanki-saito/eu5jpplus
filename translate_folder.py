import argparse
import json
import time
from pathlib import Path

import toml
from openai import OpenAI


def load_config(path="config.toml"):
    with open(path, "r", encoding="utf-8") as f:
        return toml.load(f)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="統計表示のみで翻訳を実行しない")
    return parser.parse_args()


def collect_stats(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    translated = sum(1 for x in data if x.get("translation"))
    untranslated = total - translated

    return total, translated, untranslated


def run_stats_only(source_folder):
    print("=== Translation Statistics (DRY RUN) ===")
    total_all = 0
    total_done = 0
    total_missing = 0

    for path in Path(source_folder).rglob("*.json"):
        total, done, missing = collect_stats(path)
        total_all += total
        total_done += done
        total_missing += missing

        print(f"[{path}] total={total}, translated={done}, missing={missing}")

    print("\n=== Summary ===")
    print(f"Total entries:       {total_all}")
    print(f"Translated:          {total_done}")
    print(f"Untranslated:        {total_missing}")
    print("==============================")


def preserve_surrounding_spaces(original: str, translated: str) -> str:
    """
    original の前後の空白を翻訳後に復元する
    """
    prefix = len(original) - len(original.lstrip(" "))
    suffix = len(original) - len(original.rstrip(" "))
    return " " * prefix + translated + " " * suffix


def call_translation_api(batch):
    """
    ChatGPT にまとめて翻訳する
    batch: [{"key":..., "original":..., "translation":...}, ...]
    """

    system_prompt = load_system_prompt()

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(batch, ensure_ascii=False)},
        ],
        temperature=0.2,
    )

    raw = completion.choices[0].message.content.strip()
    return json.loads(raw)


# system prompt を読み込む
def load_system_prompt(path="system_prompt.txt"):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def process_file(input_file, output_file):
    print(f"Start: {input_file}")

    # ① すでに output がある場合 → 未翻訳が残っているかチェック
    if output_file.exists():
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing = json.load(f)

            remaining_existing = [row for row in existing if not row.get("translation")]

            if len(remaining_existing) == 0:
                print(f"Skip (already translated): {output_file}")
                return  # 完全に翻訳済みならスキップ

            # 未翻訳がある → 続きから翻訳
            print(f"Resume translation: {output_file}")
            data = existing  # 続きから翻訳
        except Exception as e:
            print(f"Warning: failed to read existing output ({output_file}), re-translate. Error: {e}")
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

    else:
        # output が無い場合 → 通常開始
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    # 未翻訳のものだけ抽出
    remaining = [row for row in data if not row.get("translation")]

    if not remaining:
        print(f"Nothing to translate: {input_file}")
        return

    translated_count = 0

    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i:i + BATCH_SIZE]

        # API へ送信
        try:
            response = call_translation_api(batch)
        except Exception as e:
            print(f"API error on {input_file}: {e}")
            continue

        # 結果をマージ
        for translated_row in response:
            for row in data:
                if row["key"] == translated_row["key"]:
                    original = row["original"]
                    translated = translated_row.get("translation", "")
                    if translated:
                        translated = preserve_surrounding_spaces(original, translated)
                    row["translation"] = translated
                    break

        translated_count += len(response)
        print(f"Translated: {translated_count} lines in {input_file}")

        time.sleep(0.5)  # API 負荷抑制

    # 出力へ保存
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"export: {output_file}")


def main():
    input_dir = Path(config["paths"]["input_dir"])

    files = list(input_dir.rglob("*.json"))
    print(f"Found {len(files)} JSON files.")

    for input_path in files:
        rel = input_path.relative_to(input_dir)
        output_path = OUTPUT_DIR / rel

        process_file(input_path, output_path)

    print("🎉 完了！すべてのファイルを翻訳しました。")


if __name__ == "__main__":
    args = parse_args()
    config = load_config()

    if args.dry_run:
        run_stats_only(config["paths"]["output_dir"])
        exit(0)

    else:
        client = OpenAI(api_key=config["api"]["api_key"])
        MODEL = config["api"]["model"]
        OUTPUT_DIR = Path(config["paths"]["output_dir"])
        BATCH_SIZE = config["translation"]["batch_size"]

        main()

        exit(0)
