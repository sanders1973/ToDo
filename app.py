from shiny import render, ui
from shiny.express import input

ui.panel_title("Marks Apps")
ui.input_slider("n", "N", 0, 100, 20)


@render.text
def txt():
    return f"n*2 is {input.n() * 2}"

