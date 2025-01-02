import shiny
from shiny import reactive
from shiny import ui, render, App
import pandas as pd

# Initialize the data frame to store the to-do items
todo_df = pd.DataFrame(columns=["Item", "Description"])

# Define the UI
app_ui = ui.page_fluid(
    ui.row(
        ui.column(
            4,
            ui.input_text("new_item", "Add Item", ""),
            ui.input_text_area("description", "Description", ""),
            ui.input_action_button("add", "Add"),
            ui.output_data_frame("todo_list"),
            ui.input_select("select_item", "Select Item", choices=[]),
            ui.input_action_button("delete", "Delete"),
            ui.input_action_button("move_up", "Move Up"),
            ui.input_action_button("move_down", "Move Down"),
        ),
        ui.column(
            8,
            ui.output_text("todo_markdown"),
        )
    )
)

# Define the server logic
def server(input, output, session):

    # Function to update the select input choices
    def update_select_choices():
        session.send_input_message("select_item", choices=todo_df["Item"].tolist())

    @reactive.effect
    def add_item():
        if input.add():
            new_item = input.new_item()
            description = input.description()
            if new_item and description:
                global todo_df
                todo_df = todo_df.append({"Item": new_item, "Description": description}, ignore_index=True)
                update_select_choices()
                session.reset()

    @reactive.effect
    def delete_item():
        if input.delete():
            selected_item = input.select_item()
            global todo_df
            todo_df = todo_df[todo_df["Item"] != selected_item]
            update_select_choices()
            session.reset()

    """
    @reactive.effect
    def move_item(direction):
        if (direction == "up" and input.move_up()) or (direction == "down" and input.move_down()):
            selected_item = input.select_item()
            index = todo_df.index[todo_df["Item"] == selected_item].tolist()
            if index:
                index = index[0]
                if direction == "up" and index > 0:
                    todo_df.iloc[index], todo_df.iloc[index-1] = todo_df.iloc[index-1].copy(), todo_df.iloc[index].copy()
                elif direction == "down" and index < len(todo_df) - 1:
                    todo_df.iloc[index], todo_df.iloc[index+1] = todo_df.iloc[index+1].copy(), todo_df.iloc[index].copy()
                session.reset()

             

    @render.data_frame
    def render_todo_list():
        render.DataGrid(todo_df)
       ## output.todo_markdown(todo_df.to_markdown(index=False))

        """  

# Create the app
app = App(app_ui, server)

if __name__ == "__main__":
    app.run()
