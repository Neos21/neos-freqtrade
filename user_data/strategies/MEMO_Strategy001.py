# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
from pandas import DataFrame
# --------------------------------

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class Strategy001(IStrategy):
    """
    学習用メモ版 Strategy001
    
    元ファイル: Strategy001.py
    目的: 売買ロジックの意図を日本語コメントで追いやすくする
    
    一言でいうと:
    EMAクロス + 平均足で流れに乗るシンプルトレンドフォロー戦略
    
    用語メモ:
    - EMA = Exponential Moving Average（指数移動平均）
      新しい価格ほど重みを大きくする移動平均。トレンド転換を比較的早く捉えやすい。
    - HA = Heikin-Ashi（平均足）
      ローソク足を平滑化して、上昇/下降の流れを見やすくする手法。
    """
    
    INTERFACE_VERSION: int = 3
    
    # 利確テーブル（経過分ごとの期待利益率）
    minimal_roi = {
        "60": 0.01,
        "30": 0.03,
        "20": 0.04,
        "0": 0.05,
    }
    
    # 損切り率（-10%）
    stoploss = -0.10
    
    # 5分足で判定
    timeframe = '5m'
    
    # トレーリングは無効（固定ロジック）
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    
    # 新規足が確定したタイミングだけで計算する
    process_only_new_candles = True
    
    # Exitシグナルを使う設定
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = False
    
    # 注文種別
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
    }
    
    # パラメータ意味辞典（推奨調整方向つき）
    # 使い方:
    # - 感度を上げる = シグナルを出しやすくする（エントリー回数は増えやすい）
    # - 感度を下げる = シグナルを厳しくする（ダマシは減りやすい）
    PARAMETER_GUIDE = {
        "minimal_roi": {
            "意味": "保有時間ごとに必要な利益率を定義する利確テーブル。",
            "推奨調整方向": "早めに利確したい場合は各値を下げる。伸ばしたい場合は各値を上げる。"
        },
        "stoploss": {
            "意味": "許容する最大損失率（負値）。",
            "推奨調整方向": "損失を抑えたいなら絶対値を小さく（例 -0.10→-0.07）。耐えるなら大きく。"
        },
        "timeframe": {
            "意味": "売買判定に使う足種。",
            "推奨調整方向": "短い足は高頻度・ノイズ増、長い足は低頻度・安定寄り。"
        },
        "ema20/ema50/ema100": {
            "意味": "短期/中期/長期のトレンド確認用EMA。",
            "推奨調整方向": "期間を短くすると反応が速くなる。長くすると遅いがダマシが減りやすい。"
        },
        "use_exit_signal": {
            "意味": "populate_exit_trend の終了シグナルを利用するか。",
            "推奨調整方向": "Trueでルール退出を重視。FalseでROI/SL主導に寄せる。"
        },
        "exit_profit_only": {
            "意味": "含み益時のみ exit シグナルで決済する。",
            "推奨調整方向": "Trueは損切り回避寄り、Falseは柔軟に撤退しやすい。"
        },
        "ignore_roi_if_entry_signal": {
            "意味": "エントリー継続シグナル時にROI制約を無視するか。",
            "推奨調整方向": "トレンド追従を強めるならTrue、利確優先ならFalse。"
        },
    }
    
    def informative_pairs(self):
        # 追加の情報足は使わない
        return []
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 3本のEMAで短期・中期・長期トレンドを見る
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema100'] = ta.EMA(dataframe, timeperiod=100)
        
        # ローソク足をHeikin-Ashiに変換してノイズを減らす
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['ha_open'] = heikinashi['open']
        dataframe['ha_close'] = heikinashi['close']
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # エントリー条件
        # 1) ema20 が ema50 を上抜け（上昇転換）
        # 2) HA終値が ema20 より上（上昇優位）
        # 3) HA陽線（勢い確認）
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe['ema20'], dataframe['ema50'])
                & (dataframe['ha_close'] > dataframe['ema20'])
                & (dataframe['ha_open'] < dataframe['ha_close'])
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # エグジット条件
        # 1) ema50 が ema100 を上抜け
        # 2) HA終値が ema20 より下
        # 3) HA陰線
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe['ema50'], dataframe['ema100'])
                & (dataframe['ha_close'] < dataframe['ema20'])
                & (dataframe['ha_open'] > dataframe['ha_close'])
            ),
            'exit_long'
        ] = 1
        
        return dataframe
