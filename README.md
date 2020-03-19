# Tasks
## タスク1
期限: 3/20
- [x] Raspberry Pi に Raspbian Stretch LITE (※GUI無しです) をインストール。
- [x] ホストPCからssh接続。
- [x] python3でコンソールにhello world。
## タスク1.5
期限: 3/23
- [ ] アナログ入力センサをI2C ADCに配線。
## タスク2
期限: 3/25
- [ ] python3で6つのI2Cセンサを読み取り、コンソールに表示。
## タスク3
期限: 3/27
- [ ] タスク2のセンサ取得とコンソール表示をマルチスレッドで分割する。
- [ ] それぞれクラスにしてファイルを分割する。
## タスク4
期限: 3/31
- [ ] python3のpaho.mqttライブラリを使ってpublishとsubscribeのexampleを実行。
- [ ] subscrebeしたメッセージをコンソールに表示。
## タスク5
期限: 3/31
- [ ] タスク4のmqtt通信とコンソール表示をマルチスレッドで分割する。
- [ ] それぞれクラスにしてファイルを分割する。
## タスク6
期限: 3/31
- [ ] タスク3と5を結合し、I2Cで取得したセンサ値をmqttでpublishする。
## タスク7
期限: 3/31
- [ ] ラズパイの電源を入れたら、タスク6が自動で実行できるようにする。

---

# 開発の方針
基本的にはissue駆動開発とし、
1. タスクに対してissueを立てる
2. 自分が担当する場合issueのassignerに自分を選択
2. それに対応させた名前のブランチを切る
3. PRを送る(mergeする際はmasterのコミットログが見やすいようにSquash and merge)

のような流れで進めていきたいと思います

---

# ラズパイ側の設定
これは僕だけで使うものではないので、ラズパイ側でしている(明記しておいた方がいいと考えられる)設定について以下に書いておきます

## alias
開発の便利のためにaliasを設定しています。不都合が生じた場合は`.bashrc`を変更してください
|alias|元コマンド|概説|
|:-|:-|:-|
|python|python3|python2系で実行するのを防ぐためです|
|pip   |pip3   |python2系で実行するのを防ぐためです|

## 開発環境
仮想環境の構築に **pipenv** を利用しています。  
依存関係などを見たい場合には、`PubSubSensor`のディレクトリに入ったうえで
```bash
pipenv run pip check
```
を実行してください。

新たにライブラリをインストールする、プログラムを実行するなど、仮想環境内でのコマンドが多くなる場合は
```bash
pipenv shell
```
をすることで`pipenv run`の部分が不要になります

具体的には、
```bash
pipenv run pip install numpy
pipenv run pip check
pipenv run python hoge.py
```
のような流れは
```bash
pipenv shell
pip install numpy
pip check
python hoge.py
```
と等価です。

## 再起動時の自動実行について
再起動時に自動的にスクリプトが走るように、`.bashrc`に
```bash
python [ファイル名].py
```
とします(メインで走らせるファイル名については未定なので決まり次第変更します)


---

# メモ
|日付|概要|メモ|
|:-:|:-:|:-:|
|3/14|リポジトリ開設、開発開始|ラズパイ、センサー等の発注をしていていただいた、到着次第メイン開発を開始するが、それまでできることをやっておく(MQTTなど)|
|3/17|ラズパイ到着|セットアップをしてタスク1を終了させた|
|3/18|タスク2.5の挿入と納期延長|アナログ入力のモジュールが追加されたのでそのタスクが2.5になった。納期が3日くらい延びた|
|3/19|センサ到着|はんだごてがないので追加でとどけてもらうことになった|
|3/19|センサが増えた|センサが増えた|
