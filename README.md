# Neo's Freqtrade

[Freqtrade](https://github.com/freqtrade/freqtrade) を動かしてみた。

- Claude Code に聞きつつ環境構築・バグの修正を実施した
- OCI の Always Free VM (Arm ベース) に Docker をインストールし、[BitBank](https://bitbank.cc/) の API を利用してしばらく自動取引を動かしていた


## 試したストラテジー

- Strategy001 : <https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/Strategy001.py>
    - `freqtradeorg/freqtrade:develop` イメージで動作するようにした
    - メインで使用。1ヶ月くらいはぼちぼち稼げていたが、継続してプラスにならなかったため中止
- E0V1E_6 : <https://www.strat.ninja/overview.php?strategy=E0V1E_6>
    - `pandas_ta` を使用しないようにし、以下のようなワーニングが出ないように・FreqUI 上でのチャートが正常表示されるように修正した
        - `2026-04-16 05:40:31,038 - freqtrade.strategy.interface - WARNING - Unable to get latest candle (OHLCV) data for pair RENDER/USDT - void() takes at least 1 positional argument (0 given)`
    - Dry-Run で静観したがプラスにならなかったので中止した


## コマンド類

```bash
$ docker compose down && docker compose up -d
$ docker compose up -d --force-recreate
$ docker compose logs -f
```


## cctx の BitBank.py に日付関連のバグがある模様

> 今回の根本原因は ccxt 4.5.45のbitbank実装のバグ で、fetch_ohlcvがsince未指定のときlimit=1000件分さかのぼった日付でAPIを叩く仕様になっていた。5分足×1000本 = 約3.5日前の日付になるため、Freqtradeが今日のデータを取得できずに詰まっていた。
> 修正したファイルはdocker-compose.ymlのvolumeマウントで維持されているので、コンテナが再起動しても自動的に適用される。ccxtがバージョンアップして同じバグが修正された場合はマウントを外せばいい。

```bash
# コンテナからホストにコピー
$ docker compose run --rm --entrypoint cat freqtrade-strategy001 \
  /home/ftuser/.local/lib/python3.14/site-packages/ccxt/bitbank.py \
  > ~/freqtrade/bitbank_sync.py
$ docker compose run --rm --entrypoint cat freqtrade-strategy001 \
  /home/ftuser/.local/lib/python3.14/site-packages/ccxt/async_support/bitbank.py \
  > ~/freqtrade/bitbank_async.py

# 修正する
$ python3 << 'EOF'
files = [
    '/root/freqtrade/bitbank_sync.py',
    '/root/freqtrade/bitbank_async.py'
]

old = """        if since is None:
            if limit is None:
                limit = 1000  # it doesn't have any defaults, might return 200, might 2000(i.e. https://public.bitbank.cc/btc_jpy/candlestick/4hour/2020)
            duration = self.parse_timeframe(timeframe)
            since = self.milliseconds() - duration * 1000 * limit"""

new = """        if since is None:
            # Fix: always use today's date to get current candles
            import datetime
            today = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            since = int(today.timestamp() * 1000)
            if limit is None:
                limit = 1000"""

for f in files:
    with open(f, 'r') as fh:
        content = fh.read()
    if old in content:
        content = content.replace(old, new)
        with open(f, 'w') as fh:
            fh.write(content)
        print(f'Fixed: {f}')
    else:
        print(f'Pattern not found: {f}')
EOF

# 修正したファイルをマウントする
```


## Links

- [Neo's World](https://neos21.net/)
