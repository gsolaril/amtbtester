import os, sys, json, numpy, re as regex, pyautogui as gui
from pynput import keyboard
from pandas import Series, DataFrame, Timestamp, Timedelta
from pandas import read_csv, concat, to_datetime as datetime
from IPython.display import display as _print
from time import time as timer, sleep
from sty import fg, ef, rs

instructions = {
    "EN": {
        "welcome": ["Welcome. Please, open your MetaTrader 4 platform.",
            "Be sure to follow the upcoming instructions <r1>carefully<r1>..."],
        "references": ["Some references from now onwards:",
            " -> <r1>red<r2> words represent stuff you must be aware of.",
            " -> <y1>yellow<y2> words represent keyboard-mouse buttons to be pressed.",
            " -> <c1>cyan<c2> words represent an icon or a graphical button.",
            "    <r1>Do not click them except<r2> you're being told to",
            " -> <p1>pink<p2> words represent certain areas or regions of the screen."
        ],
        "posCSV": ["A \"pos.csv\" file with screen positions has been found on the folder",
            "Do you want to use it and skip the position recording process? (1: yes, 2: no): "],
        "readyToGo": ["Open MT4 and press <y1>CTRL<y2> to begin."],
        "pos":
        {
            "posGraphClose": ["First, open any candle chart and maximize it.",
                "Then, point at the <c1>X<c2> button that would close the chart..."],
            "posGraphDrag": ["Close all of the opened candle charts before going on.",
                "We <r1>STRONGLY suggest<r2> you to drag and place this window (where I am writing at) towards the <p1>trading chart area<p2>.",
                "Resize this window until said area is covered. When you are ready, point at the lower left corner of this window..."],
            "posSymbolPanel": ["Good! Now open the <p1>Symbol Watchlist<p2> panel (the one which displays all pairs/symbols)",
                "Point as close to the center of this panel as possible..."],
            "posSymbolClear": ["Please, make sure this <p1>Symbol Watchist<p2> panel is <r1>ALWAYS<r2> visible.",
                "Now, <y1>right-click<y2> around said panel center. Then, point at the <c1>Hide all<c2> option..."],
            "posSymbolFirst": ["Now, please make sure that your watchlist only displays two symbols.",
                "Delete or hide all until 2 remain. Then, point at the one at the 2nd place/row..."],
            "posSymbolTester": ["It's time to open the <p1>Strategy Tester<p2> panel in MetaTrader 4.",
                "Make sure that you enlarge it enough so that every clickable object is visible.",
                "Locate the symbol selector draglist (below the EA selector) and point at it..."],
            "posTesterRun": ["Good job. Now point at the <c1>Start<c2> button in charge of executing a new backtest..."],
            "posPropsOpen": ["Now, point at the <c1>Expert properties<c2> button that opens the EA parameters' window..."],
            "posPropsClose": ["<y1>Click<y2> on said <c1>Expert properties<c2> button and open the EA config window.",
                "Locate the [OK] button that confirms the parameter settings, and point at it..."],
            "posPropsFirst": ["You must now locate the top most parameter row in the list.",
                "Doesn't really matter to which parameter is related to.",
                "Point at it below the leftmost <p1>Value<p2> column..."],
            "posPropsSecond": ["Now do exactly the same but pointing at the second row in the list..."],
            "posResultOpen": ["Great! Now close the EA config window by <y1>clicking<y2> on OK or X.",
                "Find the \"Result\" tab on the bottom of the <p1>Strategy Tester<p2> panel.",
                "Said tab can only be seen after one backtest.",
                "So if not visible, start a backtest and stop it right after.",
                "Once you are able to locate the <c1>Result<c2> label, point at it..."],
            "posResultPanel": ["Next, open the <c1>Result<c2> tab and point at the center of the panel..."],
            "posResultSave": ["Almost done! <y1>Right-click<y2> at said center of the panel to open the option list.",
                "Point at the <c1>Save as report<c2> option..."],
            "posSavePath": ["Finally, point at any place along the window's <p1>folder path field<p2>...",
                "(that's where the actual folder name is written, next to the arrow icons)"],
            "posSaveFile": ["Last but not least, point at the <c1>Save<c2> push button..."]
        },
        "guideline": [
            "Great! We may now proceed with the automatic backtesting process.",
            "Please, make <p1>MetaTrader 4 maximized and visible at all times<p2>.",
            "If you wish to pause/resume the process, hold/press <y1>CTRL + ALT + 0<y2> at any moment.",
            "To definitively <p1>stop<p2> the process at any time, just <p1>close<p2> this window after pause.",
            "Now press <y1>CTRL<y2> one last time to start the process. We'll do the rest!",
            "Nice! See you in a while!"
        ],
        "rest": ["New backtesting started. You can use the PC for a while...",
            "Just <r1>make sure<r2> you open back MetaTrader when backtest is around 80%."],
        "paging": ["<y1>(CTRL to continue)<y2>"],
        "instruction1": ["with your mouse pointer <r1>without clicking<r1>"],
        "instruction2": ["Then, press <y1>CTRL<y2> once"],
        "state": {
            "paused": ["Process paused. Press <y1>CTRL + ALT + 0<y2> to resume the task.",
                "Close this window if there's any need to terminate the process."],
            "resumed": ["Process resumed. Press <y1>CTRL + ALT + 0<y2> to pause again when needed."],
            "finished": ["Process finished. Goodbye! You can close this window..."]
        }
    },

    "ES": {
        "welcome": ["Bienvenido! Por favor, antes que nada, abrí tu plataforma de MetaTrader 4.",
            "A continuación, sigue las próximas instrucciones atentamente y <r1>con cuidado<r1>."],
        "references": ["Algunas referencias de ahora en mas:",
            " -> Palabras en <r1>rojo<r2> representan advertencias en la que debes prestar atención",
            " -> Palabras en <y1>amarillo<y2> representan botones del teclado/mouse que debes apretar.",
            " -> Palabras en <c1>celeste<c2> representan algún ícono o botón gráfico en la pantalla.",
            "    <r1>No hagas clic en ellos excepto<r2> que te lo indique.",
            " -> Palabras en <p1>rosa<p2> representan regiones o areas de la ventana/pantalla."
        ],
        "posCSV": {
            "found": [
                "El archivo <g1>\"pos.csv\"<g2> fue encontrado en la carpeta local, el cual normalmente graba el historial de posiciones.",
                "Deseas omitir el proceso de guardado de posiciones, y usar directamente el contenido del archivo? (1: si, 2: no)"],
            "error": ["Una o mas de las posiciones en \"pos.csv\" son <r1>inválidas<r2>.", "Verificar si no se salen de la pantalla."],
        },
        "readyToGo": ["Bien, una vez abierto MT4, presiona <y1>CTRL<y2> para comenzar."],
        "pos":
        {
            "posGraphClose": ["Comencemos! Primero, abrí una gráfica y maximizala.",
                "Luego ubicate sobre la <c1>X<c2> que cerraría dicha gráfica..."],
            "posGraphDrag": ["Cerrá todas las gráficas de MT4 que tengas abiertas.",
                "Es <r1>ALTAMENTE recomendable<r2> que en este momento arrastres esta ventana (adonde escribo) al <p1>area de gráficas<p2>.",
                "Agrandala/achicala hasta tapar dicha area. Cuando estes listo, ubicate en el extremo inferior izquierdo de esta misma ventana..."],
            "posSymbolPanel": ["Ahora abrí el panel de <p1>Observación de Mercado<p2> (con todos los pares e instrumentos).",
                "Ubicate cerca del centro de dicho panel..."],
            "posSymbolClear": ["Por favor, asegurate de que este panel <r1>SIEMPRE<r2> esté abierto.",
                "Ahora, hacé <y1>clic derecho<y2> en el centro de dicho panel. Apuntá a la opción de <c1>Ocultar todo<c2>..."],
            "posSymbolFirst": ["Ahora, ocultá todos los pares/instrumentos del panel excepto dos.",
                "Luego de ello, apunta al segundo de ellos..."],
            "posSymbolTester": ["Bien hecho! Llegó la hora de abrir el panel de <p1>Probador de Estrategias<p2> en MetaTrader 4.",
                "Asegurate de agrandarlo lo suficiente hacia arriba, de manera que todos los íconos o listas queden visibles.",
                "Ubica al listado selector de instrumentos, y señalalo..."],
            "posTesterRun": ["Apunta ahora al botón de <c1>Iniciar<c2>, el cual comenzaría un nuevo backtest..."],
            "posPropsOpen": ["Apunta ahora al botón de <c1>Propiedades del experto<c2> que abriría la ventana de parámetros del EA..."],
            "posPropsClose": ["Hacé <y1>clic<y2> en el botón de <c1>Propiedades del experto<c2> para abrir la ventana de parámetros del EA.",
                "Ves el botón de <c1>OK<c2> que confirma y cierra la ventana de parámetros? <r1>Sin hacer clic<r1>, apunta hacia él..."],
            "posPropsFirst": ["Perfecto! Ahora, ubicá la fila mas álta dentro del listado de parámetros configurables.",
                "Sin importar cual es su valor o contenido, señalala dicha fila estando justo debajo de la colúmna <p1>\"Valor\"<p2>..."],
            "posPropsSecond": ["Bien, ahora desplazate verticalmente señalando la fila de abajo (la 2da)..."],
            "posResultOpen": ["Vas muy bien! Podes cerrar esta ventana de parámetros con <c1>OK<c2>, <c1>X<c2> o cualquier botón.",
                "En el borde inferior izquierdo de MetaTrader, deberías ver una pestaña llamada <c1>Resultados<c2>.",
                "Si no se encuentra presente, es porque jamás hiciste un backtest. Hacé uno y cancelalo rápido.",
                "Una vez que dicha pestaña está presente, ubicate sobre ella..."],
            "posResultPanel": ["Ahora, hacé <y1>clic<y2> en dicha pestaña de <c1>Resultados<c2>. Señalá al centro de su panel..."],
            "posResultSave": ["Luego, hacé <y1>clic derecho<y2> en este último punto para abrir una lista de opciones.",
                "Apuntá a la opción de <c1>Guardar como informe<c2>..."],
            "posSavePath": ["Casi terminamos! Hacé <y1>clic<y2> en <c1>Guardar como informe<c2>. Se te abrirá la ventana de una carpeta.",
                "Dentro de ella, apuntá a la <p1>barra de direcciones<p2>, en la parte superior de la ventana...",
                "(Es adonde está escrito el nombre de la carpeta, al lado de los íconos de <p1>ir atrás/adelante<p2>)"],
            "posSaveFile": ["Hecho! Por último, dentro de esta misma ventana, señala el botón de <c1>Guardar<c2> abajo a la derecha..."]
        },
        "guideline": [
            "A continuación comenzaremos con el proceso de backtesting automático.",
            "Por favor asegurate de que esté <p1>MetaTrader 4 maximizado y visible en todo momento<p2>!",
            "Si necesitas pausar/reanudar el proceso, presiona <y1>CTRL + ALT + 0<y2> en cualquier momento.",
            "Para <p1>detener<p2> el proceso de manera definitiva, solo <p1>cierra<p2> esta ventana después de pausar.",
            "Presiona <y1>CTRL<y2> una última vez para iniciar. Nosotros haremos el resto!",
            "Bien! Nos vemos en un rato! :)"
        ],
        "active": ["Nuevo backtest comenzado. Datos:", "<g1>%s<g2>", "(Puedes usar tu PC por un rato...",
            "Solo <r1>asegurate de volver a abrir MetaTrader<r2> cuando el proceso se completó en un 80%.)"],
        "paging": ["<y1>(CTRL para continuar)<y2>"],
        "mouse": ["con el puntero de tu mouse, <r1>sin hacer click<r1>."],
        "press": ["Luego, presiona <y1>CTRL<y2> una sola vez."],
        "state": {
            "paused": ["Proceso en pausa. Presiona <y1>CTRL + ALT<y2> para retomar la tarea.",
                "Cierra esta ventana si deseas finalizar el proceso de manera definitiva"],
            "resumed": ["Proceso reanudado. Presiona <y1>CTRL + ALT<y2> para volver a pausar."],
            "finished": ["Proceso terminado. Adiós! Podes cerrar esta ventana con total tranquilidad..."]
        }
    }
}

