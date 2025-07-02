import pandas as pd
import tkinter as tk
from tkinter import filedialog, ttk, Frame, StringVar, IntVar, Label, Entry, Button, END, W, messagebox, OptionMenu, simpledialog
import time
import datetime
import re
import os
import csv
import matplotlib.pyplot as plt
from matplotlib import animation
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import serial.tools.list_ports

class SerialCommunicator:
    def __init__(self):
        pass
    
    def send(self, port, command):
        try:
            port.write((command + "\n").encode())
        except Exception as e:
            print(e)

    
    def read(self, port):
        try:
            return port.readline().decode("utf-8").strip()
        except Exception as e:
            print(e)


class BatteryLoggerLogic:
    def __init__(self, app, ser):
        self.app = app
        self.ser = ser
        self.first_run = True
        self.new_start = True
        self.data = []
        self.voltage = []
        self.current = []
        self.charge = 0
        self.energy = 0
        self.charge_sum = 0
        self.energy_sum = 0
        self.time = 0
        self.timestamps = []
        self.filename = ""
        self.t1 = 0
        self.t2 = 0
        self.j = 0
        self.end = False
        self.cancel1 = False
        self.cancel2 = False
        self.create_data_dir()
        
        self.savedata = pd.DataFrame(columns=["Time", "Step", "Current", 
                                              "Voltage", "Power", "Charge", 
                                              "Energy", "Current Charge", "Current Energy"])

    def create_data_dir(self):
        if not os.path.exists("data"):
            os.makedirs("data")
    
    def set_values(self):
        voltage = 4
        current = 1.5
        self.set_voltage(voltage)
        self.set_current(current)
        self.set_voltage2(voltage)
        self.set_current2(current)
    
    def stop_plot(self):
        self.send_command(self.serial_port2, ":INP OFF")
        self.send_command(self.serial_port1, "OUT:0")
        self.serial_port1.close()
        self.serial_port2.close()
        print("Ports closed.")
    
    def get_available_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def setup_ports(self):
        self.serial_port1 = None
        self.serial_port2 = None
        ports = self.get_available_ports()
        for port in ports:
            serial_port = serial.Serial(port=port, baudrate=9600, timeout=1)
            self.send_command(serial_port, "*IDN?\n")
            response = self.read_response(serial_port)
            serial_port.close()
            if "KEL" in response:
                print(f"Sink: {response}")
                self.serial_port2 = serial.Serial(port=port, baudrate=9600, timeout=1)
            elif "KWR" in response:
                print(f"Source: {response}")
                self.serial_port1 = serial.Serial(port=port, baudrate=9600, timeout=1)
            else:
                print("unknown")
        if self.serial_port1 is None:
            print("No Source Detected.")
        if self.serial_port2 is None:
            print("No Sink Detected.")

    def send_command(self, serial_port, command):
        if serial_port:
            try:
                ser.send(serial_port, command)
            except Exception as e:
                print(f"Error while sending data: {e}")

    def read_response(self, serial_port):
        if serial_port:
            try:
                return ser.read(serial_port)
            except Exception as e:
                print(f"Error while reading data: {e}")
        return None

    def animate(self, i):
        if not self.end:
            self.animate1(i)

    def animate1(self, i):
        is_load_mode = self.mode == "Charging"
        self.get_this_step()
        if self.end:
            self.stop_plot()
            self.app.ani.event_source.stop()
            return

        print("-------------------------------------")
        print(f"Desired Value: {self.desired} with {self.desired_value}")
        if i - self.j == 3:
            if not is_load_mode:
                if self.desired == "Voltage":
                    self.set_voltage2(f"{self.desired_value[:-1]}")
                if self.desired == "Current":
                    self.set_current2(f"{self.desired_value[:-1]}")
                if self.desired == "Power":
                    self.set_power2(f"{self.desired_value[:-1]}")
                if self.desired == "Resistance":
                    self.set_resistance2(f"{self.desired_value[:-1]}")
                self.set_voltage(0)
                self.set_current(0)
                self.send_command(self.serial_port1, "OUT:1")
                self.send_command(self.serial_port2, ":INP ON")
            else:
                if self.desired == "Voltage":
                    self.set_voltage(f"{self.desired_value[:-1]}")
                if self.desired == "Current":
                    self.set_current(f"{self.desired_value[:-1]}")
                self.set_voltage2(0)
                self.set_current2(0)
                self.send_command(self.serial_port2, ":INP ON")
                self.send_command(self.serial_port1, "OUT:1")
        
        current_str = self.get_current1() if is_load_mode else self.get_current2()[:-1]
        voltage_str = self.get_voltage1() if not is_load_mode else self.get_voltage2()[:-1]
        if current_str is not None and voltage_str is not None:
            current = float(current_str)
            voltage = float(voltage_str)
        else:
            current = 0.0
            voltage = 0.0

        now = datetime.datetime.now()
        self.time = now.timestamp() - self.start_time.timestamp()
        print(f"Time: {self.time}")
        print(f"Voltage: {voltage}V")
        print(f"Current: {current}A")
    
        power = voltage * current
    
        if i - self.j % 2 == 0:
            self.t1 = time.perf_counter()
            self.dt = self.t1 - self.t2
        else:
            self.t2 = time.perf_counter()
            self.dt = self.t2 - self.t1
    
        if i - self.j == 0:
            self.dt = 0
    
        charge = self.dt * current / 3600
        energy = self.dt * power / 3600
    
        self.charge = charge
        self.energy = energy
    
        self.charge_sum += charge
        self.energy_sum += energy
    
        self.timestamps.append(now)
        self.voltage.append(voltage)
        self.current.append(current)
    
        self.timestamps = self.timestamps[-3600:]
        self.voltage = self.voltage[-3600:]
        self.current = self.current[-3600:]
    
        new_data = pd.DataFrame({
            "Time": [self.time],
            "Step": [self.schritt],
            "Current": [current],
            "Voltage": [voltage],
            "Power": [power],
            "Charge Sum": [self.charge_sum],
            "Energy Sum": [self.energy_sum],
            "Charge": [charge],
            "Energy": [energy],
        })
    
        self.savedata = pd.concat([self.savedata, new_data], ignore_index=True)
    
        self.cancel1 = self.check_canc(self.mode, self.canc1, self.canc1w[:-1])
        self.cancel2 = self.check_canc(self.mode, self.canc2, self.canc2w[:-1])
    
        if self.cancel1:
            print(f"{'Charged' if is_load_mode else 'Discharge'}, reached cancel condition 1.")
            self.j = i
        if self.cancel2:
            print(f"{'Charged' if is_load_mode else 'Discharge'}, reached cancel condition 2.")
            self.j = i

        self.app.plot(app.sub1, "voltage", "V", self.timestamps, self.voltage)
        self.app.plot(app.sub2, "current", "A", self.timestamps, self.current)
        self.app.fig.suptitle(self.filename)

    def format_for_csv(self, val):
        return str(val).replace(".", ",")
    
    def get_this_step(self):
        if self.first_run:
            to_do = self.get_step(1)
            self.first_run = False
        else:
            if not self.cancel1 and not self.cancel2:
                to_do = self.get_step(self.schritt)
            if self.cancel1:
                if self.next1 == 0:
                    print("END")
                    self.end = True
                    return
                to_do = self.get_step(self.next1)
                self.cancel1 = False
                self.cancel2 = False
                self.start_time = datetime.datetime.now()
                #self.send_command(self.serial_port1, "OUT:0")
                #self.send_command(self.serial_port2, ":INP OFF")
            if self.cancel2:
                if self.next2 == 0:
                    print("END")
                    self.end = True
                    return
                to_do = self.get_step(self.next2)
                self.cancel1 = False
                self.cancel2 = False
                self.start_time = datetime.datetime.now()
                #self.send_command(self.serial_port1, "OUT:0")
                #self.send_command(self.serial_port2, ":INP OFF")

        self.schritt = to_do[0]
        self.mode = to_do[1]
        self.desired = to_do[2]
        self.desired_value = to_do[3]
        self.canc1 = to_do[4]
        self.canc1w = to_do[5]
        self.next1 = to_do[6]
        self.canc2 = to_do[7]
        self.canc2w = to_do[8]
        self.next2 = to_do[9]

    def do_plot(self):
        date = time.strftime(f"%d%m%y", time.localtime())
        self.filename = simpledialog.askstring("Input", "Name the Plot:")
        self.app.save_step()
        self.start_time = datetime.datetime.now()
        self.get_this_step()
    
        self.cancel1 = self.check_canc(self.mode, self.canc1, self.canc1w[:-1])
        self.cancel2 = self.check_canc(self.mode, self.canc2, self.canc2w[:-1])

        try:
            self.app.run_plot()
        except Exception as e:
            self.app.show_error(e)
            return

    def check_canc(self, load, mode, value):
        value = float(value)
        if load == "Discharge":
            current_str = self.get_current2()[:-1]
            voltage_str = self.get_voltage1()

            if current_str is not None and voltage_str is not None:
                curr = float(current_str[:-1])  # strips A and V
                volt = float(voltage_str[:-1])
            else:
                curr = 0.0
                volt = 0.0
        else:
            current_str = self.get_current1()
            voltage_str = self.get_voltage2()[:-1]

            if current_str is not None and voltage_str is not None:
                curr = float(current_str)
                volt = float(voltage_str)
            else:
                curr = 0.0
                volt = 0.0

        print(load, current_str, voltage_str)

        if mode == "No Condition":
            return False
        if mode == "Min Current":
            print(f"Current {curr}A >= {value}A")
            if curr <= value:
                return True
            else:
                return False
        if mode == "Max Voltage":
            print(f"Umax {volt}V <= {value}V")
            if volt >= value:
                return True
            else:
                return False
        if mode == "Min Voltage":
            print(f"Umin {volt}V >= {value}V")
            if volt <= value:
                return True
            else:
                return False
        if mode == "Time":
            print(f"Time {self.time}s <= {value}s")
            if self.time >= value:
                return True
            else:
                return False
        if mode == "Charge":
            print(f"Charge {self.charge}C <= {value}C")
            if self.charge >= value:
                return True
            else:
                return False
        if mode == "Energy":
            print(f"Energy {self.energy}J <= {value}J")
            if self.energy >= value:
                return True
            else:
                return False
        return False

    def get_step(self, step):
        row_index = self.dataf[self.dataf.iloc[:, 0] == step].index.min()

        if pd.notna(row_index):
            return [int(x) if isinstance(x, (int, float)) and x.is_integer() else x for x in self.dataf.iloc[row_index].tolist()]
        else:
            return []

    def init_data(self, name):
        self.csv_file_path = name
        self.df = pd.read_csv(self.csv_file_path)
        app.headers = list(self.df.columns)
        self.data = self.convert_data(self.df.values.tolist())

    def convert_data(self, data):
        converted_data = []
        for row in data:
            new_row = [value for value in row]
            converted_data.append(new_row)
        return converted_data

    def set_voltage(self, voltage):
        command = f"VSET:{voltage}"
        self.send_command(self.serial_port1, command)

    def set_current(self, current):
        command = f"ISET:{current}"
        self.send_command(self.serial_port1, command)

    def set_voltage2(self, voltage):
        command = f":VOLT {voltage}V"
        self.send_command(self.serial_port2, command)

    def set_current2(self, current):
        command = f":CURR {current}A"
        self.send_command(self.serial_port2, command)

    def set_power2(self, power):
        command = f":POW {power}W"
        self.send_command(self.serial_port2, command)

    def set_resistance2(self, resist):
        command = f":RES {resist}OHM"
        self.send_command(self.serial_port2, command)

    def get_voltage1(self):
        self.send_command(self.serial_port1, "VOUT?")
        return self.read_response(self.serial_port1)

    def get_current1(self):
        self.send_command(self.serial_port1, "IOUT?")
        return self.read_response(self.serial_port1)

    def get_voltage2(self):
        self.send_command(self.serial_port2, ":MEAS:VOLT?")
        return self.read_response(self.serial_port2)

    def get_current2(self):
        self.send_command(self.serial_port2, ":MEAS:CURR?")
        return self.read_response(self.serial_port2)




