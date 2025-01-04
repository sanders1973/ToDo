from shiny import App, render, ui

app_ui = ui.page_fluid(
    ui.card(
        ui.input_text(
            "name",
            "Username",
            value="",
            autocomplete="username"  # Hint to browser this is a username field
        ),
        ui.input_password(  # Simple password input
            "password",
            "Password",
            value=""
        ),
        ui.input_action_button("submit", "Submit"),
        ui.output_text("result")
    )
)

def server(input, output, session):
    @output
    @render.text
    def result():
        if input.submit():
            return f"Submitted: Username = {input.name()}"
        return ""

app = App(app_ui, server)
