import os
import datetime
import calendar    # <--- Our new built-in math tool
import flet as ft
from supabase import create_client, Client

# ==========================================
# CONFIGURATION - PASTE YOUR KEYS HERE
# ==========================================
SUPABASE_URL = "https://rjqbdmhhczygddushtwq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqcWJkbWhoY3p5Z2RkdXNodHdxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYwOTc5NjYsImV4cCI6MjA5MTY3Mzk2Nn0.xjDhjonWu56mLDEk0GZ4DclCmLyNc272NJQoZWbLLz0"

# ==========================================
# 1. THE CLOUD BACKEND (Supabase)
# ==========================================
class HabitTracker:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.today = str(datetime.date.today())
        self.my_habits = {}
        self.my_skipped = {}
        # REMOVED: self.load_from_cloud()

    def load_from_cloud(self):
        """Fetches all habits from Supabase."""
        response = self.supabase.table("habits").select("*").execute()
        # Grab both completions AND skips from the database
        self.my_habits = {row['habit_name']: row.get('completed_dates') or [] for row in response.data}
        self.my_skipped = {row['habit_name']: row.get('skipped_dates') or [] for row in response.data}
    
    def register(self, email, password):
        try:
            self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            return "Registration successful! You can now log in."
        except Exception as e:
            return f"Error: {str(e)}"

    def login(self, email, password):
        try:
            # Capture the response from Supabase!
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            self.load_from_cloud()
            
            # Return True AND the actual token!
            return True, response.session.refresh_token
            
        except Exception as e:
            return False, f"Login failed. Check your password."

    def logout(self):
        # Tell the cloud to kill the session
        self.supabase.auth.sign_out()
        # Wipe the local dictionaries so no data is left behind
        self.my_habits.clear()
        self.my_skipped.clear()

    def _time_cop(self):
        """Cloud version: Compares last entry date to today."""
        # For a simple version, we'll keep this logic local-first 
        # but you can later expand this to fill missing SQL rows!
        return "Cloud Sync Active."

    def add_habit(self, habit_name):
        habit_name = habit_name.lower().strip()
        if not habit_name: return "Name cannot be empty."
        
        try:
            self.supabase.table("habits").insert({"habit_name": habit_name}).execute()
            self.load_from_cloud() # Refresh
            return f"Awesome! '{habit_name}' is now in the cloud."
        except Exception as e:
            return f"Error: Habit might already exist!"

    def remove_habit(self, habit_name):
        habit_name = habit_name.lower()
        self.supabase.table("habits").delete().eq("habit_name", habit_name).execute()
        self.load_from_cloud()
        return f"Poof! '{habit_name}' deleted from cloud."

    def log_today(self, habit_name, completed: bool):
        habit_name = habit_name.lower()
        if completed:
            # Add to the completed array
            self.supabase.rpc('add_date_to_habit', 
                              {'h_name': habit_name, 'new_date': self.today}).execute()
            msg = f"Logged {habit_name} for today!"
        else:
            # NEW: Add to the skipped array using your new SQL function!
            self.supabase.rpc('add_skip_date_to_habit', 
                              {'h_name': habit_name, 'skip_date': self.today}).execute()
            msg = f"Skipped {habit_name} for today."
        
        self.load_from_cloud() # Refresh local data with the new cloud state
        return msg
    
    def undo_today(self, habit_name):
        habit_name = habit_name.lower()
        self.supabase.rpc('remove_date_from_habit', 
                          {'h_name': habit_name, 'bad_date': self.today}).execute()
        self.load_from_cloud()

