from shiny import App, reactive, render, ui
import json
import base64
import requests
import os
from datetime import datetime, timezone


# Define the list names
LIST_NAMES = {
    "list1": "List 1",
    "list2": "List 2",
    "list3": "List 3",
    "list4": "List 4",
    "list5": "List 5",
    "list6": "List 6",
    "list7": "List 7",
    "list8": "List 8",
    "list9": "List 9",
    "list10": "List 10"
}

app_ui = ui.page_fillable(
        ui.tags.style("""
        .draggable-task:hover {
            background-color: #f8f9fa;
        }
        .droppable-list.drag-over {
            border: 2px dashed #007bff !important;
        }
        .draggable-task {
            transition: background-color 0.2s;
        }
        .droppable-list {
            transition: border 0.2s;
        }
        .draggable-task {
            cursor: move;
            padding: 10px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .droppable-list {
            height: 100%;
            min-height: 100px;
            padding: 10px;
            border: 1px dashed #ccc;
            border-radius: 4px;
        }
        /* New styles for control panels */
        .control-panel {
            overflow: visible !important;
            height: auto !important;
            min-height: auto !important;
        }
        .control-panel .card-body {
            overflow: visible !important;
            padding: 15px;
        }
        .button-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            padding: 5px;
        }
        .move-controls {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
    """),
    ui.layout_sidebar(
        ui.sidebar(
            ui.accordion(
                ui.accordion_panel(
                    "Settings",
                    ui.output_text("online_status"),
                    ui.input_dark_mode(id=None, mode="dark"),
                    ui.input_switch("autosave_enabled", "Enable GitHub Auto-save", value=True),
                ),
                id="settings_accordion",
                open=False
            ),
            
            ui.input_text("task", "Enter Task"),
            ui.input_text_area("description", "Enter Description", height="100px"),
            ui.input_action_button("add", "Add Task", class_="btn-primary"),
            ui.output_text("unsaved_changes_alert"),
            ui.output_ui("manual_save_button"),
            ui.output_ui("task_selector"),
            
            ui.input_action_button("load_github", "Load from GitHub", class_="btn-info"),
            ui.input_text(
                "github_repo",
                "Repository (user/repo)",
                value="",
                autocomplete="username/rep"
            ),
            ui.input_password(
                "github_token",
                "Github Token",
                value=""
            ),
            ui.output_text("github_status_output"),
            
            ui.input_action_button("edit_list_names", "Edit List Names", class_="btn-secondary"),
            ui.output_ui("list_name_controls"),
            width=350
        ),

        # Main content starts here
        ui.accordion(
            ui.accordion_panel(
                "Working List (for adding/editing)",
                ui.input_radio_buttons(
                    "active_list",
                    "",
                    LIST_NAMES,
                    inline=True
                ),
            ),
            open=True,
            id="working_list_accordion",
        ),
        
        ui.div(
        {"style": "display: flex; flex-direction: column; gap: 10px; height: 100%;"},
        ui.div(
            {"style": "flex: 0 0 auto;"},  # This div won't grow or shrink
            ui.output_ui("edit_controls"),
            ui.output_ui("move_controls"),
            ui.output_ui("conflict_dialog"),
        ),
        ui.div(
            {"style": "flex: 1 1 auto; min-height: 0;"},  # This div will take remaining space
            ui.card(
                ui.accordion(
                    ui.accordion_panel(
                        "Select Lists to Display",
                        ui.input_checkbox_group(
                            "display_lists",
                            "",
                            LIST_NAMES,
                            selected=["list1"],
                            inline=True
                        )
                    ),
                    open=True,
                    id="display_lists_accordion"
                ),
                ui.input_switch("use_drag_drop", "Enable drag and drop view", value=False),
                ui.output_ui("task_lists_display"),
                full_screen=True
            )
        )
    )
    )
)

