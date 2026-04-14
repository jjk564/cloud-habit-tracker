import os
import datetime
import flet as ft
from supabase import create_client, Client
from dotenv import load_dotenv

# Load the hidden keys from the .env file
load_dotenv()
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
        self.load_from_cloud()

    def load_from_cloud(self):
        """Fetches all habits from Supabase."""
        response = self.supabase.table("habits").select("*").execute()
        # Convert list of rows into a dictionary for our UI
        self.my_habits = {row['habit_name']: row['completed_dates'] for row in response.data}

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
            # SQL Logic: Add today's date to the array IF it's not already there
            self.supabase.rpc('add_date_to_habit', 
                              {'h_name': habit_name, 'new_date': self.today}).execute()
        
        self.load_from_cloud()
        return f"Logged {habit_name} for today!"
    
    def undo_today(self, habit_name):
        habit_name = habit_name.lower()
        self.supabase.rpc('remove_date_from_habit', 
                          {'h_name': habit_name, 'bad_date': self.today}).execute()
        self.load_from_cloud()
# ==========================================
# 2. THE FLET FRONTEND
# ==========================================
def main(page: ft.Page):
    page.title = "Cloud Habit Tracker"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 800
    
    # Initialize Tracker
    tracker = HabitTracker()

    def show_notification(message):
        try:
            # The new way Flet handles popups
            page.open(ft.SnackBar(ft.Text(message))) 
        except AttributeError:
            # The old way, just in case
            page.snack_bar = ft.SnackBar(ft.Text(message), open=True)
            page.update()

    log_list = ft.Column(spacing=10)
    report_list = ft.Column(spacing=5)
    
    # Keep track of habits skipped during this app session
    skipped_habits = set()

    def process_log(habit_name, status):
        if status:
            msg = tracker.log_today(habit_name, True)
            if habit_name in skipped_habits:
                skipped_habits.remove(habit_name)
        else:
            skipped_habits.add(habit_name)
            msg = f"Skipped {habit_name.title()} for today."
            
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
            is_skipped_today = habit in skipped_habits

            # The new Dynamic UI Logic with the Pencil (EDIT) icon
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
        page.update()

    # Settings UI Elements
    new_habit_input = ft.TextField(label="New Habit", expand=True)
    remove_dropdown = ft.Dropdown(label="Remove Habit", expand=True)

    def update_dropdowns():
        remove_dropdown.options = [ft.dropdown.Option(h.title()) for h in tracker.my_habits.keys()]

    def ui_add(e):
        show_notification(tracker.add_habit(new_habit_input.value))
        new_habit_input.value = ""
        update_dashboard()

    def ui_remove(e):
        if remove_dropdown.value:
            show_notification(tracker.remove_habit(remove_dropdown.value))
            update_dashboard()

    # Layout
    dashboard_view = ft.Container(padding=20, content=ft.Column([
        ft.Text("Cloud Dashboard", size=22, weight="bold"),
        ft.Divider(), log_list, ft.Divider(), report_list
    ], scroll=ft.ScrollMode.AUTO))

    manage_view = ft.Container(padding=20, content=ft.Column([
        ft.Text("Manage Habits", size=22, weight="bold"),
        ft.Row([new_habit_input, ft.Button("Add", on_click=ui_add)]),
        ft.Row([remove_dropdown, ft.Button("Remove", on_click=ui_remove, color="red")]),
    ], scroll=ft.ScrollMode.AUTO))

    # The Modern Flet Tabbar Layout
    page.add(
        ft.Tabs(
            selected_index=0,
            length=2,
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label="Dashboard", icon="dashboard"),
                            ft.Tab(label="Manage", icon="settings")
                        ]
                    ),
                    ft.TabBarView(
                        expand=True,
                        controls=[
                            dashboard_view,
                            manage_view
                        ]
                    )
                ]
            )
        )
    )
    
    update_dashboard()

if __name__ == "__main__":
    ft.run(main)