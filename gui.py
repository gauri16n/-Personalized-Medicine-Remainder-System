import tkinter as tk
from tkinter import messagebox, simpledialog, font
import requests
import time

API_URL = "http://127.0.0.1:5001/api"
# Create a session object to persist cookies (and login status) across requests
api_session = requests.Session()

class AppState:
    """A simple class to hold the application's state."""
    def __init__(self):
        self.user_id = None
        self.user_name = None

app_state = AppState()

class MedicationReminderApp(tk.Tk):
    """Main application window."""
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("Medication Reminder")
        self.geometry("800x600")

        self.title_font = font.Font(family='Helvetica', size=18, weight="bold")
        self.default_font = font.Font(family='Helvetica', size=12)
        self.button_font = font.Font(family='Helvetica', size=12, weight="bold")

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (LoginPage, RegisterPage, MainPage, ManageMedicationsPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, 'start_background_tasks'):
            frame.start_background_tasks()
        else:
            if "MainPage" in self.frames and self.frames["MainPage"].after_id:
                self.after_cancel(self.frames["MainPage"].after_id)

class LoginPage(tk.Frame):
    """Login Page UI."""
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        label = tk.Label(self, text="Login", font=controller.title_font)
        label.pack(pady=20)

        tk.Label(self, text="Username", font=controller.default_font).pack(pady=(10,0))
        self.username_entry = tk.Entry(self, font=controller.default_font, width=30)
        self.username_entry.pack(pady=5)

        tk.Label(self, text="Password", font=controller.default_font).pack(pady=(10,0))
        self.password_entry = tk.Entry(self, show="*", font=controller.default_font, width=30)
        self.password_entry.pack(pady=5)

        login_button = tk.Button(self, text="Login", font=controller.button_font, command=self.login, width=20, height=2)
        login_button.pack(pady=20)

        register_button = tk.Button(self, text="Go to Register", font=controller.default_font, command=lambda: controller.show_frame("RegisterPage"))
        register_button.pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Username and password cannot be empty.")
            return

        try:
            response = api_session.post(f"{API_URL}/login", json={"name": username, "password": password})
            if response.status_code == 200:
                data = response.json()
                app_state.user_id = data['user_id']
                app_state.user_name = data['name']
                messagebox.showinfo("Success", "Login successful!")
                self.username_entry.delete(0, 'end')
                self.password_entry.delete(0, 'end')
                self.controller.show_frame("MainPage")
            else:
                messagebox.showerror("Login Failed", response.json().get("error", "An unknown error occurred"))
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to the server. Is it running?")
        except requests.exceptions.JSONDecodeError:
            messagebox.showerror("Server Error", "The server sent an invalid response. Please check the backend terminal for errors.")

class RegisterPage(tk.Frame):
    """Registration Page UI."""
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        label = tk.Label(self, text="Register New Patient", font=controller.title_font)
        label.pack(pady=20)

        fields = {
            "Username": "username_entry", "Email": "email_entry", "Password": "password_entry", "Age": "age_entry",
            "Your Contact Number (for SMS alerts)": "user_contact_entry", "Close Contact's Name": "cc_name_entry",
            "Close Contact's Number": "cc_contact_entry"
        }

        for text, entry_name in fields.items():
            tk.Label(self, text=text, font=controller.default_font).pack(pady=(5,0))
            entry = tk.Entry(self, font=controller.default_font, width=40)
            if "Password" in text: entry.config(show="*")
            setattr(self, entry_name, entry)
            entry.pack(pady=2)

        register_button = tk.Button(self, text="Register", font=controller.button_font, command=self.register, width=20, height=2)
        register_button.pack(pady=20)

        login_button = tk.Button(self, text="Go to Login", font=controller.default_font, command=lambda: controller.show_frame("LoginPage"))
        login_button.pack()

    def register(self):
        data = {
            "name": self.username_entry.get(), "email": self.email_entry.get(), "password": self.password_entry.get(),
            "age": self.age_entry.get(), "user_contact": self.user_contact_entry.get(),
            "cc_name": self.cc_name_entry.get(), "cc_contact": self.cc_contact_entry.get()
        }
        # Check that all fields are filled
        if not all(data.values()):
            messagebox.showerror("Error", "All fields are required.")
            return

        try:
            response = api_session.post(f"{API_URL}/register", json=data)
            if response.status_code == 201:
                messagebox.showinfo("Success", "Registration successful! Please login.")
                self.controller.show_frame("LoginPage")
            else:
                messagebox.showerror("Registration Failed", response.json().get("error", "An unknown error occurred"))
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to the server.")
        except requests.exceptions.JSONDecodeError:
            messagebox.showerror("Server Error", "The server sent an invalid response. Check the backend terminal for errors.")

