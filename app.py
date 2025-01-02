from shiny import App, render, ui, reactive
import pandas as pd

# Initial empty DataFrames for all 8 lists
initial_df = pd.DataFrame({
    'task': [],
    'description': [],
})

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.accordion(
            ui.accordion_panel(
                "List Selection",
                ui.panel_well(
                    ui.input_radio_buttons(
                        "current_list",
                        "Choose List",
                        choices={
                            f"list_{i}": f"List {i}" 
                            for i in range(1, 9)
                        },
                        selected="list_1"
                    ),
                )
            )
        ),
        ui.br(),
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
        ui.br(),
        ui.panel_well(
            "Move to Different List",
            ui.output_ui("move_to_list_panel")
        ),
        width="400px"
    ),
    ui.output_code("markdown_list"),
)

def server(input, output, session):
    lists_rv = {
        f"list_{i}": reactive.value(initial_df.copy()) 
        for i in range(1, 9)
    }
    selected_rows = reactive.value([])  # Changed to list for multiple selections

    def get_current_list():
        return lists_rv[input.current_list()]

    @render.ui
    def task_selector():
        df = get_current_list()()
        if len(df) == 0:
            return ui.p("No tasks available")
        
        return ui.input_checkbox_group(  # Changed to checkbox group
            "selected_tasks",  # Changed name to plural
            "Select Tasks",    # Changed label to plural
            choices={str(i): row['task'] for i, row in df.iterrows()},
            selected=[str(i) for i in selected_rows()]  # Support multiple selections
        )

    @render.ui
    def edit_panel():
        selected = selected_rows()
        if len(selected) == 1:  # Only show edit panel when exactly one task is selected
            df = get_current_list()()
            return ui.div(
                ui.input_text("edit_task", "Task Name", 
                            value=df.iloc[selected[0]]["task"]),
                ui.input_text_area("edit_description", "Description", 
                                 value=df.iloc[selected[0]]["description"]),
                ui.input_action_button("save", "Save Changes")
            )
        elif len(selected) > 1:
            return ui.p("Select only one task to edit")
        return ui.p("Select a task to edit")

    @render.ui
    def move_to_list_panel():
        if len(selected_rows()) > 0:  # Show if any tasks are selected
            current_list = input.current_list()
            choices = {
                f"list_{i}": f"List {i}"
                for i in range(1, 9)
                if f"list_{i}" != current_list
            }
            
            return ui.div(
                ui.input_select(
                    "destination_list",
                    "Move to List",
                    choices=choices
                ),
                ui.input_action_button("move_to_list", "Move Selected Tasks")  # Updated label
            )
        return ui.p("Select tasks to move")

    @render.text
    def markdown_list():
        current_list_name = input.current_list().replace('_', ' ').title()
        df = get_current_list()()
        if len(df) == 0:
            return f"{current_list_name}\n\nNo tasks yet!"
        
        output = [f"{current_list_name}\n"]
        
        for idx, row in df.iterrows():
            output.append(f"\n• {row['task']}")
            if row['description']:
                desc_lines = row['description'].split('\n')
                for line in desc_lines:
                    if line.strip():
                        output.append(f"    {line}")
        
        return '\n'.join(output)

    @reactive.effect
    @reactive.event(input.add)
    def add_task():
        if input.task() and input.description():
            new_task = pd.DataFrame({
                'task': [input.task()],
                'description': [input.description()]
            })
            current_df = get_current_list()()
            get_current_list().set(pd.concat([current_df, new_task], ignore_index=True))
            ui.update_text("task", value="")
            ui.update_text("description", value="")

    @reactive.effect
    @reactive.event(input.selected_tasks, input.current_list)
    def update_selection():
        selected = input.selected_tasks()
        if selected is None:
            selected_rows.set([])
        else:
            selected_rows.set([int(x) for x in selected])

    @reactive.effect
    @reactive.event(input.save)
    def save_changes():
        selected = selected_rows()
        if len(selected) == 1:
            df = get_current_list()()
            df.loc[selected[0], "task"] = input.edit_task()
            df.loc[selected[0], "description"] = input.edit_description()
            get_current_list().set(df.copy())

    @reactive.effect
    @reactive.event(input.move_to_list)
    def move_task_to_list():
        selected = selected_rows()
        if len(selected) > 0 and input.destination_list():
            source_df = get_current_list()()
            tasks_to_move = source_df.iloc[selected].copy()
            
            # Remove selected tasks from current list
            source_df = source_df.drop(selected).reset_index(drop=True)
            get_current_list().set(source_df.copy())
            
            # Add tasks to destination list
            dest_list = lists_rv[input.destination_list()]
            dest_df = dest_list()
            dest_df = pd.concat([dest_df, tasks_to_move], ignore_index=True)
            dest_list.set(dest_df.copy())
            
            selected_rows.set([])

    @reactive.effect
    @reactive.event(input.delete)
    def delete_task():
        selected = selected_rows()
        if len(selected) > 0:
            df = get_current_list()()
            df = df.drop(selected).reset_index(drop=True)
            get_current_list().set(df.copy())
            selected_rows.set([])

    @reactive.effect
    @reactive.event(input.move_up)
    def move_task_up():
        selected = selected_rows()
        if len(selected) == 1 and selected[0] > 0:  # Only move one task at a time
            df = get_current_list()()
            idx = selected[0]
            df.iloc[idx-1:idx+1] = df.iloc[idx-1:idx+1].iloc[::-1].values
            get_current_list().set(df.copy())
            selected_rows.set([idx-1])
            ui.update_checkbox_group("selected_tasks", selected=[str(idx-1)])

    @reactive.effect
    @reactive.event(input.move_down)
    def move_task_down():
        selected = selected_rows()
        if len(selected) == 1 and selected[0] < len(get_current_list()())-1:  # Only move one task at a time
            df = get_current_list()()
            idx = selected[0]
            df.iloc[idx:idx+2] = df.iloc[idx:idx+2].iloc[::-1].values
            get_current_list().set(df.copy())
            selected_rows.set([idx+1])
            ui.update_checkbox_group("selected_tasks", selected=[str(idx+1)])

app = App(app_ui, server)