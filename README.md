# Royal Kludge R65 JIS — 配列・キー割り当て調査

Royal Kludge R65 JIS候補（`Gaming Keyboard`, VID `0x258A` / PID `0x01F7`）を実機で調べ、macOS日本語入力向けのキー割り当てを試した記録です。ユーザーが取得したRK公式ツールのHIDログと、実機での読み書き結果をもとにしています。

これは公式ツールでも汎用リマッパーでもありません。対象の1台で確認した非公式の調査・実験用ツールです。他のR65、別PID、別ファームウェアで同じように動くとは限りません。

## 現在の割り当て

| レイヤー | キー | 割り当て | 実機確認 |
|---|---|---|---|
| 表（layer 0） | Space左の無変換 | LANG2 / 英数 | 読み戻し確認済み |
| 表（layer 0） | Space右の変換 | LANG1 / かな | 読み戻し確認済み |
| 表（layer 0） | Lの右隣（`; / +`） | ハイフンキー。macOS日本語入力で「ー」 | 読み戻し確認済み・動作確認済み |
| Fn（layer 1） | Fn+R | 左GUI（macOS Command）+ Enter | ユーザー動作確認済み |
| Fn（layer 1） | Fn+V | LANG2 / 英数 | 書き込み送信済み。Fn層を読み戻せないため、個別の実機確認は未記録 |
| Fn（layer 1） | Fn+M | LANG1 / かな | 書き込み送信済み。Fn層を読み戻せないため、個別の実機確認は未記録 |

LANG1/LANG2は、この実機のReport 0x06上ではそれぞれ`00 00 00 90` / `00 00 00 91`です。元の`0x8A` / `0x8B`は変換・無変換のキー値で、LANG1/LANG2としては機能しませんでした。

## バックアップ

[2層バックアップJSON](rk65-r65-01f7-two-layer-backup-20261004.json)

- layer 0は、割り当て後に実機から読み取った応答と、対応する書き込みペイロードです。
- layer 1は、公式ツールの送信ログにFn+R/V/Mの割り当てを重ねた復元用ペイロードです。Fn層は実機から読み戻せなかったため、実機ダンプではありません。

バックアップには配列全体が含まれます。別の配列や更新後のFn設定へ無条件に書き戻さないでください。

## ファイル

- `rk65_layer0_language_patch.py` — Space両隣にLANG2/LANG1を割り当てる実験用ツール。
- `rk65_layer0_prolonged_sound.py` — L右隣をハイフンキーへ割り当てる実験用ツール。
- `rk65_fn_layer_patch.py` — キャプチャした公式ツールのログをもとに、Fn+V/M/Rを設定する実験用ツール。
- `tests/` — HIDを送信しない、ペイロード生成・検査のテスト。

通常レイヤーを読み取るプローブは[元のKeyboardリポジトリ](https://github.com/plzsayyes3/Keyboard/tree/main/rk65/tools)にあります。Fnレイヤーの読取機能はありません。

## 実行方法

Python 3とHIDAPIが必要です。macOSでは、端末から次のようにインストールできます。

```sh
python3 -m pip install hidapi
```

まず通常レイヤーを読み取り、バックアップを作ります。読み取りだけならキー設定は変更されません。

```sh
python3 /path/to/Keyboard/rk65/tools/beiying_read_probe.py --output rk65-backup.json
```

### 通常レイヤー

各ツールはドライランが既定です。

```sh
python3 rk65_layer0_language_patch.py rk65-backup.json
python3 rk65_layer0_prolonged_sound.py rk65-backup.json
```

内容を確認したあと、本体へ送るときだけ`--write`を付け、表示された確認語句を入力します。

```sh
python3 rk65_layer0_language_patch.py rk65-backup.json --write
python3 rk65_layer0_prolonged_sound.py rk65-backup.json --write
```

これらのパッチは調査時の元キー値（slot 23=`0x8B`、slot 41=`0x8A`、slot 63=`0x33`）を検査します。すでに変更済みのバックアップでは安全のため処理を中止します。現在のバックアップは変更後の状態です。

### Fnレイヤー

`rk65_fn_layer_patch.py`は、公式ツールが出力した`SetFeature [519] bytes -> ...`の完全なHIDログを入力に使います。提示したログと同じ元配列（Fn+R空、Fn+V=B、Fn+M=A）であることを確認してから、layer 1全体の送信データを作ります。

```sh
python3 rk65_fn_layer_patch.py /path/to/captured-hid-log.txt
python3 rk65_fn_layer_patch.py /path/to/captured-hid-log.txt --write
```

Fnレイヤー全体を書き込むため、元ログ取得後に行った別のFn割り当ては上書きされる可能性があります。Fn層はこのインターフェースから読み戻せないので、送信成功表示はキー動作の保証ではありません。書き込み後は実機で試してください。

## 安全性と制約

- 対象として確認したのは有線接続の`0x258A:0x01F7`と設定用HID interface（usagePage `0xFF00`, usage `0x0001`）です。
- 通常レイヤーの読み戻しは可能でした。Fnレイヤーの読み戻しは、専用ツールと本調査の読取要求ではできませんでした。
- 書き込みは一部のキーだけを差し替えた配列全体を送ります。スクリプトは想定外の元値を検出すると中止しますが、書き込み前にドライラン結果を必ず確認してください。
- 他の設定ツールやブラウザーからキーボードを開いている場合は閉じてください。送信中にUSBケーブルを抜かないでください。
- 本体設定が変化する操作です。バックアップを保管し、内容と対象機種を確認したうえで自己責任で使用してください。
- これはmacOSでの実機調査記録です。他OSの配列解釈や、別リビジョンでの動作は検証していません。

## テスト

テストはオフラインで実行でき、HIDデバイスへ接続・送信しません。

```sh
python3 -m unittest discover -s tests -v
```

## ライセンス

現時点でライセンスは設定していません。公開リポジトリですが、再配布・改変・商用利用の許可範囲は明示されていません。
