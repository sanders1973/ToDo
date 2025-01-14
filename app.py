from shiny import App, reactive, render, ui
import json
import base64
import requests
import os

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

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.accordion(
            ui.accordion_panel(
                "Settings",
                ui.output_text("online_status"),
                ui.input_dark_mode(id=None, mode="dark"),
                ui.input_switch("autosave_enabled", "Enable GitHub Auto-save", value=True),
                
            ),
            id="settings_accordion",
            open=False  # This makes it start collapsed
        ),
        
        ui.input_text("task", "Enter Task"),
        ui.input_text_area("description", "Enter Description", height="100px"),  # Changed this line
        ui.input_action_button("add", "Add Task", class_="btn-primary"),
        ui.output_text("unsaved_changes_alert"),
        ui.output_ui("manual_save_button"),
        # ui.hr(),
      #  ui.h4("Manage Tasks"),
        ui.output_ui("task_selector"),
      
       # ui.hr(),
      #  ui.h4("Save to GitHub"),
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
        
      #  ui.hr(),
      #  ui.h4("List Settings"),
        ui.input_action_button("edit_list_names", "Edit List Names", class_="btn-secondary"),
        ui.output_ui("list_name_controls"),
        width=350
    ),

    ui.accordion(
        ui.accordion_panel(
            "Working List (for adding/editing)",
            ui.input_radio_buttons(
                "active_list",
                "",  # Removed the label since it's now in the panel header
                LIST_NAMES,
                inline=True
            ),
        ),
        open=True,  # This makes it start collapsed
        id="working_list_accordion",
    ),
    
    ui.output_ui("edit_controls"),
    ui.output_ui("move_controls"),
  
   ui.card(
        ui.accordion(
            ui.accordion_panel(
                "Select Lists to Display",
                ui.input_checkbox_group(
                    "display_lists",
                    "",  # Removed label since it's now in the panel header
                    LIST_NAMES,
                    selected=["list1"],
                    inline=True
                )
            ),
            open=True,  # Makes it start expanded
            id="display_lists_accordion"
        ),
        ui.output_ui("task_lists_display")
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
            
            current_list["tasks"].append(input.task())
            current_list["descriptions"].append(input.description())
            
            lists_data.set(current_data)
            changes_unsaved.set(True)  # Add this line
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

    
    @render.ui
    def move_controls():
        if not input.selected_tasks():
            return ui.div()  # Return empty div without a card when no tasks selected
            
        current_list_id = input.active_list()
        move_options = {k: v for k, v in LIST_NAMES.items() if k != current_list_id}
        
        return ui.card(
            ui.div(
                ui.div(
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
                    ),
                    style="display: flex; align-items: center; gap: 0;"
                )
            ),
            style="margin-bottom: 0;"
        )

    @render.ui
    def edit_controls():
        if not input.selected_tasks():
            return ui.div()  # Return empty div without a card when no tasks selected
        
        # Show controls based on selection
        if len(input.selected_tasks()) == 1:
            # Single item selected - show all controls
            if editing.get():
                # Show edit form
                task_idx = int(input.selected_tasks()[0]) - 1
                current_list = get_current_list()
                
                return ui.card(  # Now wrap in card only when there's content
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
                        ui.input_action_button("save_edit", "Save", class_="btn-success"),
                        ui.input_action_button("cancel_edit", "Cancel", class_="btn-secondary"),
                        style="display: flex; gap: 10px;"
                    )
                )
            else:
                # Show action buttons for single selection
                return ui.card(  # Now wrap in card only when there's content
                    ui.div(
                        ui.input_action_button("delete_task", "Delete Task", class_="btn-danger"),
                        ui.input_action_button("start_edit", "Edit Task", class_="btn-warning"),
                        ui.input_action_button("move_up", "↑ Move Up", class_="btn-primary"),
                        ui.input_action_button("move_down", "↓ Move Down", class_="btn-primary"),
                        style="display: flex; gap: 10px; flex-wrap: wrap;"
                    )
                )
        else:
            # Multiple items selected - only show delete button
            return ui.card(  # Now wrap in card only when there's content
                ui.div(
                    ui.input_action_button("delete_task", "Delete Selected Tasks", class_="btn-danger"),
                    style="display: flex; gap: 10px;"
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

        # Online save logic continues as before...
        path = "ToDoList.txt"
        try:
            # Prepare the data
            data = lists_data.get()
            formatted_data = ""
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

            # Check if file exists
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

        path = "ToDoList.txt"
        try:
            # Prepare the data
            data = lists_data.get()
            formatted_data = ""
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

            # Check if file exists
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    # File exists, get the SHA
                    sha = response.json()["sha"]
                else:
                    sha = None
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
            else:
                github_status.set(f"Error saving to GitHub: {response.status_code}")

        except Exception as e:
            github_status.set(f"Error: {str(e)}")

    @reactive.effect
    @reactive.event(input.save_github)
    def save_to_github():
        path= "ToDoList.txt"
        if not input.github_token() or not input.github_repo():
            github_status.set("Please fill in all GitHub fields")
            return
    
        try:
            # Prepare the data
            data = lists_data.get()
            formatted_data = ""
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
    
            # Check if file exists
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
                changes_unsaved.set(False)  # Reset the unsaved changes flag
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

    @reactive.effect
    @reactive.event(input.load_github)      
    def load_from_github():        
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
                github_status.set("Successfully loaded from GitHub!")
            else:
                github_status.set(f"Error loading from GitHub: {response.status_code}")

        except Exception as e:
            github_status.set(f"Error loading: {str(e)}")
 
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