# ==========================================
# 2. THE FLET FRONTEND
# ==========================================
def main(page: ft.Page):
    page.title = "Tabit"
    page.theme_mode = ft.ThemeMode.DARK
   
    # Initialize Tracker
    tracker = HabitTracker()

    def show_notification(message):
        try:
            page.open(ft.SnackBar(ft.Text(message))) 
        except AttributeError:
            page.snack_bar = ft.SnackBar(ft.Text(message), open=True)
            page.update()

    log_list = ft.Column(spacing=10)
    report_list = ft.Column(spacing=5)
    
    skipped_habits = set()

    def process_log(habit_name, status):
        # Pass the True/False status straight to the cloud backend
        msg = tracker.log_today(habit_name, status)
        
        show_notification(msg)
        update_dashboard()

    def undo_log(habit_name):
        if habit_name in skipped_habits:
            skipped_habits.remove(habit_name)
            msg = f"Undo skip for {habit_name.title()}."
        else:
            tracker.undo_today(habit_name)
            msg = f"Removed completion for {habit_name.title()}."
            
        show_notification(msg)
        update_dashboard()

    def update_dashboard():
        log_list.controls.clear()
        report_list.controls.clear()
        
        if not tracker.my_habits:
            log_list.controls.append(ft.Text("No habits found in cloud.", italic=True))

        for habit, dates in tracker.my_habits.items():
            is_done_today = tracker.today in dates
            
            # THE CHANGED LINE: Now reading from the cloud dictionary!
            is_skipped_today = tracker.today in tracker.my_skipped.get(habit, [])

            if is_done_today:
                status_ui = ft.Row([
                    ft.Text("Done for today! 🎉", color=ft.Colors.GREEN, weight="bold"),
                    ft.IconButton(icon=ft.Icons.EDIT, tooltip="Edit Entry", 
                                  on_click=lambda e, h=habit: undo_log(h))
                ])
            elif is_skipped_today:
                status_ui = ft.Row([
                    ft.Text("Skipped for today.", color=ft.Colors.GREY, italic=True),
                    ft.IconButton(icon=ft.Icons.EDIT, tooltip="Edit Entry", 
                                  on_click=lambda e, h=habit: undo_log(h))
                ])
            else:
                status_ui = ft.Row([
                    ft.IconButton(icon=ft.Icons.CHECK_CIRCLE, icon_color=ft.Colors.GREEN, 
                                  on_click=lambda e, h=habit: process_log(h, True)),
                    ft.IconButton(icon=ft.Icons.CANCEL, icon_color=ft.Colors.RED, 
                                  on_click=lambda e, h=habit: process_log(h, False)),
                ])

            log_list.controls.append(
                ft.Row([
                    ft.Text(habit.title(), size=18, weight="bold", expand=True),
                    status_ui 
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )
            
            report_list.controls.append(ft.Text(f"• {habit.title()}: {len(dates)} total completions"))
        
        update_dropdowns()
        update_calendar() # Refresh the calendar when data changes
        page.update()

   # --- NEW CALENDAR LOGIC ---
    calendar_container = ft.Column(spacing=10)
    
    # Updated 'on_change' to 'on_select' to satisfy the newest Flet version!
    cal_habit_dropdown = ft.Dropdown(label="Select Habit to View", expand=True, on_select=lambda e: update_calendar())

    def update_calendar():
        calendar_container.controls.clear()
        
        if not cal_habit_dropdown.value or cal_habit_dropdown.value not in tracker.my_habits:
            calendar_container.controls.append(ft.Text("Select a habit from the dropdown to view your monthly streak.", italic=True))
            page.update()
            return

        selected_habit = cal_habit_dropdown.value
        completed_dates = tracker.my_habits[selected_habit]

        now = datetime.date.today()
        current_year = now.year
        current_month = now.month
        month_name = calendar.month_name[current_month]

        # 1. Add Month Header (Bypassing Flet Enum with pure string "center")
        calendar_container.controls.append(
            ft.Text(f"{month_name} {current_year}", size=20, weight="bold", text_align="center")
        )

        # 2. Add Days of the Week Header (Bypassing Flet Enum with pure string "spaceBetween")
        days_row = ft.Row(alignment="spaceBetween")
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
             days_row.controls.append(
                 ft.Container(content=ft.Text(day, weight="bold", size=12, text_align="center"), width=40)
             )
        calendar_container.controls.append(days_row)
        calendar_container.controls.append(ft.Divider())

        # 3. Build the Grid
        month_cal = calendar.monthcalendar(current_year, current_month)
        for week in month_cal:
            # Bypassing Flet Enum again
            week_row = ft.Row(alignment="spaceBetween")
            for day in week:
                if day == 0: # Empty days before the 1st of the month
                    week_row.controls.append(ft.Container(width=40, height=40))
                else:
                    # Format day to match Supabase layout (YYYY-MM-DD)
                    date_str = f"{current_year}-{current_month:02d}-{day:02d}"
                    is_completed = date_str in completed_dates

                    # Visuals: Bypassing Flet Color Enums with pure strings
                    bg_color = "green" if is_completed else "#333333"
                    
                    day_box = ft.Container(
                        content=ft.Text(str(day), text_align="center"),
                        width=40,
                        height=40,
                        bgcolor=bg_color,
                        border_radius=5
                    )
                    week_row.controls.append(day_box)
            calendar_container.controls.append(week_row)
            
        # Push the new UI elements to the screen!
        page.update()

    # --- SETTINGS / MANAGE LOGIC ---
    new_habit_input = ft.TextField(label="New Habit", expand=True)
    remove_dropdown = ft.Dropdown(label="Remove Habit", expand=True)

    def update_dropdowns():
        # Explicitly defining 'key' and 'text' fixes the collision!
        options = [ft.dropdown.Option(key=h, text=h.title()) for h in tracker.my_habits.keys()]
        
        remove_dropdown.options = options
        
        # Keep calendar dropdown selection if it still exists
        current_selection = cal_habit_dropdown.value
        cal_habit_dropdown.options = options
        if current_selection not in tracker.my_habits:
            cal_habit_dropdown.value = None

    def ui_add(e):
        show_notification(tracker.add_habit(new_habit_input.value))
        new_habit_input.value = ""
        cal_habit_dropdown.value = new_habit_input.value.lower() # Auto-select the new habit
        update_dashboard()

    def ui_remove(e):
        if remove_dropdown.value:
            show_notification(tracker.remove_habit(remove_dropdown.value))
            remove_dropdown.value = None
            update_dashboard()

    # --- LAYOUTS ---
    dashboard_view = ft.Container(padding=20, content=ft.Column([
        ft.Text("Tabit Dashboard", size=22, weight="bold"),
        ft.Divider(), log_list, ft.Divider(), report_list
    ], scroll=ft.ScrollMode.AUTO))

    # New Calendar View
    calendar_view = ft.Container(padding=20, content=ft.Column([
        ft.Text("Progress Calendar", size=22, weight="bold"),
        cal_habit_dropdown,
        ft.Divider(), 
        calendar_container
    ], scroll=ft.ScrollMode.AUTO))

    # 1. Define the function first
    def handle_logout(e):
        # FIX: Point to the tracker's supabase connection!
        tracker.supabase.auth.sign_out()
        
        page.client_storage.remove("tabit_refresh_token")
        
        page.controls.clear()
        page.add(login_view)
        page.update()
        show_notification("Successfully logged out!")

    # 2. Then build the UI that uses it
    manage_view = ft.Container(padding=20, content=ft.Column([
        ft.Text("Manage Habits", size=22, weight="bold"),
        ft.Row([new_habit_input, ft.Button("Add", on_click=ui_add)]),
        ft.Row([remove_dropdown, ft.Button("Remove", on_click=ui_remove, color="red")]),
        ft.ElevatedButton("Logout", icon=ft.Icons.LOGOUT, color="red", on_click=handle_logout)
    ], scroll=ft.ScrollMode.AUTO))

# --- AUTHENTICATION UI ---
    email_input = ft.TextField(label="Email", width=300)
    password_input = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)

    def handle_login(e):
        # 'result' will either be the token (if success) or an error message (if fail)
        success, result = tracker.login(email_input.value, password_input.value)

        if success:
            # Save the token straight to the phone!
            page.client_storage.set("tabit_refresh_token", result)
            show_dashboard() 
            show_notification("Login successful! Token saved to phone.") 
        else:
            show_notification(result)

    def handle_register(e):
        print("--- REGISTER BUTTON CLICKED ---")
        print(f"Attempting to register: {email_input.value}")
        
        msg = tracker.register(email_input.value, password_input.value)
        
        print(f"Supabase responded with: {msg}")
        show_notification(msg)
        page.update()

    login_view = ft.SafeArea(
        expand=True,
        content=ft.Container(
            alignment=ft.Alignment.CENTER, # <-- Capital 'A', Capital 'CENTER'!
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=50),
                    ft.Text("Tabit", size=30, weight="bold"),
                    email_input,
                    password_input,
                    ft.ElevatedButton("Login", on_click=handle_login, width=300),
                    ft.TextButton("Create Account", on_click=handle_register)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
    )

    def show_dashboard():
        page.controls.clear() # Wipe the login screen away
        
        # The Modern Flet Tabbar Layout (Now with 3 tabs!)
        page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Tabs(
                    selected_index=0,
                    length=3,
                    expand=True,
                    content=ft.Column(
                        expand=True,
                        controls=[
                            ft.TabBar(
                                tabs=[
                                    ft.Tab(label="Dashboard", icon=ft.Icons.DASHBOARD),
                                    ft.Tab(label="Calendar", icon=ft.Icons.CALENDAR_MONTH),
                                    ft.Tab(label="Manage", icon=ft.Icons.SETTINGS)
                                ]
                            ),
                            ft.TabBarView(
                                expand=True,
                                controls=[
                                    dashboard_view,
                                    calendar_view,
                                    manage_view
                                ]
                            )
                        ]
                    )
                )
            )
        )
        
        update_dashboard()

   # --- THE STARTUP CHECK ---
    saved_token = page.client_storage.get("tabit_refresh_token")
    
    if saved_token:
        try:
            response = tracker.supabase.auth.refresh_session(saved_token)
            page.client_storage.set("tabit_refresh_token", response.session.refresh_token)
            
            # ADD THIS LINE: Now that we are verified, download the data!
            tracker.load_from_cloud()
            
            show_dashboard() 
            show_notification("Silently logged in!")
            
        except Exception as err:
            page.client_storage.remove("tabit_refresh_token")
            page.add(login_view)
            show_notification("Session expired. Please log in again.")
    else:
        page.add(login_view)
        
    page.update()

if __name__ == "__main__":
    ft.run(main)