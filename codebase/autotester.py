import os, sys, json, re as regex
from pandas import DataFrame, concat

sys.path.append("./")
from codebase.utils import *
from codebase.connector import Connector

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Main class ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

#▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
class Autotester:

    ERROR_EA_EXT = "Unsupported file extension: \"%s\""
    ERROR_EA_NAME = "Unidentified EA name: \"%s\""
    PATH_CSV_PROCESSES = "./auth/processes.csv"

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def __init__(self, EAs: list):

        self.EAs = DataFrame(EAs, columns = ["mtver"])
        self.EAs["file_ea"] = self.EAs["mtver"].str.split(".")
        self.EAs.index = self.EAs["file_ea"].str[0].rename("name")
        self.EAs["mtver"] = self.EAs["file_ea"].str[-1].str[-1]
        self.EAs["file_ea"] = self.EAs["file_ea"].str.join(".")
        self.EAs["file_set"] = self.EAs.index + ".set"
        self.EAs["file_ini"] = self.EAs.index + ".ini"
        self.EAs["mtver"] = self.EAs["mtver"].astype(int)
        self.EAs["tests"], self.EAs["prog"] = 0, 0.0
        self.EAs["optimized"] = False

        self.EAs.to_csv(self.PATH_CSV_PROCESSES)
        self.conn, self.temp, self.proc = dict(), dict(), dict()

        for name_ea in self.EAs.index:
            file_ea = self.EAs.loc[name_ea, "file_ea"]
            ext = os.path.split(file_ea)[-1].split(".")[-1]
            assert (ext in ["ex4", "ex5"]), self.ERROR_EA_EXT % file_ea
            self.temp[name_ea] = read_set(name_ea + ".set")
            self.conn[name_ea] = Connector(id = name_ea)
            
        self.temp = concat(self.temp, names = ["name", "key"])
    
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def set_config(self, name_ea: str, **kwargs):
        
        assert (name_ea in self.EAs.index), self.ERROR_EA_NAME % name_ea
        return self.conn[name_ea].cmd_config(name_ea + ".ini", **kwargs)

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def set_backtest(self, name_ea: str, **kwargs):

        assert (name_ea in self.EAs.index), self.ERROR_EA_NAME % name_ea
        df = self.temp.loc[name_ea].rename(columns = {"config": "default"})
        df["include"] = True

        filename = name_ea + ".set"
        config_str = dict_to_config(df, **kwargs)
        with open(filename, "w") as file: file.write(config_str)
        return os.path.abspath(filename)

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Tests ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

if (__name__ == "__main__"):

    ea = "MACrossover"
    auto = Autotester([ea + ".ex4"])
    path_report = PATH_LOCAL + "/report.html"

    print(backtest := auto.set_backtest(ea,
        boolean = True,
        lbLong = 12,
        lbShort = 8,
        lotInit = 0.01000000,
        gFactor = 0.00000000,
        xStLoss = 0.00010000,
    ))
    
    print(filepath := auto.set_config(ea,
        Login = 1040225920,
        Password = "XYJSZ16",
        Server = "FTMO-Demo2",
        TestExpert = ea + ".ex4",
        TestExpertParameters = ea + ".set",
        TestSymbol = "EURUSD",
        TestReport = f"../Common/{ea}.html" #os.path.normpath(path_report),
    ))

    auto.conn[ea].run(mtid = "FTDT4_US1", filepath = filepath,
        callback = lambda R: print("registry:", R, sep = "\n"))