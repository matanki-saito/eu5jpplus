## 機能概要

EU5はSteamcmdを通して4時間毎に更新があるかチェックされます。更新がある場合にはgithub actionsから利用できるwindows VMにインストールされ、その中にあるlocalization関係のファイルがgitに取り込まれます。またゲームバージョンを含んだ２つのテキストファイルを読み取りリリースタグを作ります。

## 処理フロー

```mermaid
flowchart TD
  A[Trigger_by_GAS] --> B[Job build]
  B --> C[Checkout]
  C --> D[Setup Python]
  D --> E[Update pip]
  E --> F[Install deps]
  F --> G[Download SteamCMD]
  G --> H[Set credentials]
  H --> I[Extract files]
  I --> J[Done]
```

Extract filesの処理は以下

```mermaid
flowchart TD
  A[Start] --> B[Steamcmd Info]
  B --> C[Parse Build IDs]
  C --> D{Build ID Match}
  D -- Yes --> Z[Stop No Update]
  D -- No --> E[Steamcmd Update]
  E --> F[Clear Source]
  F --> G[Copy Files]
  G --> H[Create Tag]
  H --> I[Git Push]
  I --> J[Create Release]
  J --> K[End]
```