def server(input, output, session):
    # Create a dictionary to store tasks and descriptions for each list
    lists_data = reactive.value({
        list_id: {"tasks": [], "descriptions": []}
        for list_id in LIST_NAMES.keys()
    })
    
    changes_unsaved = reactive.value(False)
    editing = reactive.value(False)
        # Add these near the start of the server function with other reactive values
    is_online = reactive.value(True)  # Track online status
    pending_changes = reactive.value([])  # Queue of changes made while offline
    loaded_file_timestamp = reactive.value("")
    showing_conflict_dialog = reactive.value(False)

   
    def format_metadata(timestamp):
        return f"--- METADATA ---\nLast updated: {timestamp}\n--- END METADATA ---\n\n"
    
    def extract_metadata(content):
        if "--- METADATA ---" not in content:
            return ""  # Return empty string instead of None
        try:
            timestamp_line = content.split("--- METADATA ---")[1].split("--- END METADATA ---")[0]
            timestamp = timestamp_line.split("Last updated: ")[1].strip()
            return timestamp if timestamp else ""  # Return empty string if timestamp is empty
        except:
            return ""  # Return empty string on any error
    
    def check_for_conflicts():
        if not input.github_token() or not input.github_repo():
            return False
        
        try:
            # GitHub API endpoint
            repo = input.github_repo()
            path = "ToDoList.txt"
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
    
            # Headers for authentication
            headers = {
                "Authorization": f"token {input.github_token()}",
                "Accept": "application/vnd.github.v3+json"
            }
    
            # Get the file content
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Decode content from base64
                content = base64.b64decode(response.json()["content"]).decode()
                github_timestamp = extract_metadata(content)
                stored_timestamp = loaded_file_timestamp.get()
                
                print(f"Current GitHub timestamp: {github_timestamp}")
                print(f"Stored local timestamp: {stored_timestamp}")
                
                # Only detect conflict if both timestamps exist and are different
                if github_timestamp and stored_timestamp and github_timestamp != stored_timestamp:
                    print("Conflict detected!")
                    return True
                print("No conflict detected")
            return False
        except Exception as e:
            print(f"Error in check_for_conflicts: {str(e)}")
            return False
    
    @render.ui
    def conflict_dialog():
        if not showing_conflict_dialog.get():
            return ui.div()
        
        return ui.card(
            ui.h3("Conflict Detected!", style="color: red;"),
            ui.p("The file on GitHub has been modified since you last loaded it."),
            ui.p("What would you like to do?"),
            ui.div(
                ui.input_action_button("resolve_conflict_overwrite", "Overwrite GitHub Version", class_="btn-warning"),
                ui.input_action_button("resolve_conflict_reload", "Reload from GitHub", class_="btn-info"),
                style="display: flex; gap: 10px;"
            )
        )
    
    @reactive.effect
    @reactive.event(input.resolve_conflict_overwrite)
    def handle_conflict_overwrite():
        showing_conflict_dialog.set(False)
        # Force save without checking conflicts
        save_to_github(force=True)
    
    
    
    
    
    def check_online_status():
        try:
            requests.get("https://api.github.com", timeout=2)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False       

    def get_current_list():
        return lists_data.get()[input.active_list()]

    @reactive.effect
    @reactive.event(input.add)
    def add_task():
        if input.task().strip():
            current_data = lists_data.get().copy()
            current_list = current_data[input.active_list()]
            
            # Changed from append() to insert(0, ...)
            current_list["tasks"].insert(0, input.task())
            current_list["descriptions"].insert(0, input.description())
            
            lists_data.set(current_data)
            changes_unsaved.set(True)
            ui.update_text("task", value="")
        ui.update_text("description", value="")
    
    @render.ui
    def task_selector():
        current_list = get_current_list()
        if not current_list["tasks"]:
            return ui.p("No tasks in this list")
        
        options = {str(i): f"{i}. {task}" 
                  for i, task in enumerate(current_list["tasks"], 1)}
        
        return ui.div(
            ui.input_checkbox_group(
                "selected_tasks",
                "Select Tasks to Move/Edit",
                options
            )
        )

    @render.text
    def online_status():
        if not is_online.get():
            return "📴 Offline Mode - Changes will sync when online"
        return "🌐 Online"

    
    @render.ui
    def task_lists_display():
        selected_lists = input.display_lists()
        if not selected_lists:
            return ui.p("Please select lists to display")
        
        col_width = 12 // len(selected_lists)
        col_width = max(3, min(12, col_width))
        
        if not input.use_drag_drop():
            # Original markdown view
            columns = []
            for list_id in selected_lists:
                current_list = lists_data.get()[list_id]
                current_tasks = current_list["tasks"]
                current_descriptions = current_list["descriptions"]
                
                task_items = []
                task_items.append(ui.h3(LIST_NAMES[list_id]))
                
                if not current_tasks:
                    task_items.append(ui.p("No tasks in this list"))
                else:
                    for i, (task, desc) in enumerate(zip(current_tasks, current_descriptions), 1):
                        desc_paragraphs = [ui.p(p, style="text-indent:50px") for p in desc.split('\n')]
                        task_html = ui.div(
                            ui.h5(f"• {task}"),
                            *desc_paragraphs,
                            style="margin-bottom: 0;"
                        )
                        task_items.append(task_html)
                
                column = ui.column(
                    col_width,
                    ui.card(
                        *task_items,
                        style="height: 100%;"
                    )
                )
                columns.append(column)
            
            return ui.row(*columns)
        else:
            # Drag and drop view
            columns = []
            for list_id in selected_lists:
                current_list = lists_data.get()[list_id]
                current_tasks = current_list["tasks"]
                current_descriptions = current_list["descriptions"]
                
                task_items = []
                
                if not current_tasks:
                    task_items.append(ui.p("No tasks in this list"))
                else:
                    for i, (task, desc) in enumerate(zip(current_tasks, current_descriptions)):
                        task_html = ui.div(
                            {"draggable": "true",
                             "data-task-id": f"{list_id}-{i}",
                             "data-list-id": list_id,
                             "data-task-index": str(i),
                             "ondragstart": "handleDragStart(event)",
                             "ondragover": "handleDragOver(event)",
                             "ondrop": "handleDrop(event)",
                             "class": "draggable-task"},
                            ui.h5(task),
                            ui.p(desc) if desc else "",
                            style="cursor: move; padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px;"
                        )
                        task_items.append(task_html)
                
                column = ui.column(
                    col_width,
                    ui.div(
                        {"data-list-id": list_id,
                         "class": "droppable-list",
                         "ondragover": "handleDragOver(event)",
                         "ondrop": "handleDrop(event)"},
                        ui.h3(LIST_NAMES[list_id]),
                        *task_items,
                        style="height: 100%; min-height: 100px; padding: 10px; border: 1px dashed #ccc; border-radius: 4px;"
                    )
                )
                columns.append(column)
            
            # Add required JavaScript
            script = """
            function handleDragStart(event) {
                event.dataTransfer.setData('text/plain', 
                    JSON.stringify({
                        taskId: event.target.dataset.taskId,
                        listId: event.target.dataset.listId,
                        taskIndex: event.target.dataset.taskIndex
                    })
                );
            }
            
            function handleDragOver(event) {
                event.preventDefault();
            }
            
            function handleDrop(event) {
                event.preventDefault();
                const data = JSON.parse(event.dataTransfer.getData('text/plain'));
                
                // Get target list and position
                let targetElement = event.target;
                while (targetElement && !targetElement.classList.contains('droppable-list') &&
                       !targetElement.classList.contains('draggable-task')) {
                    targetElement = targetElement.parentElement;
                }
                
                if (!targetElement) return;
                
                const targetListId = targetElement.dataset.listId;
                let targetIndex = -1;
                
                if (targetElement.classList.contains('draggable-task')) {
                    targetIndex = parseInt(targetElement.dataset.taskIndex);
                }
                
                // Send move information to Shiny
                const moveInfo = {
                    sourceListId: data.listId,
                    sourceIndex: parseInt(data.taskIndex),
                    targetListId: targetListId,
                    targetIndex: targetIndex
                };
                
                Shiny.setInputValue('drag_drop_move', moveInfo);
            }
            """
            
            return ui.tags.div(
                ui.tags.script(script),
                ui.row(*columns)
            )

    @render.ui
    def move_controls():
        if not input.selected_tasks():
            return ui.div()
            
        current_list_id = input.active_list()
        move_options = {k: v for k, v in LIST_NAMES.items() if k != current_list_id}
        
        return ui.card(
            {"class": "control-panel"},
            ui.div(
                {"class": "move-controls"},
                ui.input_radio_buttons(
                    "move_to_list",
                    "Move selected tasks to:",
                    move_options,
                    inline=True
                ),
                ui.input_action_button(
                    "move_tasks", 
                    "Move Tasks", 
                    class_="btn-info"
                )
            )
        )
    
    
    @reactive.effect
    @reactive.event(input.drag_drop_move)
    def handle_drag_drop_move():
        move_info = input.drag_drop_move()
        current_data = lists_data.get().copy()
        
        source_list = current_data[move_info["sourceListId"]]
        source_index = move_info["sourceIndex"]
        target_list_id = move_info["targetListId"]
        target_index = move_info["targetIndex"]
        
        # Get the task and description to move
        task = source_list["tasks"][source_index]
        desc = source_list["descriptions"][source_index]
        
        # Remove from source
        source_list["tasks"].pop(source_index)
        source_list["descriptions"].pop(source_index)
        
        # Add to target
        if target_list_id == move_info["sourceListId"]:
            # Moving within the same list
            if target_index >= 0:
                # Insert at specific position
                target_index = min(target_index, len(source_list["tasks"]))
                source_list["tasks"].insert(target_index, task)
                source_list["descriptions"].insert(target_index, desc)
            else:
                # Append to end
                source_list["tasks"].append(task)
                source_list["descriptions"].append(desc)
        else:
            # Moving to different list
            target_list = current_data[target_list_id]
            if target_index >= 0:
                # Insert at specific position
                target_index = min(target_index, len(target_list["tasks"]))
                target_list["tasks"].insert(target_index, task)
                target_list["descriptions"].insert(target_index, desc)
            else:
                # Append to end
                target_list["tasks"].append(task)
                target_list["descriptions"].append(desc)
        
        lists_data.set(current_data)
        changes_unsaved.set(True)


    @render.ui
    def edit_controls():
        if not input.selected_tasks():
            return ui.div()
        
        if len(input.selected_tasks()) == 1:
            if editing.get():
                task_idx = int(input.selected_tasks()[0]) - 1
                current_list = get_current_list()
                
                return ui.card(
                    {"class": "control-panel"},
                    ui.h4("Edit Task"),
                    ui.input_text(
                        "edit_task",
                        "Task",
                        value=current_list["tasks"][task_idx]
                    ),
                    ui.input_text_area(
                        "edit_description",
                        "Description",
                        value=current_list["descriptions"][task_idx],
                        height="100px"
                    ),
                    ui.div(
                        {"class": "button-container"},
                        ui.input_action_button("save_edit", "Save", class_="btn-success"),
                        ui.input_action_button("cancel_edit", "Cancel", class_="btn-secondary")
                    )
                )
            else:
                return ui.card(
                    {"class": "control-panel"},
                    ui.div(
                        {"class": "button-container"},
                        ui.input_action_button("delete_task", "Delete Task", class_="btn-danger"),
                        ui.input_action_button("start_edit", "Edit Task", class_="btn-warning"),
                        ui.input_action_button("move_up", "↑ Move Up", class_="btn-primary"),
                        ui.input_action_button("move_down", "↓ Move Down", class_="btn-primary")
                    )
                )
        else:
            return ui.card(
                {"class": "control-panel"},
                ui.div(
                    {"class": "button-container"},
                    ui.input_action_button("delete_task", "Delete Selected Tasks", class_="btn-danger")
                )
            )
        



    

    @reactive.effect
    @reactive.event(input.move_tasks)
    def move_selected_tasks():
        if not input.selected_tasks():
            return
            
        selected_indices = [int(idx) - 1 for idx in input.selected_tasks()]
        source_list_id = input.active_list()
        target_list_id = input.move_to_list()
        
        current_data = lists_data.get().copy()
        source_list = current_data[source_list_id]
        target_list = current_data[target_list_id]
        
        # Get tasks and descriptions to move
        tasks_to_move = [source_list["tasks"][i] for i in selected_indices]
        descriptions_to_move = [source_list["descriptions"][i] for i in selected_indices]
        
        # Add to target list
        target_list["tasks"].extend(tasks_to_move)
        target_list["descriptions"].extend(descriptions_to_move)
        
        # Remove from source list (in reverse order to maintain indices)
        for i in sorted(selected_indices, reverse=True):
            source_list["tasks"].pop(i)
            source_list["descriptions"].pop(i)
        
        lists_data.set(current_data)
        changes_unsaved.set(True)  # Add this line

    @reactive.effect
    @reactive.event(input.start_edit)
    def start_editing():
        editing.set(True)

    @reactive.effect
    @reactive.event(input.cancel_edit)
    def cancel_editing():
        editing.set(False)

    @reactive.effect
    @reactive.event(input.save_edit)
    def save_edit():
        if not input.selected_tasks():
            return
            
        task_idx = int(input.selected_tasks()[0]) - 1
        current_data = lists_data.get().copy()
        current_list = current_data[input.active_list()]
        
        current_list["tasks"][task_idx] = input.edit_task()
        current_list["descriptions"][task_idx] = input.edit_description()
        
        lists_data.set(current_data)
        changes_unsaved.set(True)  # Add this line
        editing.set(False)

    # Add a reactive value for GitHub save status
    github_status = reactive.value("")

  
    @render.text
    def github_status_output():
        return github_status.get()

    @reactive.effect
    @reactive.event(input.move_up)
    def move_task_up():
        if not input.selected_tasks() or len(input.selected_tasks()) != 1:
            return
            
        task_idx = int(input.selected_tasks()[0]) - 1
        if task_idx <= 0:  # Can't move up if already at top
            return
            
        current_data = lists_data.get().copy()
        current_list = current_data[input.active_list()]
        
        # Swap tasks
        current_list["tasks"][task_idx], current_list["tasks"][task_idx-1] = \
            current_list["tasks"][task_idx-1], current_list["tasks"][task_idx]
        
        # Swap descriptions
        current_list["descriptions"][task_idx], current_list["descriptions"][task_idx-1] = \
            current_list["descriptions"][task_idx-1], current_list["descriptions"][task_idx]
        
        lists_data.set(current_data)
        changes_unsaved.set(True)  # Add this line
        
        # Update the selection to follow the moved task
        ui.update_checkbox_group(
            "selected_tasks",
            selected=[str(task_idx)]  # Index is 0-based, but UI is 1-based
        )

    @reactive.effect
    @reactive.event(input.move_down)
    def move_task_down():
        if not input.selected_tasks() or len(input.selected_tasks()) != 1:
            return
            
        task_idx = int(input.selected_tasks()[0]) - 1
        current_data = lists_data.get().copy()
        current_list = current_data[input.active_list()]
        
        if task_idx >= len(current_list["tasks"]) - 1:  # Can't move down if already at bottom
            return
            
        # Swap tasks
        current_list["tasks"][task_idx], current_list["tasks"][task_idx+1] = \
            current_list["tasks"][task_idx+1], current_list["tasks"][task_idx]
        
        # Swap descriptions
        current_list["descriptions"][task_idx], current_list["descriptions"][task_idx+1] = \
            current_list["descriptions"][task_idx+1], current_list["descriptions"][task_idx]
        
        lists_data.set(current_data)
        changes_unsaved.set(True)  # Add this line
        
        # Update the selection to follow the moved task
        ui.update_checkbox_group(
            "selected_tasks",
            selected=[str(task_idx + 2)]  # Index is 0-based, but UI is 1-based
        )    
    
    @reactive.effect
    @reactive.event(input.delete_task)
    def delete_task():
        if not input.selected_tasks():
            return
            
        selected_indices = [int(idx) - 1 for idx in input.selected_tasks()]
        current_data = lists_data.get().copy()
        current_list = current_data[input.active_list()]
        
        # Remove tasks and descriptions in reverse order to maintain correct indices
        for idx in sorted(selected_indices, reverse=True):
            current_list["tasks"].pop(idx)
            current_list["descriptions"].pop(idx)
        
        lists_data.set(current_data)
        changes_unsaved.set(True)    
   
    @reactive.effect
    @reactive.event(lists_data, input.autosave_enabled)
    def auto_save():
        # Check online status first
        is_online.set(check_online_status())
        
        # If autosave was just disabled but there are no actual changes,
        # make sure changes_unsaved is False
        if not input.autosave_enabled() and not changes_unsaved.get():
            return
    
        # If there are no changes, nothing to do
        if not changes_unsaved.get():
            return
    
        # If autosave is disabled, keep existing unsaved state
        if not input.autosave_enabled():
            return
    
        if not input.github_token() or not input.github_repo():
            github_status.set("Please fill in GitHub credentials to enable auto-save")
            return
    
        # If we're offline, queue the changes
        if not is_online.get():
            if changes_unsaved.get():
                github_status.set("⚠️ Changes pending - Currently offline")
                # Store the current state
                pending_changes.set(pending_changes.get() + [lists_data.get()])
            return
    
        # Check for conflicts first, before creating new timestamp
        path = "ToDoList.txt"
        try:
            # GitHub API endpoint
            repo = input.github_repo()
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
            headers = {
                "Authorization": f"token {input.github_token()}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get current GitHub content
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                content = base64.b64decode(response.json()["content"]).decode()
                github_timestamp = extract_metadata(content)
                stored_timestamp = loaded_file_timestamp.get()
                
                print(f"Auto-save - GitHub timestamp: {github_timestamp}")
                print(f"Auto-save - Local timestamp: {stored_timestamp}")
                
                if github_timestamp != stored_timestamp:
                    print("Auto-save - Conflict detected!")
                    showing_conflict_dialog.set(True)
                    return
        except Exception as e:
            print(f"Auto-save - Error checking conflicts: {str(e)}")
            return
    
        try:
            # Now proceed with save
            data = lists_data.get()
            current_timestamp = datetime.now(timezone.utc).isoformat()
            formatted_data = format_metadata(current_timestamp)
            
            for list_id, list_name in LIST_NAMES.items():
                formatted_data += f"=== {list_name} ===\n"
                list_content = data[list_id]
                for task, desc in zip(list_content["tasks"], list_content["descriptions"]):
                    formatted_data += f"- {task}\n"
                    if desc.strip():
                        formatted_data += f"  |{desc}\n"
                formatted_data += "\n"
    
            # Check if file exists and get its SHA
            try:
                response = requests.get(url, headers=headers)
                sha = response.json()["sha"] if response.status_code == 200 else None
            except:
                sha = None
    
            # Prepare the content
            content = base64.b64encode(formatted_data.encode()).decode()
    
            # Prepare the data for the API request
            data = {
                "message": "Auto-update task lists",
                "content": content,
            }
            if sha:
                data["sha"] = sha
    
            # Make the API request
            response = requests.put(url, headers=headers, json=data)
    
            if response.status_code in [200, 201]:
                github_status.set("✓ Changes saved automatically")
                changes_unsaved.set(False)
                loaded_file_timestamp.set(str(current_timestamp))
            else:
                github_status.set(f"❌ Error auto-saving: {response.status_code}")
    
        except requests.RequestException as e:
            github_status.set("⚠️ Changes pending - Network error")
        except Exception as e:
            github_status.set(f"❌ Error auto-saving: {str(e)}")


    @reactive.effect
    def handle_online_status():
        # Periodically check online status
        current_online_status = check_online_status()
        is_online.set(current_online_status)
        
        # If we just came back online and have pending changes
        if current_online_status and pending_changes.get():
            try:
                # Process pending changes
                if input.autosave_enabled():
                    # Trigger a save with the latest state
                    lists_data.set(pending_changes.get()[-1])  # Use most recent change
                    pending_changes.set([])  # Clear the queue
                    github_status.set("✓ Syncing changes after coming back online...")
            except Exception as e:
                github_status.set(f"❌ Error syncing changes: {str(e)}")
    
    @reactive.effect
    @reactive.event(input.quick_save)
    def handle_quick_save():
        if not input.github_token() or not input.github_repo():
            github_status.set("Please fill in GitHub credentials in the sidebar first")
            return
    
        # Check for conflicts first, before creating new timestamp
        path = "ToDoList.txt"
        try:
            # GitHub API endpoint
            repo = input.github_repo()
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
            headers = {
                "Authorization": f"token {input.github_token()}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get current GitHub content
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                content = base64.b64decode(response.json()["content"]).decode()
                github_timestamp = extract_metadata(content)
                stored_timestamp = loaded_file_timestamp.get()
                
                print(f"Quick save - GitHub timestamp: {github_timestamp}")
                print(f"Quick save - Local timestamp: {stored_timestamp}")
                
                if github_timestamp != stored_timestamp:
                    print("Quick save - Conflict detected!")
                    showing_conflict_dialog.set(True)
                    return
        except Exception as e:
            print(f"Quick save - Error checking conflicts: {str(e)}")
            return
    
        try:
            # Now proceed with save
            data = lists_data.get()
            current_timestamp = datetime.now(timezone.utc).isoformat()
            formatted_data = format_metadata(current_timestamp)
            
            for list_id, list_name in LIST_NAMES.items():
                formatted_data += f"=== {list_name} ===\n"
                list_content = data[list_id]
                for task, desc in zip(list_content["tasks"], list_content["descriptions"]):
                    formatted_data += f"- {task}\n"
                    if desc.strip():
                        formatted_data += f"  |{desc}\n"
                formatted_data += "\n"
    
            # Check if file exists and get its SHA
            try:
                response = requests.get(url, headers=headers)
                sha = response.json()["sha"] if response.status_code == 200 else None
            except:
                sha = None
    
            # Prepare the content
            content = base64.b64encode(formatted_data.encode()).decode()
    
            # Prepare the data for the API request
            data = {
                "message": "Quick update task lists",
                "content": content,
            }
            if sha:
                data["sha"] = sha
    
            # Make the API request
            response = requests.put(url, headers=headers, json=data)
    
            if response.status_code in [200, 201]:
                github_status.set("Successfully saved to GitHub!")
                changes_unsaved.set(False)
                loaded_file_timestamp.set(str(current_timestamp))
            else:
                github_status.set(f"Error saving to GitHub: {response.status_code}")
    
        except Exception as e:
            github_status.set(f"Error: {str(e)}")

    
    def save_to_github(force=False):
        path = "ToDoList.txt"
        if not input.github_token() or not input.github_repo():
            github_status.set("Please fill in all GitHub fields")
            return
    
        # Check for conflicts first, before creating new timestamp
        if not force:
            try:
                # GitHub API endpoint
                repo = input.github_repo()
                url = f"https://api.github.com/repos/{repo}/contents/{path}"
                headers = {
                    "Authorization": f"token {input.github_token()}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                # Get current GitHub content
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    content = base64.b64decode(response.json()["content"]).decode()
                    github_timestamp = extract_metadata(content)
                    stored_timestamp = loaded_file_timestamp.get()
                    
                    print(f"GitHub timestamp: {github_timestamp}")
                    print(f"Local timestamp: {stored_timestamp}")
                    
                    if github_timestamp != stored_timestamp:
                        print("Conflict detected!")
                        showing_conflict_dialog.set(True)
                        return
            except Exception as e:
                print(f"Error checking conflicts: {str(e)}")
                return
    
        try:
            # Now proceed with save
            data = lists_data.get()
            current_timestamp = datetime.now(timezone.utc).isoformat()
            formatted_data = format_metadata(current_timestamp)
            
            for list_id, list_name in LIST_NAMES.items():
                formatted_data += f"=== {list_name} ===\n"
                list_content = data[list_id]
                for task, desc in zip(list_content["tasks"], list_content["descriptions"]):
                    formatted_data += f"- {task}\n"
                    if desc.strip():
                        formatted_data += f"  |{desc}\n"
                formatted_data += "\n"
    
            # GitHub API endpoint
            repo = input.github_repo()
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
    
            # Headers for authentication
            headers = {
                "Authorization": f"token {input.github_token()}",
                "Accept": "application/vnd.github.v3+json"
            }
    
            # Check if file exists and get its SHA
            try:
                response = requests.get(url, headers=headers)
                sha = response.json()["sha"] if response.status_code == 200 else None
            except:
                sha = None
    
            # Prepare the content
            content = base64.b64encode(formatted_data.encode()).decode()
    
            # Prepare the data for the API request
            data = {
                "message": "Update task lists",
                "content": content,
            }
            if sha:
                data["sha"] = sha
    
            # Make the API request
            response = requests.put(url, headers=headers, json=data)
    
            if response.status_code in [200, 201]:
                github_status.set("Successfully saved to GitHub!")
                changes_unsaved.set(False)
                # Store the timestamp as string
                loaded_file_timestamp.set(str(current_timestamp))
            else:
                github_status.set(f"Error saving to GitHub: {response.status_code}")
    
        except Exception as e:
            github_status.set(f"Error: {str(e)}")
    
    
    
    
    




    
    def load_list_names_from_github():
        if not input.github_token() or not input.github_repo():
            github_status.set("Please fill in GitHub credentials to load list names")
            return False
    
        try:
            # GitHub API endpoint
            repo = input.github_repo()
            path = "ToDoListNames.txt"
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
    
            # Headers for authentication
            headers = {
                "Authorization": f"token {input.github_token()}",
                "Accept": "application/vnd.github.v3+json"
            }
    
            # Get the file content
            response = requests.get(url, headers=headers)
            
            if response.status_code == 404:
                # File doesn't exist yet, this is okay
                github_status.set("No saved list names found, using defaults")
                return True
            elif response.status_code == 200:
                # Decode content from base64
                content = base64.b64decode(response.json()["content"]).decode()
                
                # Parse the content and update LIST_NAMES
                for line in content.strip().split('\n'):
                    if ':' in line:
                        list_id, name = line.split(':', 1)
                        if list_id in LIST_NAMES:
                            LIST_NAMES[list_id] = name
    
                # Update UI elements
                ui.update_radio_buttons(
                    "active_list",
                    choices=LIST_NAMES
                )
                ui.update_checkbox_group(
                    "display_lists",
                    choices=LIST_NAMES,
                    selected=input.display_lists()
                )
                
                github_status.set("Successfully loaded list names from GitHub!")
                return True
            else:
                github_status.set(f"Error loading list names from GitHub: {response.status_code}")
                return False
    
        except Exception as e:
            github_status.set(f"Error loading list names: {str(e)}")
            return False    

    def perform_load_from_github():        
        # First load the list names
        if not load_list_names_from_github():
            return
                
        path = "ToDoList.txt"
        if not input.github_token() or not input.github_repo():
            github_status.set("Please fill in all GitHub fields")
            return
    
        try:
            # GitHub API endpoint
            repo = input.github_repo()
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
    
            # Headers for authentication
            headers = {
                "Authorization": f"token {input.github_token()}",
                "Accept": "application/vnd.github.v3+json"
            }
    
            # Get the file content
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Decode content from base64
                content = base64.b64decode(response.json()["content"]).decode()
                
                # Extract and store timestamp
                timestamp = extract_metadata(content)
                print(f"Loading file with timestamp: {timestamp}")
                loaded_file_timestamp.set(str(timestamp))  # Ensure it's stored as string
                
                # Remove metadata section before parsing
                if "--- END METADATA ---" in content:
                    content = content.split("--- END METADATA ---")[1].strip()
                
                # Parse the content
                current_list_id = None
                new_data = {list_id: {"tasks": [], "descriptions": []} 
                        for list_id in LIST_NAMES.keys()}
                
                lines = [line.rstrip() for line in content.split('\n')]
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if not line:
                        i += 1
                        continue
                        
                    # Check if this is a list header
                    if line.startswith('===') and line.endswith('==='):
                        list_name = line.strip('= ')
                        # Find the list_id for this list_name
                        current_list_id = next(
                            (k for k, v in LIST_NAMES.items() if v == list_name),
                            None
                        )
                    # Check if this is a task
                    elif line.startswith('- ') and current_list_id:
                        task = line[2:]  # Remove the '- ' prefix
                        new_data[current_list_id]["tasks"].append(task)
                        
                        # Look ahead for description
                        desc = ""
                        if i + 1 < len(lines):
                            next_line = lines[i + 1]
                            if next_line.startswith('  |'):
                                desc = next_line[3:].strip()  # Remove '  |' prefix
                                i += 1  # Skip the description line
                        new_data[current_list_id]["descriptions"].append(desc)
                    
                    i += 1
    
                # Update the lists_data
                lists_data.set(new_data)
                changes_unsaved.set(False)  # Reset unsaved changes flag
                showing_conflict_dialog.set(False)  # Hide conflict dialog if it was showing
                github_status.set("Successfully loaded from GitHub!")
            else:
                github_status.set(f"Error loading from GitHub: {response.status_code}")
    
        except Exception as e:
            github_status.set(f"Error loading: {str(e)}")
    
    @reactive.effect
    @reactive.event(input.load_github)      
    def load_from_github():
        perform_load_from_github()
    
    @reactive.effect
    @reactive.event(input.resolve_conflict_reload)
    def handle_conflict_reload():
        showing_conflict_dialog.set(False)
        perform_load_from_github()

    
 
    editing_names = reactive.value(False)
    
    
    @render.ui
    def list_name_controls():
        if not editing_names.get():
            return ui.div()
            
        inputs = []
        for list_id, current_name in LIST_NAMES.items():
            inputs.extend([
                ui.input_text(
                    f"name_{list_id}",
                    f"Name for {list_id}:",
                    value=current_name
                ),
                ui.br()
            ])
        
        return ui.div(
            ui.card(
                *inputs,
                ui.div(
                    ui.input_action_button(
                        "save_list_names", 
                        "Save Names", 
                        class_="btn-success"
                    ),
                    ui.input_action_button(
                        "cancel_list_names", 
                        "Cancel", 
                        class_="btn-secondary"
                    ),
                    style="display: flex; gap: 10px;"
                )
            )
        )

    @reactive.effect
    @reactive.event(input.edit_list_names)
    def start_editing_names():
        editing_names.set(True)

    @reactive.effect
    @reactive.event(input.cancel_list_names)
    def cancel_editing_names():
        editing_names.set(False)

    @reactive.effect
    @reactive.event(input.save_list_names)
    def save_list_names():
        # Update the LIST_NAMES dictionary with new values
        for list_id in LIST_NAMES.keys():
            LIST_NAMES[list_id] = getattr(input, f"name_{list_id}")()
        
        # Update any UI elements that depend on list names
        ui.update_radio_buttons(
            "active_list",
            choices=LIST_NAMES
        )
        ui.update_checkbox_group(
            "display_lists",
            choices=LIST_NAMES,
            selected=input.display_lists()
        )
        
        # Save to GitHub if credentials are available
        save_list_names_to_github()
        
        editing_names.set(False)
        changes_unsaved.set(True)

    def save_list_names_to_github():
        if not input.github_token() or not input.github_repo():
            github_status.set("Please fill in GitHub credentials to save list names")
            return False

        try:
            # GitHub API endpoint
            repo = input.github_repo()
            path = "ToDoListNames.txt"
            url = f"https://api.github.com/repos/{repo}/contents/{path}"

            # Headers for authentication
            headers = {
                "Authorization": f"token {input.github_token()}",
                "Accept": "application/vnd.github.v3+json"
            }

            # Format the list names data
            formatted_data = "\n".join([f"{list_id}:{name}" for list_id, name in LIST_NAMES.items()])
            content = base64.b64encode(formatted_data.encode()).decode()

            # Check if file exists
            try:
                response = requests.get(url, headers=headers)
                sha = response.json()["sha"] if response.status_code == 200 else None
            except:
                sha = None

            # Prepare the data for the API request
            data = {
                "message": "Update list names",
                "content": content,
            }
            if sha:
                data["sha"] = sha

            # Make the API request
            response = requests.put(url, headers=headers, json=data)

            if response.status_code in [200, 201]:
                github_status.set("Successfully saved list names to GitHub!")
                return True
            else:
                github_status.set(f"Error saving list names to GitHub: {response.status_code}")
                return False

        except Exception as e:
            github_status.set(f"Error saving list names: {str(e)}")
            return False

   
    @render.ui
    def manual_save_button():
        if not input.autosave_enabled() and changes_unsaved.get():
            return ui.input_action_button(
                "save_github",  # Changed from manual_save to save_github
                "Save Changes to GitHub",
                class_="btn-success"
            )
        return ui.div()
    
   
    @render.text
    def unsaved_changes_alert():
        if not input.autosave_enabled() and changes_unsaved.get():
            return "⚠️ You have unsaved changes"
        return ""
    
    
app = App(app_ui, server)