class MainPage(tk.Frame):
    """Main application page after login."""
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.after_id = None

        self.welcome_label = tk.Label(self, text="", font=controller.title_font)
        self.welcome_label.pack(pady=20)

        controls_frame = tk.Frame(self)
        controls_frame.pack(pady=10)

        add_med_button = tk.Button(controls_frame, text="Add New Medication", font=controller.button_font, command=self.add_medication)
        add_med_button.pack(side=tk.LEFT, padx=10)

        manage_meds_button = tk.Button(controls_frame, text="Manage Medications", font=controller.button_font, command=lambda: controller.show_frame("ManageMedicationsPage"))
        manage_meds_button.pack(side=tk.LEFT, padx=10)

        refresh_button = tk.Button(controls_frame, text="Refresh Schedule", font=controller.button_font, command=self.refresh_schedule)
        refresh_button.pack(side=tk.LEFT, padx=10)

        logout_button = tk.Button(controls_frame, text="Logout", font=controller.button_font, command=self.logout)
        logout_button.pack(side=tk.LEFT, padx=10)

        self.schedule_frame = tk.Frame(self, borderwidth=2, relief="sunken")
        self.schedule_frame.pack(fill="both", expand=True, padx=20, pady=10)

    def start_background_tasks(self):
        self.welcome_label.config(text=f"Welcome, {app_state.user_name}!")
        self.refresh_schedule()
        self.check_for_missed_doses()

    def refresh_schedule(self):
        if not app_state.user_id: return
        for widget in self.schedule_frame.winfo_children(): widget.destroy()

        try:
            response = api_session.get(f"{API_URL}/schedule")
            if response.status_code == 200:
                schedule = response.json().get("schedule", [])
                if not schedule:
                    tk.Label(self.schedule_frame, text="No medications scheduled for today.", font=self.controller.default_font).pack(pady=20)
                    return
                for item in schedule: self.display_schedule_item(item)
            else:
                try:
                    messagebox.showerror("Error", f"Failed to fetch schedule: {response.json().get('error')}")
                except requests.exceptions.JSONDecodeError:
                    messagebox.showerror("Server Error", "The server sent an invalid response. Check the backend terminal for errors.")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to the server.")


    def display_schedule_item(self, item):
        item_frame = tk.Frame(self.schedule_frame, pady=10)
        item_frame.pack(fill='x', padx=10)

        time_obj = time.strptime(item['scheduled_time'], '%H:%M:%S')
        display_time = time.strftime('%I:%M %p', time_obj)
        info_text = f"{display_time} - {item['medicine_name']} ({item['dosage']})"
        tk.Label(item_frame, text=info_text, font=self.controller.default_font).pack(side=tk.LEFT)

        status_label = tk.Label(item_frame, text=item['status'], font=self.controller.default_font, width=10)
        status_label.pack(side=tk.RIGHT, padx=10)

        if item['status'] == 'PENDING':
            status_label.config(fg="orange")
            confirm_button = tk.Button(item_frame, text="I have taken this", font=self.controller.button_font,
                                       command=lambda dose_id=item['dose_id']: self.confirm_dose(dose_id))
            confirm_button.pack(side=tk.RIGHT)
        elif item['status'] == 'TAKEN': status_label.config(fg="green")
        elif item['status'] == 'MISSED': status_label.config(fg="red")

    def confirm_dose(self, dose_id):
        try:
            response = api_session.post(f"{API_URL}/confirm_dose", json={"dose_id": dose_id})
            if response.status_code == 200:
                self.refresh_schedule()
            else:
                try:
                    messagebox.showerror("Error", f"Failed to confirm dose: {response.json().get('error')}")
                except requests.exceptions.JSONDecodeError:
                    messagebox.showerror("Server Error", "The server sent an invalid response. Check the backend terminal for errors.")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to the server.")


    def add_medication(self):
        dialog = AddMedicationDialog(self)
        if dialog.result:
            try:
                response = api_session.post(f"{API_URL}/add_medication", json=dialog.result)
                if response.status_code == 200:
                    messagebox.showinfo("Success", "Medication added successfully.")
                    self.refresh_schedule()
                else:
                    try:
                        messagebox.showerror("Error", f"Failed to add medication: {response.json().get('error')}")
                    except requests.exceptions.JSONDecodeError:
                        messagebox.showerror("Server Error", "The server sent an invalid response. Check the backend terminal for errors.")
            except requests.exceptions.ConnectionError:
                messagebox.showerror("Connection Error", "Could not connect to the server.")


    def check_for_missed_doses(self):
        if app_state.user_id:
            try:
                response = api_session.get(f"{API_URL}/check_missed_doses")
                if response.status_code == 200 and response.json().get("missed_alerts"):
                    self.refresh_schedule()
                    messagebox.showwarning("Missed Dose Alert!", "\n".join(response.json()["missed_alerts"]))
            except requests.exceptions.ConnectionError:
                print("Connection error while checking for missed doses.")
        self.after_id = self.after(60000, self.check_for_missed_doses)



    def logout(self):
        app_state.user_id = None
        app_state.user_name = None
        if self.after_id: self.after_cancel(self.after_id)
        self.after_id = None
        self.controller.show_frame("LoginPage")

