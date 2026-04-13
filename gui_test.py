import customtkinter as ctk
import json
import os

# --- THE BULLETPROOF PATH UPGRADE ---
# 1. Find exactly where this Python script lives on your hard drive
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Force the database to ALWAYS save right next to the script
FILE_NAME = os.path.join(BASE_DIR, "habits.json")
# ------------------------------------

# ==========================================
# 0. THE MEMORY LOAD
# ==========================================
if os.path.exists(FILE_NAME):
    with open(FILE_NAME, "r") as file:
        my_habits = json.load(file)
else:
    my_habits = {}

# ... (The rest of your code stays exactly the same!) ...
# ==========================================
# 1. SETUP THE WINDOW
# ==========================================
ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("400x350")
app.title("Habit Tracker V3 - Prototype")

# ==========================================
# 2. THE EVENT FUNCTIONS
# ==========================================
def add_habit_event():
    # Grab the text and make it lowercase so it matches our old format
    habit_name = habit_entry.get().lower() 
    
    if habit_name == "":
        result_label.configure(text="Error: Please type a habit first!", text_color="red")
        
    elif habit_name in my_habits:
        result_label.configure(text=f"Error: '{habit_name}' already exists!", text_color="orange")
        
    else:
        # 1. Add it to the dictionary
        my_habits[habit_name] = []
        
        # 2. Save it permanently to the hard drive!
        with open(FILE_NAME, "w") as file:
            json.dump(my_habits, file)
            
        # 3. Update the UI to show success
        result_label.configure(text=f"Success! '{habit_name}' added to database.", text_color="green")
        habit_entry.delete(0, 'end') 

# ==========================================
# 3. DRAWING THE WIDGETS
# ==========================================
title_label = ctk.CTkLabel(app, text="My Habit Tracker", font=("Arial", 24, "bold"))
title_label.pack(pady=20)

habit_entry = ctk.CTkEntry(app, width=200, placeholder_text="Type a new habit...")
habit_entry.pack(pady=10)

add_button = ctk.CTkButton(app, text="Add Habit", command=add_habit_event)
add_button.pack(pady=10)

result_label = ctk.CTkLabel(app, text="")
result_label.pack(pady=20)

# ==========================================
# 4. THE EVENT LOOP
# ==========================================
app.mainloop()