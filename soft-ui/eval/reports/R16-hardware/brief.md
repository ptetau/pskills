# R16 · Sensor node: block diagram and alarm logic

`blocks.json` describes the hardware of a battery-powered door sensor node: its blocks
(power, MCU, sensors, radio), and the signals and buses between them, with the voltage
domain of each block. `logic.json` holds the alarm logic: the inputs, and a boolean
expression for each output.

Reader: the firmware engineer who joins the project. They need the block diagram with
the buses and power domains, and the full truth table of the alarm logic, with the input
cases that raise the alarm easy to see.
