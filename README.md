# ROYAL KLUDGE R65 JIS — 調査メモ

対象: `Gaming Keyboard`, VID `0x258A`, PID `0x01F7`。このリポジトリでは、ユーザーが取得したWindows公式ツールのHIDログを基に、FnレイヤーのLANG割り当てを調査・変更します。

## ログから確認できたこと

- 設定用HIDはusagePage `0xFF00`, usage `0x0001`。Feature Report IDは`0x06`。
- 公式ツールはReport 0x06のcommand `0x03`でキー配列を書き込みます。2バイト目がlayer番号で、通常レイヤーは`0`、Fnレイヤーは`1`です。送信ペイロードは519バイト。
- ユーザーのログでFn+MをAに設定したFnレイヤーペイロードでは、slot 46が`00 00 00 04`。
- 同じ配列のFn+Vはslot 28で、ログ取得時点の値は`00 00 00 05`（B）。
- 通常レイヤーslot 41は`00 00 00 8A`、slot 23は`00 00 00 8B`。この実機の配置に従い、slot 41をLANG1、slot 23をLANG2として扱います。
- 専用ツールでもFnレイヤーを読み戻せないとのユーザー報告があるため、PythonコードもFnレイヤーの読み出し・書き戻し検証は行いません。

## Fn+V=LANG2 / Fn+M=LANG1

`rk65_fn_layer_patch.py` は、キャプチャした公式ツールのログから最後の完全なlayer 1ペイロードを取り出し、slot 28をLANG2 (`00 00 00 8B`)、slot 46をLANG1 (`00 00 00 8A`)に置換します。ほかのFnレイヤーバイトは、そのログの値を維持します。

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
