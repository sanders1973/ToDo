from shiny import App, render, ui, reactive
import pandas as pd

# Initial empty DataFrame for storing tasks
initial_df = pd.DataFrame({
    'task': [],
    'description': [],
})

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.panel_well(
            "Add New Task",
            ui.input_text("task", "Task Name"),
            ui.input_text_area("description", "Description"),
            ui.input_action_button("add", "Add Task"),
        ),
        ui.br(),
        ui.panel_well(
            "Task List",
            ui.output_ui("task_selector"),
            ui.br(),
            ui.input_action_button("move_up", "Move Up"),
            ui.input_action_button("move_down", "Move Down"),
            ui.input_action_button("delete", "Delete Selected"),
        ),
        ui.br(),
        ui.panel_well(
            "Edit Selected Task",
            ui.output_ui("edit_panel")
        ),
        width="400px"
    ),
    ui.output_text("markdown_list"),
)

def server(input, output, session):
    # Reactive values for the task DataFrame and selected row
    tasks_rv = reactive.value(initial_df)
    selected_row = reactive.value(None)

    @render.ui
    def task_selector():
        df = tasks_rv()
        if len(df) == 0:
            return ui.p("No tasks available")
        
        # Use the selected_row value to set the selected radio button
        current_selection = str(selected_row()) if selected_row() is not None else None
        
        return ui.input_radio_buttons(
            "selected_task",
            "Select Task",
            choices={str(i): row['task'] for i, row in df.iterrows()},
            selected=current_selection
        )

    @render.ui
    def edit_panel():
        if selected_row() is not None:
            return ui.div(
                ui.input_text("edit_task", "Task Name", 
                            value=tasks_rv().iloc[selected_row()]["task"]),
                ui.input_text_area("edit_description", "Description", 
                                 value=tasks_rv().iloc[selected_row()]["description"]),
                ui.input_action_button("save", "Save Changes")
            )
        return ui.p("Select a task to edit")

    @render.text
    def markdown_list():
        df = tasks_rv()
        if len(df) == 0:
            return "No tasks yet!"
        
        markdown = "# To Do List\n\n"
        for idx, row in df.iterrows():
            markdown += f"## {row['task']}\n"
            markdown += f"{row['description']}\n\n"
        return markdown

    @reactive.effect
    @reactive.event(input.add)
    def add_task():
        if input.task() and input.description():
            new_task = pd.DataFrame({
                'task': [input.task()],
                'description': [input.description()]
            })
            tasks_rv.set(pd.concat([tasks_rv(), new_task], ignore_index=True))
            ui.update_text("task", value="")
            ui.update_text("description", value="")

    @reactive.effect
    @reactive.event(input.selected_task)
    def update_selection():
        if input.selected_task() is not None:
            selected_row.set(int(input.selected_task()))
        else:
            selected_row.set(None)

    @reactive.effect
    @reactive.event(input.save)
    def save_changes():
        if selected_row() is not None:
            df = tasks_rv()
            df.loc[selected_row(), "task"] = input.edit_task()
            df.loc[selected_row(), "description"] = input.edit_description()
            tasks_rv.set(df.copy())  # Use copy to ensure reactivity

    @reactive.effect
    @reactive.event(input.delete)
    def delete_task():
        if selected_row() is not None:
            df = tasks_rv()
            df = df.drop(selected_row()).reset_index(drop=True)
            tasks_rv.set(df.copy())  # Use copy to ensure reactivity
            selected_row.set(None)

    @reactive.effect
    @reactive.event(input.move_up)
    def move_task_up():
        if selected_row() is not None and selected_row() > 0:
            df = tasks_rv()
            idx = selected_row()
            # Swap rows
            df.iloc[idx-1:idx+1] = df.iloc[idx-1:idx+1].iloc[::-1].values
            # Update DataFrame and selection
            tasks_rv.set(df.copy())  # Use copy to ensure reactivity
            selected_row.set(idx-1)
            # Update radio button selection
            ui.update_radio_buttons("selected_task", selected=str(idx-1))

    @reactive.effect
    @reactive.event(input.move_down)
    def move_task_down():
        if selected_row() is not None and selected_row() < len(tasks_rv())-1:
            df = tasks_rv()
            idx = selected_row()
            # Swap rows
            df.iloc[idx:idx+2] = df.iloc[idx:idx+2].iloc[::-1].values
            # Update DataFrame and selection
            tasks_rv.set(df.copy())  # Use copy to ensure reactivity
            selected_row.set(idx+1)
            # Update radio button selection
            ui.update_radio_buttons("selected_task", selected=str(idx+1))

app = App(app_ui, server)