#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#
#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#
#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#

class AutoMQT:

    corrections = {"/": "-", ":": "."}
    columns = ["page", "cell", "type"]

    #===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#

    colors = {
        "r": (255, 120, 120),
        "p": (255, 192, 203),
        "y": (255, 255,   0),
        "c": (  0, 255, 255),
        "g": (100, 255, 100), }

    def print(cls, string: list[str]):

        for char, color in cls.colors.items():

            string = "\n".join(string)
            L, R = f"<{char}1>", f"<{char}2>"
            regex_color = regex.compile(L + ".*?" + R)
            
            for item in regex_color.findall(string):
                phrase = item.replace(L, "").replace(R, "")
                phrase = fg(*color) + ef.b + phrase + rs.all
                string = "\n" + string.replace(item, phrase)
        
        print(string)
    
    #===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#

    def __init__(self, waitTest: float = 2.5, waitSave: float = 0.5, waitInput: float = 0.5):
        
        self.print("Seleccionar idioma / Choose language...")
        language = input("1: español / spanish, 2: ingles / english: ")
        language = "EN "if (int(language) == 2) else "ES"
        self.instructions = instructions[language]

        self.xmax, self.ymax = gui.size()
        self.active = True

        self.pos = self.symbol = self.test = self.config = self.format = None
        self.waitTest, self.waitSave, self.waitInput = waitTest, waitSave, waitInput

        self.path = os.getcwd()
        self.print(self.instructions["welcome"])
        self.print(self.instructions["references"])
        posCSV = self.instructions["posCSV"]["found"]
        if ("pos.csv" in os.listdir(self.path)):
            self.print([posCSV[0]])
            if (input(posCSV[1]) == "1"):
                if (self.pos is None): self.locateCSV()
        
        self.path += "\\" + Timestamp.now().strftime("%Y-%m-%d %H.%M")
        os.mkdir(self.path)

        if (self.pos == None):
            self.checkpoint(self.instructions["readyToGo"])
            self.locate()
            paging = self.instructions["paging"][0]
            for line in self.instructions["guideline"]:
                self.checkpoint([line + " " + paging])

        self.run()

    #===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#

    def checkpoint(self, string: list[str]):

        self.pressed = False
        self.print(string)
        def listen(key): self.pressed = (key == keyboard.Key.ctrl_l)
        with keyboard.Listener(on_press = listen) as listener:
            while not self.pressed: sleep(0.5)
        self.pressed = False
        listener.join()

    def locate(self):

        pos = self.instructions["pos"]
        insMouse = self.instructions["mouse"]
        insPress = self.instructions["press"]
        step_temp = "[%s/%d]" % ("%02d", len(pos))
        self.pos = DataFrame(columns = ["x", "y"],
            index = self.instructions["pos"].keys())

        for step, (id, line) in enumerate(pos.items()):
            line[-1] = line[-1].replace("...", insMouse)
            self.checkpoint([step_temp % step] + line + insPress)
            self.pos.loc[id] = gui.position()

        self.pos.to_csv("pos.csv", index_col = 0)
        point = lambda p: gui.Point(p["x"], p["y"])
        self.pos["p"] = self.pos.apply(point)

    def locateCSV(self):

        error = self.instructions["posCSV"]["error"]
        pos = read_csv("pos.csv", names = ["x", "y"], index_col = 0)
        if (self.pos["x"] <= 0).any():
            self.print(error); self.pos = None; return
        if (self.pos["x"] >= self.xmax).any():
            self.print(error); self.pos = None; return
        if (self.pos["y"] <= 0).any():
            self.print(error); self.pos = None; return
        if (self.pos["y"] >= self.ymax).any():
            self.print(error); self.pos = None; return

        self.pos = pos
        point = lambda p: gui.Point(p["x"], p["y"])
        self.pos["p"] = self.pos.apply(point)

    #===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#

    def list_symbols(self):

        try:
            with open("symbols.csv", "rt") as CSV:
                symbols = CSV.read().split("\n")
                self.symbol = symbols.pop(0)
                assert self.symbol.isalnum()
            with open("symbols.csv", "wt") as CSV:
                CSV.writelines("\n".join(symbols))
                OK = True
        except: OK = False
        with open("tests.csv", "rt") as CSV: tests = CSV.read()
        with open("temp.csv", "wt") as CSV: CSV.write(tests)
        self.print(f"Actual symbol: \"{self.symbol}\", pending: {symbols}")
        return OK

    def list_configs(self):

        try:
            with open("configs.csv", "rt") as CSV:
                tests = CSV.read().split("\n")
                self.test = tests.pop(0).split(",")
                types = zip(self.test, self.config["type"])
                self.test = [tp(value) for (value, tp) in types if value != ""]
                self.test = Series(self.test, index = self.config.index)
            with open("configs.csv", "wt") as CSV:
                CSV.writelines("\n".join(tests))
                OK = True
        except: OK = False
        return OK

    #===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#

    def generate(self):

        with open("generator.json", "r") as file:
            generator = json.load(file)

        symbols, meshes, params = generator.values()
        params = DataFrame(params).transpose()
        template = DataFrame(columns = params.index)
        backtests = template.copy()
        for mesh in meshes:
            values = params.loc[mesh, "values"]
            values = numpy.meshgrid(*values)
            for n, dim in enumerate(values):
                values[n] = dim.reshape(-1)
            values = numpy.stack(values)
            backtests_mesh = template.copy()
            backtests_mesh[mesh] = values.T
            fixed = list(set(params.index).difference(mesh))
            backtests_mesh[fixed] = params.loc[fixed, "def"]
            backtests = concat((backtests, backtests_mesh))

        for parameter in backtests.columns:
            values = params.at[parameter, "values"]
            backtests_mesh = template.copy()
            backtests_mesh[parameter] = values
            fixed = list(backtests.columns)
            fixed.remove(parameter)
            backtests_mesh[fixed] = params.loc[fixed, "def"]
            backtests = concat((backtests, backtests_mesh))

        backtests = backtests.drop_duplicates()
        backtests = backtests.sort_values(list(backtests.columns))
        backtests = backtests.reset_index(drop = True)
        backtests.to_csv("configs.csv", index = False)
        with open("symbols.csv", "wt") as CSV:
            CSV.writelines("\n".join(symbols))

    #===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#

    def run(self):

        def listen(self, key: keyboard.Key):

            if (str(key) == r"'\x10'"): # ctrl + p

                insPaused = self.instructions["state"]["paused"]
                insResume = self.instructions["state"]["resumed"]
                insState = insResume if self.paused else insPaused
                self.print([f"Key: <{key}>"] + insState)
                self.paused = not self.paused
                return False
                
            if (str(key) == r"'\x12'"): # ctrl + r

                return False

            if (str(key) == r"'\x1a'"): # ctrl + z

                return False

        #===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#

        with keyboard.Listener(on_press = listen) as listener:

            while True:

                while self.paused: sleep(0.5); pass
                if not self.list_symbols(): sleep(0.5); break
                self.test_symbol()

                while True:
                    while self.paused: sleep(0.5); pass
                    if not self.list_configs(): sleep(0.5); break
                    self.test_config()

                    while True:
                        sleep(2)
                        while self.paused: sleep(0.5); pass
                        if gui.locateOnScreen("started.png"): sleep(0.5); break

                    now = Timestamp.now()
                    verbose = self.instructions["active"].copy()
                    verbose[0] = verbose[0] % now.strftime("%X")
                    verbose[1] = verbose[1] % str(self.test)
                    self.print(verbose)

                    while True:
                        sleep(2)
                        while self.paused: sleep(0.5); pass
                        if gui.locateOnScreen("finished.png"): sleep(0.5); break
                        
                    while self.paused: sleep(0.5); pass
                    self.save_results()
            
        listener.join()

    #===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#===#                

    def setup(self):

        width = len(self.columns)  ;  generator = None  ;  self.format = ""
        self.config = read_csv("setup.csv", index_col = 0, header = None)
        if (self.config.shape[1] > width):
            generator = self.config.iloc[:, width :]
        self.config = self.config.iloc[:, : width]
        self.config.columns = self.columns
        self.config["type"] = self.config["type"].apply(func = eval)
        for key in self.config.index: self.format += f", {key} = %s"
        if isinstance(generator, type(None)): return
        generator = generator.to_dict().values()
        generator = map(Series, generator)
        self.generate(*generator)

    @staticmethod
    def generate(meshed: Series, scope: Series):

        scope = scope.apply(eval) ; index = scope.index
        tests = DataFrame(columns = scope.index)
        default = scope.apply(lambda array: array[0])
        for label, values in scope.to_dict().items():
            for value in values:
                test = default.copy()
                test.at[label] = value
                tests.at[len(tests)] = test
        mesh = numpy.meshgrid(*scope.loc[meshed])
        mesh = [axis.reshape(-1) for axis in mesh]
        size = len(mesh[0])
        mesh = zip(index, mesh)
        for n in range(size):
            test = default.copy()
            for label, axis in mesh:
                test.at[label] = axis[n]
            tests.at[len(tests)] = test
        tests.drop_duplicates(inplace = True)
        tests.reset_index(inplace = True, drop = True)
        tests.iloc[0:].to_csv("tests.csv", index = False, header = False)

    def test_symbol(self):
        
        gui.moveTo(self.posSymbolPanel)  ;  gui.rightClick()
        gui.moveTo(self.posSymbolClear)  ;  gui.leftClick()
        gui.moveTo(self.posSymbolPanel)
        if not self.active: return
        gui.doubleClick()
        gui.write(self.symbol)
        gui.press("enter")
        sleep(self.waitInput)
        x, y = self.posSymbolTester
        gui.moveTo(self.posSymbolFirst)
        if not self.active: return
        gui.dragTo(x, y, self.waitInput, button = "left")
        if not self.active: return

    def test_config(self):

        gui.moveTo(self.posPropsOpen)  ;  gui.leftClick()  ;  sleep(1)
        gui.moveTo(self.posPropsFirst) ;  gui.leftClick()
        if not self.active: return
        while self.paused: pass
        gui.press("home")
        x0 = self.posPropsFirst.x
        y0 = self.posPropsFirst.y
        y1 = self.posPropsSecond.y
        page = 0
        sleep(1)
        test = self.test.to_dict()
        for label, value in test.items():
            if not self.active: return
            while self.paused: pass
            config = self.config.loc[label, :]
            diff, page = config["page"] - page, config["page"]
            for press in range(diff + 1): gui.press("pgdn")
            gui.moveTo(x0, y0 + (y1 - y0) * config["cell"])
            if not self.active: return
            while self.paused: pass
            if config["type"] in [int, float, str]:
                gui.doubleClick() ; gui.write(str(value))
            if (config["type"] == list):
                for press in range(value): gui.press("down")
            gui.press("enter")
            sleep(self.waitInput)
        if not self.active: return
        while self.paused: pass
        gui.moveTo(self.posPropsClose) 
        gui.leftClick()
        sleep(self.waitInput)
        gui.moveTo(self.posTesterRun)
        if not self.active: return
        while self.paused: pass
        gui.leftClick()
        sleep(0.25) ; gui.keyDown("alt") ; gui.keyDown("tab")
        sleep(0.25) ; gui.keyUp("alt")   ; gui.keyUp("tab")
        sleep(1)

    def save_results(self):

        sleep(self.waitSave)
        fileName = self.symbol + self.format % (*self.test,)
        for wrong, right in self.corrections.items():
            fileName = fileName.replace(wrong, right)
        if not self.active: return
        while self.paused: pass
        gui.moveTo(self.posResultOpen)  ; gui.leftClick()  ; sleep(0.5)
        gui.moveTo(self.posResultPanel) ; gui.rightClick() ; sleep(0.5)
        gui.moveTo(self.posResultSave)  ; gui.leftClick()  ; sleep(2.0)
        gui.write(fileName)
        if not self.active: return
        while self.paused: pass
        gui.moveTo(self.posSavePath)          ; gui.rightClick() ; sleep(0.5)
        [gui.press("down") for _ in range(3)] ; sleep(0.5) ; gui.press("enter")
        if not self.active: return
        while self.paused: pass
        gui.write(self.path)          ;  gui.press("enter")  ; sleep(0.5)
        gui.moveTo(self.posSaveFile)  ;  gui.leftClick()     ; sleep(3)
        if not self.active: return
        while self.paused: pass
        gui.press("left")    ;   sleep(0.5)
        if not self.active: return
        while self.paused: pass
        gui.press("enter")   ;   sleep(5)
        if not self.active: return
        while self.paused: pass
        gui.leftClick()
        sleep(0.5) ; gui.keyDown("ctrl") ; gui.keyDown("w") 
        sleep(0.5) ; gui.keyUp("ctrl")   ; gui.keyUp("w")
        sleep(0.5) ; gui.keyDown("alt")  ; gui.keyDown("f4")
        sleep(0.5) ; gui.keyUp("alt")    ; gui.keyUp("f4")
        if not self.active: return
        while self.paused: pass
        x, y = self.posResultOpen      ;  posSettings = gui.Point(x // 2, y)
        gui.moveTo(posSettings)  ;  gui.leftClick()
        sleep(self.waitSave)

if (__name__ == "__main__"): AutoMQT()