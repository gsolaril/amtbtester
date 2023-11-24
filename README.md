<center><h4><b><u>Auto MetaTrader backtester</u></b></h4></center>

Purpose of this project is to establish a remote control of the infamous "Strategy Tester" utility through command line and using "`.ini`" files during MetaTrader startup. Backtest subprocess will run and store the resulting HTML report in the Common folder. Then this tool will fetch such report and choose the EA parameter values ("`.set`") for the next backtest, hopefully closer to optimal configuration.

The EA parameter choice is intended to be made based on different predictive algorithms ("$pred$" below) in "`models`" folder. These will use the report content and results on prior choices as input. The process will stop the backtesting cycle after a certain preselected "performance function" ("$perf$" below) proves to have reached a maximum.

<u>So basically, the idea is</u>:

> While "$r_{n} - r_{n-1} > \Delta r$":
> <br> &emsp;...recalculate parameters: "$\bold{X_{n+1}} = \text{pred}(\bold{X_n}, \bold{R_{n}})$"
> <br> &emsp;&emsp; (where "$\bold{R_{n}}=[r_1, r_2, ..., r_n]$")
> <br> &emsp;...backtest the EA with such new parameters "$\bold{X_{n+1}}$".
> <br> &emsp;...parse resulting HTML report and get metrics "$\bold{M_{n+1}}$".
> <br> &emsp;...recalculate performance: "$r_{n+1}=\text{perf}(\bold{M_{n+1}})$"

<u>Basic diagram</u> would be the following:

<center><img src = "./Schematic - cell.jpg" width = "80%"></center></img>