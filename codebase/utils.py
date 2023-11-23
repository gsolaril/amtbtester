import os, sys
from numpy import nan
from loguru import logger
from loguru._logger import Logger
from pandas import Series, DataFrame, merge
from typing import Callable
from pathlib import Path

PATH_LOCAL = __file__.rsplit(os.sep, 2)[0]

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Chars ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

CHAR_BLOCK_WHOLE = "█"
CHAR_BLOCK_CHESS_1 = "▚"
CHAR_BLOCK_CHESS_2 = "▞"
CHAR_BLOCK_UPPER_HALF = "▀"
CHAR_BLOCK_UPPER_EIGH = "▔"
CHAR_BLOCK_LOWER_HALF = "▄"
CHAR_BLOCK_LOWER_QUAR = "▂"
CHAR_BLOCK_LOWER_EIGH = "▁"
CHAR_PIPE_MID = "═"
CHAR_OVERLINE = "‾"
CHAR_WIDELINE = "⎯"
CHAR_BULLET = "⦿"

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#████████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Logger ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

class MyLogger(Logger):
    """
    Main purpose of this class is to just provide a wrapper for other more important classes that need logging.
    So let's say that "`MyClass`" needs internal logging. Then we can write "`@MyLogger.assign(logger)`" above the
    class' declaration ("`class MyClass: ...`") and such function will introduce a custom logger object for it to
    use internally. No need to specify "`logger`" as an argument in the "`MyClass`" constructor. The "`MyClass`" will
    only need some "`id`" attribute to be used in the entry printing, for oneself to recognise the entry's origin.
    """
    TPL_FORMAT = "[<level>{time:YYYY-MM-DD HH:mm:ss!UTC} | {extra[src]} @ {function}, L{line}</level>] {message}"
    TPL_FILENAME = "./logs/%s{time:MM-DD HH.mm}.log"

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def init(cls, _logger: Logger, src: str):
        """
        This function will return a "refreshed" logger object for the given class, whenever that class is at the
        top of the inheritance tree. Let's say that I've got the following inheritance sequence: "`A -> B -> C"`...
        "`A`" class is the top, so this function will run at the "`A`" class' level when the "`assign`" decorator is
        used. Classes "`B`" and "`C`" won't need to redefine the logger: they will just use the one from "`A`" while
        adding their own "`id`" to the "`src`" string.
        """
        # Empty logger sinks. We'll create new ones.
        _logger.remove(0)
        # Define the ".log" filenames to be used as 2nd sink.
        filename = cls.TPL_FILENAME % (src + " ")
        # This will enable logging to the terminal.
        _logger.add(sink = sys.stderr,
            format = cls.TPL_FORMAT, colorize = True)
        # This will enable logging to the "log" files.
        _logger.add(sink = filename, rotation = "10 MB",
            format = cls.TPL_FORMAT, colorize = False)

    #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    @classmethod
    def watch(cls, is_top: bool = False):
        """
        This will wrap any class which may need specific logging. So let's say I've got a class called "`MyClass`"
        which needs logging. Then I can write "`@MyLogger.assign`" above the class' declaration and such function
        will introduce a custom logger object for it to use internally. E.g.:
        ```
        @MyLogger.assign
        class MyClass:
            def __init__(self, id, *args, **kwargs):
                self.id, self.log = id, None
        ```
        This will automatically force "`self.log`" to receive "`logger`" after the initialization finishes. Logger
        will contain "`self.id`" in its "`src`" string to indicate where is each entry coming from, in the logger
        sinks.
        Arguments:
            - "`is_top`" (`bool`): Whether the class is at the top of the hierarchy tree. This will just reset the
            logger object and configure new sinks and properties as specified in the "`MyLogger.init`" function.
        """
        #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                # Instantiate the class. We'll return this.
                instance: object = func(*args, **kwargs)
                # If there's an "id" attribute, use that as "src"
                if hasattr(instance, "id"): src = instance.id
                # Else, use the class name itself for reference.
                else: src = instance.__class__.__name__
                # If the class is at the top of the hierarchy tree, initialize logger.
                if is_top: cls.init(_logger = logger, src = src)
                # Bind the "src" source string to the logger.
                instance.log = logger.bind(src = src)
                return instance
            # All of this happens after inits.
            return wrapper
        return decorator
        #▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Various ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

D2CONF_ERROR_MISSING = "Needed key fields not found."
D2CONF_ERROR_MISTYPE = "Wrong types for entered fields: %s"
MERGE_ARGS = dict(left_index = True, right_index = True)

#▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
def dict_to_config(template: DataFrame, **kwargs):

    template = template.copy()
    template["type"] = template["type"].map(eval)
    pars_mistype, pars_missing = dict(), dict()
    
    if not ("section" in template.columns): section = None
    else: section = template.pop("section").reset_index()
    template = template[["type", "include", "default"]]

    try: df = kwargs["config"]
    except: df = dict(**kwargs)
    
    for par, values in template.iterrows():
        dtype_def, include, default = values
        
        if not (par in df):
            if not (default is nan): df[par] = default
            elif include: pars_missing[par] = dtype_def
        else:
            dtype = type(df[par])
            df[par] = str(df[par])
            if (dtype != dtype_def): pars_mistype[par] = dtype
            if (dtype is bool): df[par] = str.lower(df[par])
                
    join = "\n".join
    df = Series(df).reset_index()
    df.columns = ["key", "config"]
    assert not pars_missing, D2CONF_ERROR_MISSING % pars_missing
    assert not pars_mistype, D2CONF_ERROR_MISTYPE % pars_mistype

    format_line = "{0[key]}={0[config]}".format
    df["line"] = df.agg(format_line, axis = "columns")
    if (section is None): return join(df["line"])

    df = merge(section, df, **MERGE_ARGS)
    df = df.groupby("section")["line"]
    df = df.agg(join).reset_index()
    
    format_section = "; {0[section]}\n{0[line]}\n".format
    df["block"] = df.agg(format_section, axis = "columns")
    return join(df["block"])

#▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
def read_set(filename: str):

    def try_get_type(string: str):
        try: t = type(eval(string))
        except: t = type(string)
        return t.__name__

    with open(filename) as file: config = file.read()
    config = DataFrame(config.split("\n"), columns = ["config"])
    has_eq = config["config"].str.contains("=")
    is_not_comment = ~ config["config"].str.contains("^;")
    is_not_empty = ~ config["config"].str.contains("^ *$")
    config = config.loc[is_not_comment & is_not_empty & has_eq]

    config["config"] = config["config"].str.split("=")
    config.index = config["config"].str[0].rename("key")
    config["config"] = config["config"].str[1 :].str.join("=")
    config["config"] = config["config"].replace("false", False)
    config["config"] = config["config"].replace("true", True)
    config["type"] = config["config"].map(try_get_type)
    return config
    
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
#█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████ Tests ███
#███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████

if (__name__ == "__main__"):
    
    df = read_set("Forex Fury v4.set")