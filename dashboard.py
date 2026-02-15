import tkinter as tk
from tkinter import messagebox

# Create main window
root = tk.Tk()
root.title("Simple Dashboard")
root.geometry("500x400")
root.configure(bg="#f0f0f0")

# Title Label
title = tk.Label(root, text="My Dashboard", font=("Arial", 20, "bold"), bg="#f0f0f0")
title.pack(pady=20)

# Function for button click
def show_message():
    messagebox.showinfo("Info", "Button Clicked!")

# Buttons
btn1 = tk.Button(root, text="Home", width=15, height=2)
btn1.pack(pady=10)

btn2 = tk.Button(root, text="Profile", width=15, height=2)
btn2.pack(pady=10)

btn3 = tk.Button(root, text="Settings", width=15, height=2)
btn3.pack(pady=10)

btn4 = tk.Button(root, text="Click Me", width=15, height=2, command=show_message)
btn4.pack(pady=10)

# Run app
root.mainloop()
