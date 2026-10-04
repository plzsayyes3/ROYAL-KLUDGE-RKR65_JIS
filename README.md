# ROYAL KLUDGE R65 JIS — 調査メモ

対象: `Gaming Keyboard`, VID `0x258A`, PID `0x01F7`。このリポジトリでは、ユーザーが取得したWindows公式ツールのHIDログを基に、FnレイヤーのLANG割り当てを調査・変更します。

## ログから確認できたこと

- 設定用HIDはusagePage `0xFF00`, usage `0x0001`。Feature Report IDは`0x06`。
- 公式ツールはReport 0x06のcommand `0x03`でキー配列を書き込みます。2バイト目がlayer番号で、通常レイヤーは`0`、Fnレイヤーは`1`です。送信ペイロードは519バイト。
- ユーザーのログでFn+MをAに設定したFnレイヤーペイロードでは、slot 46が`00 00 00 04`。
- 同じ配列のFn+Vはslot 28で、ログ取得時点の値は`00 00 00 05`（B）。
- 書き込み前の通常レイヤーslot 41=`00 00 00 8A`、slot 23=`00 00 00 8B`は変換・無変換の旧キーコードであり、LANG1/LANG2としては反応しませんでした。
- LANG1/LANG2はアプリのファームウェアコード`0x9000`/`0x9100`をReport 0x06上で`00 00 00 90`/`00 00 00 91`として格納します。
- 専用ツールでもFnレイヤーを読み戻せないとのユーザー報告があるため、PythonコードもFnレイヤーの読み出し・書き戻し検証は行いません。

## Fn+V=LANG2 / Fn+M=LANG1

`rk65_fn_layer_patch.py` は、キャプチャした公式ツールのログから最後の完全なlayer 1ペイロードを取り出し、slot 28（Fn+V）をLANG2 (`00 00 00 91`)、slot 46（Fn+M）をLANG1 (`00 00 00 90`)に置換します。ほかのFnレイヤーバイトは、そのログの値を維持します。

既定ではドライランです。

```sh
python3 rk65_fn_layer_patch.py /path/to/captured-hid-log.txt
```

実機へ送る場合のみ`--write`を付けます。送信直前に対象デバイスを一意に確認し、確認語句 `WRITE RK65 PID 01F7` の入力を要求します。

```sh
python3 rk65_fn_layer_patch.py /path/to/captured-hid-log.txt --write
```

重要: Fnレイヤー全体を書き込む形式です。元にするログ取得後に公式ツールでFnレイヤーを編集していると、その後の変更はログ時点の配列に戻る可能性があります。書き込み後の読み戻し・成功確認はできません。`--write`は十分に理解したうえで明示的に実行してください。

このツールのオフラインテスト:

```sh
python3 -m unittest discover -s tests -v
```

## 通常レイヤーのスペース隣接キー

`rk65_layer0_language_patch.py` は、読み取り専用プローブで作ったJSONバックアップを元に、slot 23（Space左）をLANG2、slot 41（Space右）をLANG1にします。その他の通常レイヤー配列を保持し、slot 23/41が想定した旧値でない場合は中止します。

```sh
python3 rk65_layer0_language_patch.py /path/to/rk65-backup.json
python3 rk65_layer0_language_patch.py /path/to/rk65-backup.json --write
```

本体への送信後は、通常レイヤーを読み取り専用プローブで再読取できます。今回の実機書き込みではslot 23=`00 00 00 91`、slot 41=`00 00 00 90`を確認済みです。