class ManageMedicationsPage(tk.Frame):
    """Page to view and delete all medications."""
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        label = tk.Label(self, text="Manage Your Medications", font=controller.title_font)
        label.pack(pady=20)

        back_button = tk.Button(self, text="Back to Daily Schedule", font=controller.button_font, command=lambda: controller.show_frame("MainPage"))
        back_button.pack(pady=10)

        self.med_list_frame = tk.Frame(self, borderwidth=2, relief="sunken")
        self.med_list_frame.pack(fill="both", expand=True, padx=20, pady=10)

    def start_background_tasks(self):
        """This is called when the frame is shown."""
        self.load_medications()

    def load_medications(self):
        for widget in self.med_list_frame.winfo_children():
            widget.destroy()

        try:
            response = api_session.get(f"{API_URL}/medications")
            if response.status_code == 200:
                medications = response.json().get("medications", [])
                if not medications:
                    tk.Label(self.med_list_frame, text="You have not added any medications yet.", font=self.controller.default_font).pack(pady=20)
                    return
                for med in medications:
                    self.display_med_item(med)
            else:
                messagebox.showerror("Error", f"Failed to load medications: {response.json().get('error')}")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to the server.")
        except requests.exceptions.JSONDecodeError:
            messagebox.showerror("Server Error", "The server sent an invalid response. Check the backend terminal for errors.")

    def display_med_item(self, med):
        item_frame = tk.Frame(self.med_list_frame, pady=10)
        item_frame.pack(fill='x', padx=10)

        time_obj = time.strptime(med['time_to_take'], '%H:%M:%S')
        display_time = time.strftime('%I:%M %p', time_obj)

        info_text = f"{display_time} - {med['medicine_name']} ({med['dosage']})"
        tk.Label(item_frame, text=info_text, font=self.controller.default_font).pack(side=tk.LEFT, expand=True, fill='x')

        delete_button = tk.Button(item_frame, text="Delete", font=self.controller.button_font, fg="red",
                                  command=lambda med_id=med['id']: self.delete_medication(med_id))
        delete_button.pack(side=tk.RIGHT)

    def delete_medication(self, medication_id):
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this medication? This cannot be undone."):
            return

        try:
            response = api_session.post(f"{API_URL}/delete_medication", json={"medication_id": medication_id})
            if response.status_code == 200:
                messagebox.showinfo("Success", "Medication deleted.")
                self.load_medications() # Refresh the list
            else:
                messagebox.showerror("Error", f"Failed to delete medication: {response.json().get('error')}")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to the server.")

class AddMedicationDialog(simpledialog.Dialog):
    """Dialog to add a new medication."""
    def body(self, master):
        self.title("Add New Medication")
        tk.Label(master, text="Medicine Name:").grid(row=0, sticky="w")
        tk.Label(master, text="Dosage (e.g., 1 pill):").grid(row=1, sticky="w")
        tk.Label(master, text="Time (e.g., 08:30 or 14:00):").grid(row=2, sticky="w")
        self.e1 = tk.Entry(master); self.e2 = tk.Entry(master); self.e3 = tk.Entry(master)
        self.e1.grid(row=0, column=1); self.e2.grid(row=1, column=1); self.e3.grid(row=2, column=1)
        return self.e1

    def apply(self):
        time_str = self.e3.get()
        try:
            time.strptime(time_str, '%H:%M')
        except ValueError:
            messagebox.showerror("Invalid Format", "Please enter the time in HH:MM (24-hour) format.")
            self.result = None
            return
        self.result = {"medicine_name": self.e1.get(), "dosage": self.e2.get(), "time": time_str}

if __name__ == "__main__":
    app = MedicationReminderApp()
    app.mainloop()
