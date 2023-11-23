import os, sys, subprocess, uuid, time
from subprocess import CompletedProcess
from pandas import Timestamp, Series, DataFrame, read_csv, merge
from concurrent.futures import Future, ThreadPoolExecutor, wait

sys.path.append("./")
from codebase.utils import *

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#███████████████████████████████████████████████████████████████████████████████████████████████████████████ Commander class ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

#@MyLogger.watch
#▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
class CMD(ThreadPoolExecutor):

    vb_PROC_START = "{key} - \"{cmd}\""
    vb_PROC_FINISH = vb_PROC_START + ", retcode: {retcode}"
    vb_PROC_ERROR = vb_PROC_FINISH + ", error: \n{error}\n"
    
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def __init__(self, id: str, *args, **kwargs):
        """
        Base class for interaction with command line processes. Inherits the "thread-pool" structure from Concurrent Futures"
        library. This class is to be used inside the actual interface subclasses in production, and as standalone in tests.
        \nInputs:
            - "`id`" (`str`): Unique identifier for the instance. Will be used for logging.
            - "`*args, **kwargs`": Positional and keyword-based arguments passed to parent class ("`ThreadPoolExecutor`").
        """
        self.id: str = id
        self.log: Logger = None
        super().__init__(thread_name_prefix = id, *args, **kwargs)
        self.processes = dict()
    
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def process_complete(self, future: Future, key: str, callback: Callable = None):
        """
        Internal callback meant to record the outcomes of the subprocesses in "`processes`". When the subprocess finishes, this
        will store the terminal output, the return-code and the finish timestamp. Not to be used as a standalone function. 
        """
        result: CompletedProcess = future.result()

        reg = self.processes[key]
        reg["stdout"] = result.stdout
        reg["stderr"] = result.stderr
        reg["end"] = Timestamp.utcnow()
        reg["retcode"] = result.returncode

        if not result.returncode: self.log.debug(self.vb_PROC_FINISH.format(**reg))
        else: self.log.error(self.vb_PROC_ERROR.format(**reg, error = result.stderr))

        if callback: callback(reg)
        
    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def process_starting(self, cmd: str, **kwargs):
        """
        Attach a command-line operation to the thread pool. Returns the subprocess key (UUID) so that the result can be
        retrieved from the "`processes`" dict. This function is intended to take care of everything related to inputs,
        outputs and logging of all subprocesses.
        \nInputs:
            \n* "`cmd`" (`str`): Command to be executed.
            \n* "`callback`" (`function`, optional): External callback. Any kind of function that shall be
                executed when the subprocess ends.
            \n* "`**kwargs`": Any extra or custom metadata that needs to be added to the "`processes`" dict.
        \nOutput:
            \n* "`key`" (`str`): Unique identifier for the subprocess. This can be used for later retrieval
                of the result.
        \nExample:
        ```
        instance = CMD("ABCD")                      # Instantiate the CMD.
        cmd = "python -c 'print('hello world')'"    # Will use a simple "hello world" print.
        key = cmd.run(cmd = cmd)                    # Run the command in the thread pool.
        print("Results:", instance.results[key])    # Print the results
        ```
        \nResult:
        ```
        >> {"key": {same key given above}, "start": YYYY-MM-DD HH:MM:SS.fff,
            "end": YYYY-MM-DD HH:MM:SS.fff, "id": ABCD, "stdout": hello world, 
            "cmd": {same cmd given above}, "stderr": "", "retcode": 0}
        ```
        """
        # If there's a timeout, retrieve it.
        timeout = kwargs.pop("timeout", None)
        cb_ext = kwargs.pop("callback", None)
        # Generate unique key for subprocess.
        key = uuid.uuid4().__str__().upper()

        reg = dict() # New subprocess entry.
        reg.update({"key": key, "start": Timestamp.utcnow(),
            "end": None, "id": self.id, "cmd": cmd, **kwargs})
        
        # Print that the subprocess has started.
        self.log.debug(self.vb_PROC_START.format(**reg))
        # "PIPE" enables the return of terminal verbose as string.
        subArgs = {"args": cmd, "timeout": timeout, "text": True,
            "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
        # Start the subprocess in a separate thread. Keep the "future".
        process: Future = self.submit(subprocess.run, **subArgs)
        callback = lambda future: self.process_complete(future, key, cb_ext)
        # Add the "process_complete" method as callback. Once finished,
        # the subprocess will run this callback automatically.
        process.add_done_callback(callback)

        # Store entry with future in the "results" dict.
        self.processes[key] = reg 
        # Return the unique key for further processing.
        return key 
    
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#███████████████████████████████████████████████████████████████████████████████████████████████████████████ Connector class ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

#@MyLogger.watch(is_top = True)
#▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
class Connector(CMD):

    PATH_TERMINAL = os.path.expanduser("~") + "/AppData/Roaming/MetaQuotes/Terminal/"
    PATH_TERMINAL_COMMON = (PATH_TERMINAL := os.path.normpath(PATH_TERMINAL)) + "\\Common\\"
    PATH_CSV_ACCOUNTS, PATH_CSV_KEYWORDS = "./auth/accounts.csv", "./auth/keywords.csv"
    ERROR_NEEDED_KEYS = "Needed key fields not found. Review \"%s\"" % PATH_CSV_KEYWORDS
    ERROR_WRONG_TYPES = "Wrong types for entered fields. Review \"%s\"" % PATH_CSV_KEYWORDS

    TABLE_KEYWORDS = read_csv(PATH_CSV_KEYWORDS, index_col = ["key"])
    REGEX_TEST_ACCOUNTS = "T\w_"
    FORMAT_CONFIG_LINE = "{0[key]}={0[config]}".format
    FORMAT_CONFIG_SECTION = "; {0[section]}\n{0[ini_line]}".format
    FORMAT_CMD_STARTUP = "{mtpath}\\{exec} /config:{filepath}".format
    FORMAT_CMD_STARTUP = "\"{mtpath}\\{exec}\" \"{filepath}\"".format
    MAPPER_MTVER = {4: "terminal.exe", 5: "terminal64.exe"}

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def __init__(self, accounts: DataFrame = None, *args, **kwargs):
        """
        This class extends CMD to handle MetaTrader instances through command-line instructions.
        """
        self.accounts = accounts
        self.id = kwargs.pop("id")
        if (self.accounts is None):
            path = self.PATH_CSV_ACCOUNTS
            regex = self.REGEX_TEST_ACCOUNTS
            df = read_csv(path).set_index("id")
            is_test = df.index.str.contains(regex)
            self.accounts = df.loc[is_test]

        super().__init__(id = self.id, *args, **kwargs)

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def cmd_config(self, filename: str, **kwargs):
        """
        Set the configuration file of the MetaTrader instance.
        """
        config_str = dict_to_config(self.TABLE_KEYWORDS, **kwargs)
        with open(filename, "w") as file: file.write(config_str)
        return os.path.abspath(filename)

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    def run(self, mtid: str, filepath: str, **kwargs):
        """
        Run the configuration file of the MetaTrader instance.
        """
        conn_to = self.accounts.loc[mtid].copy()
        conn_to["filepath"] = os.path.normpath(filepath)
        conn_to["exec"] = self.MAPPER_MTVER[conn_to["mtver"]]

        cmd = self.FORMAT_CMD_STARTUP(**conn_to)
        uid = self.process_starting(cmd, **conn_to, **kwargs)

        return uid

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Tests ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

if (__name__ == "__main__"):
    
    #cmd: CMD = CMD("ABCD")
    #cmd.process_starting("python test.py")
    #print("results:")
    #print(cmd.results)

    conn = Connector(id = "ABCD")
    today = Timestamp.now().strftime("%Y.%m.%d")

    #conn.log.debug("Accounts:\n%s" % conn.accounts)
    kwargs = dict(
        Login = 1040225920,
        Password = "XYJSZ16",
        Server = "FTMO-Demo2",
        TestExpert = "MACrossover.ex4",
        TestExpertParameters = "MACrossover.set",
        TestSymbol = "EURUSD",
        TestToDate = today,
    )
    filepath = conn.cmd_config(filename = "MACrossover.ini", **kwargs)
    uid = conn.run(mtid = "FTDT4_US1", filepath = filepath)
    print("\nCan do other stuff in the meantime...")
    verb = "\r...like displaying the current time:"

    for i in range(20):
        clock = Timestamp.now().strftime(" %X")
        print(verb, clock, end = ""), time.sleep(1)
    
    proc = Series(conn.processes[uid])
    print(""), print(""), print(proc)
