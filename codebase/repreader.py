import os, sys, re as regex, numpy
from pandas import Series, DataFrame
from pandas import Timestamp, Timedelta, DateOffset
from pandas import Index, DatetimeIndex, MultiIndex
from pandas import concat, merge_asof, date_range
from pandas import read_html, read_csv

sys.path.append("./")
from codebase.utils import *
from codebase.connector import *

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Main class ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

class ReportReader:

    HEADER_EVENTS_VER = {
        4: ["#", "time", "event", "id", "lot", "price", "sl", "tp", "profit", "balance", "symbol"],
        5: ["#", "time", "event", "id", "lot", "price", "sl", "tp", "profit", "balance", "symbol"],
    }
    HEADER_EVENTS = {"event": str, "id": int, "lot": float, "price": float,
        "sl": float, "tp": float, "profit": float, "balance": float, "symbol": str}
    HEADER_TRADES = {"time_s": Timestamp, "time_e": Timestamp, "time_x": Timestamp,
        "price_e": float, "price_x": float, "price_s": float, "symbol": str, "lot": float,
        "entry": str, "exit": str, "reqs": int, "sl": float, "tp": float, "balance": float}
    
    PATH_PRICES = "./utils/prices/{symbol}_{month}.csv"
    EXIT_MAPPER = {"s/l": "sl", "t/p": "tp", "close at stop": "end"}
    SYMBOL_SPECS = read_csv("./utils/specs.csv", index_col = "symbol")
    GROWTH_FACTORS = Index(numpy.linspace(0, 1, 5))
    COLUMNS_TICKS = ["time", "worst_ask", "worst_bid"]
    CANDLE_SAMPLER = dict(worst_ask = "max", worst_bid = "min")

    FIELDS_INIT = dict(
        symbol = "symbol", time_s = "time",
        lot = "lot", growth = "growth")

    EVENTS_EN = ["buy", "sell"]
    EVENTS_ORD = ["buy limit", "buy stop", "sell limit", "sell stop"]
    EVENTS_MOD = ["modify", "cancel", "close"]
    EVENTS_EX = ["s/l", "t/p", "close at stop", "close"]
    SIGN_ENTRY = {"buy": 1.0, "sell": -1.0}

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def from_registry(cls, reg: dict):

        ea, mtver = reg["id"], reg["mtver"]
        path = Connector.PATH_TERMINAL_COMMON
        path = path + ea + ".html"

        header, events = read_html(io = path)
        header = cls.process_header(header)
        events["symbol"] = header["symbol"]
        dep = float(header["usd_deposit"])

        events.columns = cls.HEADER_EVENTS_VER[mtver]
        events = events.iloc[1 :, 1 :].set_index("time")
        events.index = DatetimeIndex(events.index)

        events["balance"].iloc[0] = dep
        events["profit"] = events["profit"].fillna(0)
        events["balance"] = events["balance"].ffill()
        report = cls(events, ea, mtver).run()
        report.header = header.copy()
        return report
    
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def __init__(self, events: DataFrame, system: str, mtver: int = 5, lever: int = 100):

        self.lever = lever
        events: DataFrame = events.copy()
        self.system, self.header = system, DataFrame()
        ev_columns = Index(self.HEADER_EVENTS_VER[mtver])
        assert set(events.columns).issubset(ev_columns)
        ev_columns = ev_columns.intersection(events.columns)
        self.events = events[ev_columns]
        for column, dtype in self.HEADER_EVENTS.items():
            self.events[column] = self.events[column].astype(dtype)

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def process_header(cls, header: DataFrame, lever: int = 100):

        symbol = header.iloc[0, -1].split(" ")[0]
        tframe = header.iloc[1, -1].split(" ")[: -3]
        tstart = Timestamp(str.join(" ", tframe[3 : 5]))
        tuntil = Timestamp(str.join(" ", tframe[6 :]))
        tframe = Timedelta(str.join(" ", tframe[: 2]))

        params = header.iloc[3, -1].replace(";", ",")
        params = Series(eval("dict(%s)" % params))
        params.index = "$PAR_" + params.index
        header = header.iloc[4 :]
        
        regex_dec = regex.compile("[0-9]+\\.[0-9]+")
        x_ask_gain = float(regex_dec.findall(header.iloc[9, 5])[0]) / 100
        x_bid_gain = float(regex_dec.findall(header.iloc[9, 3])[0]) / 100

        header = map(header.get, range(1, header.shape[1], 2))
        header: Series = concat(map(Series, header)).dropna()
        header = header.str.replace("( |\(.*|%)", "", regex = True)
        header = header.loc[~ header.str.contains("[A-Za-z]")]
        header = header.reset_index(drop = True)

        n_ask_g = int(round((n_ask := int(header[11])) * x_ask_gain))
        n_bid_g = int(round((n_bid := int(header[21])) * x_bid_gain))
        n_ask_l, n_bid_l = n_ask - n_ask_g, n_bid - n_bid_g
        
        return Series(name = "header", data = {
            "symbol": symbol, "timeframe": tframe, "t_start": tstart, "t_until": tuntil, "span": tuntil - tstart,
            "usd_deposit": float(header[2]), "usd_gain_par": float(header[8]), "usd_loss_par": - float(header[19]),
            "usd_total": float(header[3]), "usd_gain_avg": float(header[14]), "usd_loss_avg": - float(header[24]),
            "usd_gain_max": float(header[13]), "usd_loss_max": - float(header[23]), "ddwn_usd": float(header[10]),
            "ddwn_prc": float(header[20]) / 100, "prof_factor": float(header[4]), "exp_payoff": float(header[9]),
            "ops_gain_ask": n_ask_g, "ops_loss_ask": n_ask_l, "ops_gain_bid": n_bid_g, "ops_loss_bid": n_bid_l,
            "ops_total": n_ask + n_bid, "ops_gain_cons": int(header[17]), "ops_loss_cons": int(header[27]),
            "n_bars": int(header[0]), "n_ticks": int(header[7]), "quality": float(header[18]), "lev": lever,
            **params })

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def get_sink_prices(cls, symbols: list, since: Timestamp,
                        until: Timestamp = Timestamp.utcnow(),
                        step: DateOffset = DateOffset(months = 1),
                        tframe = Timedelta(minutes = 1)):

        since = Timestamp(since.strftime("%Y-%m-01"))
        until = Timestamp(until.strftime("%Y-%m-01"))
        month_range = date_range(since, until, freq = step)
        sinks = [DataFrame()]

        for symbol in sorted(symbols):
            args = {"symbol": symbol}
            for month in month_range:
                args["month"] = month.strftime("%y%m")
                path = cls.PATH_PRICES.format(**args)
                df = read_csv(path, names = cls.COLUMNS_TICKS)
                df["time"] = DatetimeIndex(df["time"]).floor(tframe)
                df = df.groupby("time").aggregate(cls.CANDLE_SAMPLER)
                df["symbol"] = symbol
                sinks.append(df)
        
        if not sinks: return None
        sinks = concat(objs = sinks, axis = "index")
        sinks = sinks.set_index("symbol", append = True)
        return sinks
    
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def process_as_order(cls, context: object, pending: dict):

        response = dict(reqd = False)
        symbol: str = context["symbol"]
        event: str = context["event"]
        sl: float = context["sl"]
        tp: float = context["tp"]
        iD: int = context["id"]
        n: int = context["n"]

        is_add = (event in cls.EVENTS_ORD)
        is_mod = (event in cls.EVENTS_MOD)
        is_rem = (event in [*cls.EVENTS_EN, "cancel"])
        
        if (iD in pending):
            pending[iD]["sl"], pending[iD]["tp"] = sl, tp
            pending[iD]["req"] = pending[iD]["req"] + is_mod
            if is_rem: response.update(**pending.pop(iD))
            if is_mod: response.update(reqd = True)
        
        elif is_add:
            entry, order = event.split(" ")
            pending[iD] = {"symbol": symbol,
                "entry": entry, "order": order, "lot": context["lot"],
                "time_s": context["time"], "price_s": context["price"],
                "sl": sl, "tp": tp, "req": 1, "row_s": n}
            response.update(**pending[iD], reqd = True)

        return response
    
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def process_as_trade(cls, context: object, active: dict, trade: dict = None):
        
        if not (trade is None):
            trade = trade.copy()
            trade.pop("reqd")
        else: trade = dict()

        response = dict(reqd = False)
        symbol: str = context["symbol"]
        event: str = context["event"]
        sl: float = context["sl"]
        tp: float = context["tp"]
        iD: int = context["id"]
        n: int = context["n"]

        is_add = (event in cls.EVENTS_EN)
        is_mod = (event in cls.EVENTS_MOD)
        is_rem = (event in cls.EVENTS_EX)

        if (iD in active):
            cls.update_worst_price(context, active[iD])
            active[iD]["sl"], active[iD]["tp"] = sl, tp
            active[iD]["req"] = active[iD]["req"] + is_mod
            if is_rem: response.update(active.pop(iD))
            if is_mod: response.update(reqd = True)

        elif is_add:
            if trade: active[iD] = {**trade, "time_e": context["time"],
                "price_e": context["price"], "price_w": context["price"],
                "sl": sl, "tp": tp, "row_e": n}
            else:
                active[iD] = {"row_s": n, "row_e": n, "symbol": symbol,
                    "entry": event, "order": "bbo", "lot": context["lot"],
                    "time_s": context["time"], "price_s": context["price"],
                    "time_e": context["time"], "price_e": context["price"],
                    "price_w": context["price"], "sl": sl, "tp": tp, "req": 1}
                
                response.update(**active[iD], reqd = True)

        return response
            
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def update_worst_price(cls, context: object, trade: dict):

        worst_bid = context["worst_bid"]
        worst_ask = context["worst_ask"]
        worst_price_prev = trade["price_w"]

        worst_price_dict = {"buy": (worst_bid, min), "sell": (worst_ask, max)}

        worst_price_last, func = worst_price_dict[trade["entry"]]
        
        trade["price_w"] = func(worst_price_prev, worst_price_last)
    
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def process_as_close(cls, context: object, closed: dict, trade: dict = None):
        
        if not (trade is None):
            trade = trade.copy()
            trade.pop("reqd")
        else: trade = dict()
        
        response = dict(reqd = False)
        event: str = context["event"]
        sl: float = context["sl"]
        tp: float = context["tp"]
        iD: int = context["id"]
        n: int = context["n"]
        
        if (event in cls.EVENTS_EX) and trade:

            closed[iD] = {**trade, "exit": event, "time_x": context["time"],
                "price_x": context["price"], "sl": sl, "tp": tp, "row_x": n}
        
        return response

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def run(self):

        timeline = self.events.index.unique()
        symbols = self.events["symbol"].unique()
        since, until = timeline[[0, -1]]
        sinks = self.get_sink_prices(symbols, since, until)
        self.specs = self.SYMBOL_SPECS.loc[symbols].copy()
        self.specs = self.specs[["point", "value"]]

        if (sinks is None):
            sinks = self.events[["price"] * 2]
            sinks.columns = ["worst_ask", "worst_bid"]
            sinks = sinks.groupby(["time", "symbol"])
            sinks: DataFrame = sinks.agg(self.CANDLE_SAMPLER)
            
        ############################################################################

        self.events = self.events.reset_index()
        orders, trades, closes = dict(), dict(), dict()
        requests = Series(0, index = timeline, name = "requests")
        deposit = self.events["balance"].iloc[0]
        
        for n, context in self.events.iterrows():

            context = {"n": n, **context}
            ts, symbol = context["time"], context["symbol"]
            context.update(**sinks.loc[(ts, symbol)])
            order = self.process_as_order(context, orders)
            trade = self.process_as_trade(context, trades, order)
            close = self.process_as_close(context, closes, trade)
            requests[ts] += order.get("reqd") or trade.get("reqd")

        self.trades = DataFrame.from_dict(closes, "index")
        self.trades = self.trades.rename_axis("id").sort_index()

        sign = self.trades["entry"].map(self.SIGN_ENTRY)
        coef = self.trades["symbol"].map(self.specs["value"] / self.specs["point"])
        self.trades["pts_x"] = self.trades.eval("price_x - price_e") * sign * coef
        self.trades["pts_w"] = self.trades.eval("price_w - price_e") * sign * coef
        self.trades["margin_u"] = self.trades["price_e"] * coef / self.lever
        self.trades = self.trades.reset_index()

        ############################################################################
        
        columns_index = ["sort", "event", "row", "time"]
        columns_vars = ["id", "lot", "pts_x", "pts_w", "margin_u"]
        contexts: DataFrame = concat(names = columns_index, objs = {
            (1, "signal"): self.trades.set_index(["row_s", "time_s"]),
            (2, "entry"): self.trades.set_index(["row_e", "time_e"]),
            (3, "exit"): self.trades.set_index(["row_x", "time_x"])})
        
        contexts = contexts[columns_vars].sort_index(level = ["row", "sort"])
        contexts = contexts.reset_index(drop = True, level = ["row", "sort"])
        contexts = contexts.reset_index("event")

        ############################################################################

        gfactors = ["core", *numpy.linspace(0, 1, 3)]
        buffer_eqfall = {gf: dict() for gf in gfactors}
        buffer_margin = {gf: dict() for gf in gfactors}
        buffer_profit = {gf: dict() for gf in gfactors}
        balances = Series(deposit, index = gfactors)

        columns_series = ["balance", "equity", "profit", "margin", "returns", "mglevel"]
        self.series = DataFrame(0.0, index = contexts.index, columns = gfactors)
        self.series = {column: self.series.copy() for column in columns_series}
        self.series = concat(self.series, axis = "columns", names = ["series", "gf"])
        self.series["balance"] = deposit
        
        for n, (ts, context) in enumerate(contexts.iterrows()):

            event, iD, lot = context[["event", "id", "lot"]]

            for gf in gfactors:

                if (event == "signal"):
                    
                    if isinstance(gf, float):
                        inc = balances[gf] / deposit
                        lot = 1 + gf * (inc - 1)

                    buffer_eqfall[gf][iD] = lot * context["pts_w"]
                    buffer_profit[gf][iD] = lot * context["pts_x"]
                    buffer_margin[gf][iD] = lot * context["margin_u"]
                    continue

                eqfall = buffer_eqfall[gf][iD]
                margin = buffer_margin[gf][iD]
                profit = buffer_profit[gf][iD]

                if (event == "entry"):

                    self.series[("equity", gf)].iloc[n] += eqfall
                    self.series[("margin", gf)].iloc[n] += margin

                elif (event == "exit"):
                    
                    balances[gf] += profit
                    self.series[("equity", gf)].iloc[n] -= eqfall
                    self.series[("margin", gf)].iloc[n] -= margin
                    self.series[("profit", gf)].iloc[n] += profit

        self.series["balance"] = self.series["profit"].cumsum() + self.series["balance"]
        self.series["equity"] = self.series["equity"].cumsum() + self.series["balance"]
        self.series["margin"] = self.series["margin"].cumsum()
        self.series["mglevel"] = self.series["equity"] / self.series["margin"]
        self.series["returns"] = self.series["profit"] / self.series["balance"]
        
        print("=" * 123, "Series:", "-" * 123, sep = "\n")
        print(         self.series, "=" * 123, sep = "\n")
        return self

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Tests ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

if (__name__ == "__main__"):

    reg = dict(id = "Test", mtver = 4)
    report = ReportReader.from_registry(reg)
        
    if False: 
        print(CHAR_PIPE_MID * 150, "header:", CHAR_PIPE_MID * 6, report.header, sep = "\n", end = "\n\n")
        print(CHAR_PIPE_MID * 150, "events:", CHAR_PIPE_MID * 6, report.events, sep = "\n", end = "\n\n")
        print(CHAR_PIPE_MID * 150, "trades:", CHAR_PIPE_MID * 6, report.trades, sep = "\n", end = "\n\n")
        print(CHAR_PIPE_MID * 150, "series:", CHAR_PIPE_MID * 6, report.series, sep = "\n", end = "\n\n")
        print(CHAR_PIPE_MID * 150, "stats:", CHAR_PIPE_MID * 6, report.stats, sep = "\n", end = "\n\n")