class BatteryLoggerApp:
    def __init__(self, root, logic):
        self.root = root
        
        self.logic = logic
        self.root.title("GUI for Charging and Discharging")
        self.plot_setup()

        self.start_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        print("Performing Cleanup...")
        try:
            self.logic.stop_plot()
            self.root.destroy()
        except:
            self.root.destroy()

    def plot_setup(self):
        self.subplot_count = 0
        self.fig = plt.figure(figsize=(6, 4))
        self.sub1 = self.fig.add_subplot(2, 1, 1)
        self.sub2 = self.fig.add_subplot(2, 1, 2)

    def plot(self, subplot, name, unit, x, y):
        self.subplot_count += 1
        subplot.clear()
        subplot.plot(x, y)
        subplot.set_ylabel(name + ' in ' + unit)
        plt.tight_layout()
        subplot.grid()

        if self.subplot_count != 2:
            plt.setp(subplot.get_xticklabels(), visible=False)
            subplot.xaxis.set_ticks_position('none')
        else:
            subplot.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self.subplot_count = 0
    
    def run_plot(self):
        print("Starting to measure...")

        def init_pass():
            pass
        self.ani = animation.FuncAnimation(self.fig, logic.animate, 
            interval=1000, init_func=init_pass, frames=None, cache_frame_data=False)
        
        plt.tight_layout()
        plt.show()
        if not logic.end:
            logic.stop_plot()

        logic.savedata.to_csv(f"data/{logic.filename}.csv", sep=";", index=False)
        print(f"Data saved to data/{logic.filename}.csv")

    def show_error(self, error):
        messagebox.showerror("Error", error)
    
    def start_gui(self):
        root.geometry("400x300")
        self.fra = Frame(root)
        self.fra.pack()
        tk.Button(self.fra, text="Choose .step file", command=self.choose).grid(row=0, column=1, padx=30)
        self.temp_button=tk.Button(self.fra, text="Create new file", command=self.new_file)
        self.temp_button.grid(row=0, column=2, padx=30)
        self.logic.setup_ports()

    def choose(self):
        filename = filedialog.askopenfilename(
            title="Please choose file",
            filetypes=[("STEP Files", "*.step")]  
        )
        if filename:
            self.stepfile = filename
            logic.init_data(self.stepfile)
            if logic.new_start:
                self.start_full()
            else:
                self.setup_treeview(root)

    def new_file(self):
        self.headers = ["Step", "Mode", "Desired Value", "Value", 
                        "Cancel Condition 1", "Cancel Value 1", "Next Step 1", 
                        "Cancel Condition 2", "Cancel Value 2", "Next Step 2"]
        if self.logic.new_start:
            self.start_full()
        else:
            self.setup_treeview(root)

    def start_full(self):
        self.logic.new_start = False
        try:
            self.logic.serial_port1
            self.logic.serial_port2
        except:
            self.show_error("Error while opening Ports.")
            return
        root.geometry("")
        self.temp_button.destroy()
        self.button2 = tk.Button(self.fra, text="Save .step File", command=self.save_step).grid(row=0, column=0, padx=30)
        self.setup_add_frame(root)
        self.setup_middle(root)
        self.setup_treeview(root)
        self.plot_button1 = Button(root, text="Start", command=self.logic.do_plot)
        self.plot_button1.pack(pady=5)
        
    def get_data(self):
        return self.logic.data
    
    def setup_treeview(self, frame):
        self.exist = False
        if hasattr(self, "my_tree"):
            for item in self.my_tree.get_children():
                self.my_tree.delete(item)
            self.exist = True
        else:
            self.my_tree = ttk.Treeview(frame)
            self.my_tree["columns"] = self.headers
            self.my_tree["show"] = "headings"
            for col in self.headers:
                if col in ["Mode"]:
                    self.my_tree.column(col, anchor=W, width=70, minwidth=5)
                elif col in ["Value"]:
                    self.my_tree.column(col, anchor=W, width=40, minwidth=5)
                elif col in ["Cancel Condition 1", "Cancel Condition 2"]:
                    self.my_tree.column(col, anchor=W, width=125, minwidth=5)
                elif col in ["Next Step 1", "Next Step 2"]:
                    self.my_tree.column(col, anchor=W, width=105, minwidth=5)
                else:
                    self.my_tree.column(col, anchor=W, width=95, minwidth=5)
                self.my_tree.heading(col, text=col, anchor=W)
            self.my_tree.pack(pady=10, padx=20)
            
        for record in self.get_data():
            self.my_tree.insert("", "end", values=record)

    def setup_middle(self, frame):
        self.fm = Frame(frame)
        self.fm.pack()
        self.button1 = tk.Button(self.fm, text="Add to Tree", command=self.handle_add_record)
        self.button1.grid(row=0, column=0, padx=10, pady=5)
        self.button1 = tk.Button(self.fm, text="Choose line", command=self.handle_select_record)
        self.button1.grid(row=0, column=1, padx=10, pady=5)
        self.button1 = tk.Button(self.fm, text="Redo line", command=self.handle_update_record)
        self.button1.grid(row=0, column=2, padx=10, pady=5)
        self.button1 = tk.Button(self.fm, text="Delete line", command=self.handle_delete_record)
        self.button1.grid(row=0, column=3, padx=10, pady=5)

    def mode_change(self, value):
        if value == "Charge":
            self.option_set = ["Voltage", "Current"]
        else:
            self.option_set = ["Voltage", "Current", "Power", "Resistance"]
        self.set_menu.destroy()
        self.set_menu=ttk.OptionMenu(self.add, self.selected_set, self.option_set[0], *self.option_set, command=self.set_change)
        self.set_menu.grid(row=1, column=2, sticky="w", padx=8)
    def set_change(self, value):
        if value == "Voltage":
            self.einheit1.config(text="V")
        elif value == "Current":
            self.einheit1.config(text="A")
        elif value == "Resistance":
            self.einheit1.config(text="R")
        else:
            self.einheit1.config(text="W")
    def break_change(self, value):
        if value == "Min Current":
            self.einheit2.config(text="A")
        elif value == "Max Voltage":
            self.einheit2.config(text="V")
        elif value == "Min Voltage":
            self.einheit2.config(text="V")
        elif value == "Time":
            self.einheit2.config(text="s")
        elif value == "Charge":
            self.einheit2.config(text="C")
        elif value == "Energy":
            self.einheit2.config(text="J")
    def break_2_change(self, value):
        if value == "Min Current":
            self.einheit3.config(text="A")
        elif value == "Max Voltage":
            self.einheit3.config(text="V")
        elif value == "Min Voltage":
            self.einheit3.config(text="V")
        elif value == "Time":
            self.einheit3.config(text="s")
        elif value == "Charge":
            self.einheit3.config(text="C")
        elif value == "Energy":
            self.einheit3.config(text="J")
        else:
            self.einheit3.config(text="-")

    def setup_add_frame(self, frame):
        self.add = Frame(frame)
        self.add.pack()
        self.selected_step = tk.IntVar()
        self.selected_mode = tk.StringVar()
        self.selected_set = tk.StringVar()
        self.selected_break = tk.StringVar()
        self.selected_break_2 = tk.StringVar()
        self.selected_next = tk.IntVar()
        self.selected_next_2 = tk.IntVar()
        self.option_mode = ["Charge", "Discharge"]
        self.option_set = ["Voltage", "Current"] #["Voltage", "Current", "Power", "Resistance"]
        self.option_break = ["Min Current", "Max Voltage", "Min Voltage", "Time", "Charge", "Energy"]
        self.option_break_2 = ["No Condition", "Min Current", "Max Voltage", "Min Voltage", "Time", "Charge", "Energy"]
        self.entries = []

        ttk.Label(self.add, text="Step").grid(row=0, column=0, padx=8, pady=4)
        self.step_spin=ttk.Spinbox(self.add, from_=1, to=100, textvariable=self.selected_step, width=5)
        self.step_spin.grid(row=1, column=0, padx=8, pady=4)
        self.step_spin.set(1)

        ttk.Label(self.add, text="Mode").grid(row=0, column=1, padx=8, pady=4)
        ttk.OptionMenu(self.add, self.selected_mode, self.option_mode[0], *self.option_mode, command=self.mode_change).grid(row=1, column=1, padx=8, pady=4)

        ttk.Label(self.add, text="Desired Value").grid(row=0, column=2, padx=8, pady=4)
        self.set_menu=ttk.OptionMenu(self.add, self.selected_set, self.option_set[0], *self.option_set, command=self.set_change)
        self.set_menu.grid(row=1, column=2, sticky="w", padx=8)
        
        self.wertframe = Frame(self.add)
        self.wertframe.grid(row=1, column=3, padx=8, pady=4)
        ttk.Label(self.add, text="Value").grid(row=0, column=3, padx=8, pady=4)
        entry1=ttk.Entry(self.wertframe, width=5)
        entry1.grid(row=0, column=0, padx=2)
        entry1.insert(0,0)
        self.einheit1=ttk.Label(self.wertframe, text="V")
        self.einheit1.grid(row=0, column=1, padx=2)
        
        ttk.Label(self.add, text="Cancel Condition 1").grid(row=0, column=4, padx=8, pady=4)
        ttk.OptionMenu(self.add, self.selected_break, self.option_break[0], *self.option_break, command=self.break_change).grid(row=1, column=4, sticky="w", padx=8)
        
        self.wertframe2 = Frame(self.add)
        self.wertframe2.grid(row=1, column=5, padx=8, pady=4)
        ttk.Label(self.add, text="Value").grid(row=0, column=5, padx=8, pady=4)
        entry2=ttk.Entry(self.wertframe2, width=5)
        entry2.grid(row=0, column=0, padx=2)
        entry2.insert(0,0)
        self.einheit2=ttk.Label(self.wertframe2, text="A")
        self.einheit2.grid(row=0, column=1, padx=2)
        
        ttk.Label(self.add, text="Next Step").grid(row=0, column=6, padx=8, pady=4)
        ttk.Spinbox(self.add, from_=0, to=100, textvariable=self.selected_next, width=5).grid(row=1, column=6, padx=8, pady=4)
        
        ttk.Label(self.add, text="Cancel Condition 2").grid(row=0, column=7, padx=8, pady=4)
        ttk.OptionMenu(self.add, self.selected_break_2, self.option_break_2[0], *self.option_break_2, command=self.break_2_change).grid(row=1, column=7, sticky="w", padx=8)
        
        self.wertframe3 = Frame(self.add)
        self.wertframe3.grid(row=1, column=8, padx=8, pady=4)
        ttk.Label(self.add, text="Value").grid(row=0, column=8, padx=8, pady=4)
        entry3=ttk.Entry(self.wertframe3, width=5)
        entry3.grid(row=0, column=0, padx=2)
        entry3.insert(0,0)
        self.einheit3=ttk.Label(self.wertframe3, text="-")
        self.einheit3.grid(row=0, column=1, padx=2)
        
        ttk.Label(self.add, text="Next Step").grid(row=0, column=9, padx=8, pady=4)
        ttk.Spinbox(self.add, from_=0, to=100, textvariable=self.selected_next_2, width=5).grid(row=1, column=9, padx=8, pady=4)
        self.entries.append(entry1)
        self.entries.append(entry2)
        self.entries.append(entry3)

    def set_defaults(self, step, mode, set_value, value, break_1, break_1_value,
                    next_step, break_2, break_2_value, next_step_2):
        
        self.selected_step.set(step)
    
        self.selected_mode.set(mode)
    
        self.selected_set.set(set_value)

        self.entries[0].delete(0, 'end')
        self.entries[0].insert(0, value)
    
        self.selected_break.set(break_1)
    
        self.entries[1].delete(0, 'end')
        self.entries[1].insert(0, break_1_value)
    
        self.selected_next.set(next_step)
    
        self.selected_break_2.set(break_2)
    
        self.entries[2].delete(0, 'end')
        self.entries[2].insert(0, break_2_value)
    
        self.selected_next_2.set(next_step_2)

    def get_values(self):
        a = self.entries[0].get()
        b = self.einheit1.cget("text")
        c = a+b
        d = self.entries[1].get()
        f = self.einheit2.cget("text")
        g = d+f
        h = self.entries[2].get()
        i = self.einheit3.cget("text")
        j = h+i
        print(a, b, c)
        self.values=[]
        self.values.append(self.selected_step.get())
        self.values.append(self.selected_mode.get())
        self.values.append(self.selected_set.get())
        self.values.append(c)
        self.values.append(self.selected_break.get())
        self.values.append(g)
        self.values.append(self.selected_next.get())
        self.values.append(self.selected_break_2.get())
        self.values.append(j)
        self.values.append(self.selected_next_2.get())
        
    def data_check(self):
        new_record = []
        for entry in self.entries:
            value = entry.get()
            try:
                float_value = float(value)
                new_record.append(float_value)
            except ValueError:
                self.show_error("All inputs must be Numbers.")
                return
        if any(value < 0 for value in new_record):
            self.show_error("All inputs must be positive.")
            return
        return True
        
    def handle_add_record(self):
        self.get_values()
        existing_values = [int(self.my_tree.item(item, "values")[0]) for item in self.my_tree.get_children()]
        if self.values[0] in existing_values:
            self.show_error(f"Step {self.values[0]} already exists. Please choose a different number")
        #elif self.values[1]=="Charge" and self.values[2]=="Power":
        #    self.show_error("Charge does not have the option Power.")
        #elif self.values[1]=="Charge" and self.values[2]=="Resistance":
        #    self.show_error("Charge does not have the option Resistance.")
        else:
            if self.data_check():
                new_record = [value for value in self.values]
                self.my_tree.insert("", "end", values=[value for value in new_record])

    def handle_update_record(self):
        try:
            self.get_values()
            selected = self.my_tree.selection()[0]
            renew_record = [value for value in self.values]
            self.my_tree.item(selected, text="", values=renew_record)
        except Exception as e:
            self.show_error(e)
            return

    def handle_delete_record(self):
        selected = self.my_tree.selection()
        if selected:
            confirm = messagebox.askyesno("Confirm", "Do you want to delete the selected line?")
            if confirm:
                for record in selected:
                    self.my_tree.delete(record)
        else:
            self.show_error("No line selected.")

    def handle_select_record(self):
        try: 
            selected = self.my_tree.selection()[0]
            values = self.my_tree.item(selected, 'values')
            self.replace(values)
            self.mode_change(values[1])
            #print(values[1])
            self.selected_set.set(values[2])
            self.set_change(values[2])
            self.break_change(values[4])
            self.break_2_change(values[7])

        except: 
            selected = self.my_tree.get_children()[0]
            values = self.my_tree.item(selected, 'values')
            self.replace(values)
            self.mode_change(values[1])
            self.set_menu.set(values[2])
            self.set_change(values[2])
            self.break_change(values[4])
            self.break_2_change(values[7])

    def replace(self, values):
        step, mode, set_value, value, break_1, break_1_value, next_step, break_2, break_2_value, next_step_2 = values
    
        self.set_defaults(step, mode, set_value, value[:-1], break_1, break_1_value[:-1], next_step, break_2, break_2_value[:-1], next_step_2) 

    def save_step(self):
        if logic.filename == "" :
            name = simpledialog.askstring("Input", "Save .step File under following name:")
        else:
            name = logic.filename
        v1 = [int(self.my_tree.item(item, "values")[0]) for item in self.my_tree.get_children()]
        v2 = [(self.my_tree.item(item, "values")[1]) for item in self.my_tree.get_children()]
        v3 = [(self.my_tree.item(item, "values")[2]) for item in self.my_tree.get_children()]
        v4 = [self.my_tree.item(item, "values")[3] for item in self.my_tree.get_children()]
        v5 = [(self.my_tree.item(item, "values")[4]) for item in self.my_tree.get_children()]
        v6 = [self.my_tree.item(item, "values")[5] for item in self.my_tree.get_children()]
        v7 = [int(self.my_tree.item(item, "values")[6]) for item in self.my_tree.get_children()]
        v8 = [(self.my_tree.item(item, "values")[7]) for item in self.my_tree.get_children()]
        v9 = [self.my_tree.item(item, "values")[8] for item in self.my_tree.get_children()]
        v10 = [int(self.my_tree.item(item, "values")[9]) for item in self.my_tree.get_children()]
        step = {
            'Step': v1,
            'Mode': v2,
            'Desired Value': v3,
            'Value': v4,
            'Cancel Condition 1': v5,
            'Cancel Value 1': v6,
            'Next Step 1': v7,
            'Cancel Condition 2': v8,
            'Cancel Value 2': v9,
            'Next Step 2': v10,
        }

        self.logic.dataf = pd.DataFrame(step)
        step_file_path = f"{name}.step"
        self.logic.dataf.to_csv(step_file_path, index=False)
        df = pd.read_csv(step_file_path)

    def run(self):
        self.root.mainloop()
    
if __name__ == "__main__":
    root = tk.Tk()
    ser = SerialCommunicator()
    app = None #Placeholder
    logic = BatteryLoggerLogic(ser, app)
    app = BatteryLoggerApp(root, logic)
    logic.app = app
    app.run()
