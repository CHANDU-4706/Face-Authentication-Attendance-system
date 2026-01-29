import tkinter as tk
from tkinter import simpledialog, messagebox
import cv2
import os
from PIL import Image, ImageTk
import datetime
import threading
import time

from .face_core import FaceSystem
from .liveness import LivenessDetector
from .storage import DatabaseManager

class AppUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Authentication Attendance System")
        self.root.geometry("1100x750")

        # Initialize Core Systems
        self.db = DatabaseManager()
        self.face_system = FaceSystem()
        self.liveness_detector = LivenessDetector()

        # Cache User Names
        self.user_map = self.db.get_users_dict()

        # State Variables
        self.current_user_id = None
        self.current_user_name = None
        self.last_punch_time = {} # user_id -> timestamp to prevent spamming
        self.liveness_counter = 0 
        self.is_verifying = False 
        self.liveness_confirmed = False
        
        # Active Liveness State
        self.active_challenge = None
        self.challenge_start_time = 0
        self.CHALLENGES = ["BLINK", "SMILE", "TURN_LEFT", "TURN_RIGHT"]
        
        # Registration State
        self.is_registering = False
        self.reg_samples = []
        self.reg_user_id = None
        self.reg_user_name = None
        self.reg_count = 0
        self.MAX_SAMPLES = 50
        
        # Stability Buffers
        self.liveness_exit_counter = 0
        self.LIVENESS_THRESHOLD_FRAMES = 30 # Maintain verified state for 1 second after face loss
        
        # Diagnostic Startup
        print(f"--- System Diagnostic ---")
        print(f"Users in Database: {len(self.user_map)}")
        if os.path.exists(self.face_system.trainer_path):
             stats = os.stat(self.face_system.trainer_path)
             print(f"Trainer Model Found: {self.face_system.trainer_path} ({stats.st_size} bytes)")
        else:
             print("WARNING: No Trainer Model found. Register a user first.")
        print(f"-------------------------")

        # Camera
        self.cap = cv2.VideoCapture(0)
        
        # UI Layout
        self.setup_ui()
        
        # Start Video Loop
        self.update_video()

    def setup_ui(self):
        # Main Container
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Left Panel (Video)
        self.left_panel = tk.Frame(self.main_container, bg="black", width=800)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.video_label = tk.Label(self.left_panel)
        self.video_label.pack(expand=True)

        # Right Panel (Controls & Status)
        self.right_panel = tk.Frame(self.main_container, bg="#f0f0f0", width=300)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)

        # Title
        tk.Label(self.right_panel, text="Attendance System", font=("Segoe UI", 20, "bold"), bg="#f0f0f0").pack(pady=20)

        # Status Box
        self.status_var = tk.StringVar(value="System Ready")
        self.status_label = tk.Label(self.right_panel, textvariable=self.status_var, font=("Segoe UI", 12), bg="white", fg="blue", wraplength=280, padx=10, pady=10, relief=tk.RIDGE)
        self.status_label.pack(pady=10, padx=10, fill=tk.X)

        # Instructions
        self.instruction_var = tk.StringVar(value="Look at camera to verify.")
        tk.Label(self.right_panel, textvariable=self.instruction_var, font=("Segoe UI", 10), bg="#f0f0f0", wraplength=280).pack(pady=5)

        # --- Control Action Buttons ---
        self.btn_frame = tk.Frame(self.right_panel, bg="#f0f0f0")
        self.btn_frame.pack(pady=20, fill=tk.X, padx=20)

        self.punch_in_btn = tk.Button(self.btn_frame, text="PUNCH IN", command=lambda: self.manual_punch('IN'), font=("Segoe UI", 12, "bold"), bg="#4CAF50", fg="white", state=tk.DISABLED)
        self.punch_in_btn.pack(fill=tk.X, pady=5)

        self.punch_out_btn = tk.Button(self.btn_frame, text="PUNCH OUT", command=lambda: self.manual_punch('OUT'), font=("Segoe UI", 12, "bold"), bg="#FF9800", fg="white", state=tk.DISABLED)
        self.punch_out_btn.pack(fill=tk.X, pady=5)

        # Register Button
        self.reg_btn = tk.Button(self.right_panel, text="Register New User", command=self.register_user_btn, font=("Segoe UI", 12), bg="#2196F3", fg="white", width=20)
        self.reg_btn.pack(pady=20)
        
        # Exit Button
        self.exit_btn = tk.Button(self.right_panel, text="EXIT SYSTEM", command=self.quit_app, font=("Segoe UI", 11, "bold"), bg="#f44336", fg="white", width=20)
        self.exit_btn.pack(side=tk.BOTTOM, pady=20)

        # Log Display
        tk.Label(self.right_panel, text="Recent Activity:", bg="#f0f0f0", anchor="w").pack(fill=tk.X, padx=10)
        self.log_text = tk.Text(self.right_panel, height=15, width=35, font=("Courier New", 9))
        self.log_text.pack(padx=10, pady=5)

    def log_msg(self, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)

    def register_user_btn(self):
        if self.is_registering: return
        
        name = simpledialog.askstring("Register", "Enter Name of the User:")
        if name:
            try:
                # Create user in DB first
                uid = self.db.add_user(name)
                self.reg_user_id = uid
                self.reg_user_name = name
                self.reg_samples = []
                self.reg_count = 0
                self.is_registering = True
                self.status_var.set(f"Look at camera. Capturing samples...")
                self.reg_btn.config(state=tk.DISABLED)
                self.punch_in_btn.config(state=tk.DISABLED)
                self.punch_out_btn.config(state=tk.DISABLED)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def finish_registration(self):
        if hasattr(self, 'is_training') and self.is_training:
            return
            
        self.is_training = True
        self.status_var.set("Training Model... Please Wait.")
        self.log_msg("Training started...")
        
        def train_task():
            try:
                self.face_system.save_samples(self.reg_user_id, self.reg_samples)
                self.face_system.train_model()
            except Exception as e:
                print(f"Training Task Failed: {e}")
            
            # Update cache
            self.user_map = self.db.get_users_dict()
            
            # Reset UI
            self.root.after(0, lambda: self.registration_complete())

        threading.Thread(target=train_task).start()

    def registration_complete(self):
        self.is_training = False
        self.is_registering = False
        self.reg_btn.config(state=tk.NORMAL)
        self.log_msg(f"Registered: {self.reg_user_name}")
        self.status_var.set("Registration Complete.")
        messagebox.showinfo("Success", f"User {self.reg_user_name} registered!")

    def manual_punch(self, punch_type):
        if not self.current_user_id:
            return

        if not self.current_user_id:
            return

        # Double Check Cooldown
        last = self.last_punch_time.get(self.current_user_id, 0)
        if time.time() - last < 30:
            remaining = int(30 - (time.time() - last))
            messagebox.showwarning("Cooldown", f"Please wait {remaining} seconds before punching again.")
            return

        # Log attendance
        self.db.log_attendance(self.current_user_id, punch_type)
        self.last_punch_time[self.current_user_id] = time.time()
        
        # UI Feedback
        color = "green" if punch_type == "IN" else "orange"
        msg = f"{punch_type} Success: {self.current_user_name} (Strict Verified)"
        self.status_var.set(msg)
        self.status_label.config(fg=color)
        self.log_msg(msg)
        
        # Reset verification state to avoid spamming
        self.liveness_confirmed = False 
        self.active_challenge = None
        self.current_user_id = None
        self.current_user_name = None
        self.punch_in_btn.config(state=tk.DISABLED)
        self.punch_out_btn.config(state=tk.DISABLED)
        
    def quit_app(self):
        self.on_closing()

    def update_video(self):
        ret, frame = self.cap.read()
        if ret:
            display_frame = frame.copy()
            
            # --- REGISTRATION MODE ---
            if self.is_registering:
                gray_crop, rect = self.face_system.get_face_crop(frame)
                
                if gray_crop is not None:
                    self.reg_samples.append(gray_crop)
                    self.reg_count += 1
                    
                    # Draw visual feedback
                    x, y, w, h = rect
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (255, 255, 0), 2)
                    cv2.putText(display_frame, f"Capturing: {self.reg_count}/{self.MAX_SAMPLES}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
                    if self.reg_count >= self.MAX_SAMPLES:
                        self.finish_registration()
                else:
                    cv2.putText(display_frame, "Face not found!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # --- RECOGNITION MODE ---
            else:
                try:
                    user_id, conf, rect = self.face_system.recognize_face(frame)
                    
                    if rect:
                        x, y, w, h = rect
                        name = "Register First"
                        color = (0, 0, 255)
                        
                        # Confidence Logic
                        # Debugging: Print confidence to console
                        print(f"DEBUG: ID={user_id}, Conf={conf}") 
                        
                        if conf < 100 and user_id is not None:  # RELAXED THRESHOLD from 85 to 100 for easier recognition
                            name = self.user_map.get(user_id, "Register First")
                            color = (0, 255, 0)
                            
                            # ACTIVE LIVENESS CHECK (2-Step Sequence)
                            live_info = self.liveness_detector.process_frame(frame)
                            EAR = live_info["ear"]
                            MAR = live_info["mar"]
                            ORIENT = live_info["orientation"]
                            
                            if not self.liveness_confirmed:
                                import random
                                # If no active challenge queue, create one
                                if not self.active_challenge:
                                    # Create a sequence of 2 unique challenges
                                    self.active_challenge = random.sample(self.CHALLENGES, 2)
                                    self.challenge_start_time = time.time()
                                
                                # Get current challenge target
                                current_target = self.active_challenge[0]
                                
                                # Display Instructions
                                # "Challenge 1/2: Please SMILE!"
                                step_num = 3 - len(self.active_challenge)
                                challenge_text = f"Step {step_num}/2: Please {current_target}!"
                                text_color = (0, 165, 255) # Orange
                                cv2.putText(display_frame, challenge_text, (x, y+h+30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
                                
                                # Verify Current Challenge
                                passed = False
                                if current_target == "BLINK":
                                    if live_info["is_blinking"]: passed = True
                                elif current_target == "SMILE":
                                    if live_info["is_smiling"]: passed = True
                                elif current_target == "TURN_LEFT":
                                    if ORIENT == "TURN_LEFT": passed = True
                                elif current_target == "TURN_RIGHT":
                                    if ORIENT == "TURN_RIGHT": passed = True
                                
                                if passed:
                                    # Remove completed challenge
                                    self.active_challenge.pop(0)
                                    # Reset timer for next challenge
                                    self.challenge_start_time = time.time()
                                    
                                    # If queue empty -> ALL PASSED
                                    if not self.active_challenge:
                                        self.liveness_confirmed = True
                                        self.current_user_id = user_id
                                        self.current_user_name = name
                                        self.liveness_exit_counter = self.LIVENESS_THRESHOLD_FRAMES
                                        
                                        # CHECK COOLDOWN (30s)
                                        last = self.last_punch_time.get(user_id, 0)
                                        if time.time() - last < 30:
                                            self.status_var.set(f"Cooldown Active ({int(30 - (time.time()-last))}s)")
                                        else:
                                            # ENABLE BUTTONS
                                            self.punch_in_btn.config(state=tk.NORMAL)
                                            self.punch_out_btn.config(state=tk.NORMAL)
                                            self.status_var.set(f"Verified: {name}. Select Action.")
                                            
                                        # Reset challenge state
                                        self.active_challenge = None

                            else:
                                # Already confirmed, waiting for button press
                                cv2.putText(display_frame, "VERIFIED - SELECT ACTION", (x, y-30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                                
                                if self.current_user_id == user_id:
                                    self.liveness_exit_counter = self.LIVENESS_THRESHOLD_FRAMES # Keep buffer full
                                else:
                                    self.liveness_exit_counter -= 1
                                    
                                if self.liveness_exit_counter <= 0:
                                    self.liveness_confirmed = False
                                    self.active_challenge = None
                                    self.punch_in_btn.config(state=tk.DISABLED)
                                    self.punch_out_btn.config(state=tk.DISABLED)

                        else:
                            # Unrecognized or low confidence
                            # Debug log to console (Internal)
                            print(f"DEBUG: Unrecognized Face, Conf: {int(conf)}")
                            
                            if self.liveness_confirmed:
                                self.liveness_exit_counter -= 1
                                if self.liveness_exit_counter <= 0:
                                    self.liveness_confirmed = False
                                    self.active_challenge = None
                                    self.punch_in_btn.config(state=tk.DISABLED)
                                    self.punch_out_btn.config(state=tk.DISABLED)
                                    self.status_var.set("System Ready")
                            
                        cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
                        cv2.putText(display_frame, f"{name} ({int(conf)})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    
                    else:
                        # NO FACE FOUND
                        if self.liveness_confirmed:
                            self.liveness_exit_counter -= 1
                            if self.liveness_exit_counter <= 0:
                                self.liveness_confirmed = False
                                self.active_challenge = None
                                self.punch_in_btn.config(state=tk.DISABLED)
                                self.punch_out_btn.config(state=tk.DISABLED)
                                self.status_var.set("System Ready")
                
                except Exception as e:
                    # print(f"Update Loop Error: {e}")
                    pass

            # Convert to Tkinter Image
            img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.root.after(10, self.update_video)

    def on_closing(self):
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()
