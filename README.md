# Face Authentication Attendance System

![Status](https://img.shields.io/badge/Status-Active-success) ![Python](https://img.shields.io/badge/Python-3.x-blue)

An intelligent, AI-driven attendance system that uses Facial Recognition and Liveness Detection to ensure secure and accurate attendance logging.

## 🌟 Features
- **Real-time Face Recognition**: Utilizes **OpenCV's LBPH (Local Binary Patterns Histograms)** algorithm to identify registered users instantly with high accuracy on standard CPUs.
- **Active Liveness Detection**: A robust "Challenge-Response" system that asks users to perform random actions (**Smile**, **Blink**, **Turn Head**) to prove they are human, verified using **MediaPipe Face Mesh**.
- **Secure Attendance Logging**: Implements a "Verify-Then-Punch" workflow. Users can only punch in/out *after* passing the liveness check, preventing accidental or proxy attendance.
- **Liveness Stability Buffer**: Implements a 30-frame "grace period" to prevent session resets during brief movement or tracking loss.
- **Startup Diagnostics**: Automatically verifies database integrity and model existence on launch, logging status to the terminal.
- **Local Data Persistence**: All user profiles and time logs are securely stored in a local `sqlite3` database, ensuring data privacy and reliability.

## 🧠 Technical Architecture & Models
This project prioritizes **efficiency** and **deployability** over heavy hardware requirements.

### 1. Face Detection: MediaPipe BlazeFace
- **What it is**: An ultra-lightweight face detector optimized for mobile and CPU inference.
- **Why**: It is significantly faster (< 5ms) and more robust to occlusion than traditional Haar Cascades.
- **Working**: It uses a Single Shot Detector (SSD) architecture on a custom lightweight backbone to locate faces (bounding box) in the video stream.

### 2. Face Recognition: LBPH (Local Binary Patterns Histograms)
- **What it is**: A texture-based recognition algorithm provided by OpenCV.
- **Why**: Deep learning models (like FaceNet) require GPUs and thousands of images. LBPH works effectively with just **50 samples** and trains in seconds on a CPU.
- **Working**: 
    - Converts the face to grayscale.
    - Captures local texture patterns (binary comparisons with neighbors).
    - creates a histogram of these patterns.
    - Matches the current face's histogram to stored users using Chi-Square distance.

### 3. Active Liveness: MediaPipe Face Mesh
- **What it is**: A solution that maps **468 3D landmarks** on the user's face.
- **Why**: Bounding boxes aren't enough to detect subtle actions like "Blinking" or "Smiling".
- **Working**:
    - **Blink**: Calculates **EAR (Eye Aspect Ratio)** using vertical/horizontal eye landmark distances.
    - **Smile**: Calculates **MAR (Mouth Aspect Ratio)** using lip landmarks.
    - **Head Turn**: compares the distance of the nose tip to the left vs. right cheek landmarks to estimate Yaw.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: A generic webcam is required.*

## 🚀 Usage

1.  **Run the Application**:
    ```bash
    python main.py
    ```
2.  **Register a User**:
    - Click **"Register New User"**.
    - Enter the name.
    - Look at the camera while it captures 50 samples.
    - Wait for the "Training Complete" message.
3.  **Mark Attendance**:
    - Look at the camera.
    - **Follow the Challenges**: The system will ask you to (e.g., "Smile", "Turn Left").
    - Complete the **2-Step Sequence** to prove you are human.
    - Once "Verified", click **PUNCH IN** or **PUNCH OUT**.
    - Your attendance is now saved in `attendance.db`.

## 📂 Project Structure
```
Face Authenticator/
├── src/
│   ├── face_core.py    # Face detection & recognition logic
│   ├── liveness.py     # Active Liveness (Blink, Smile, Turn detection)
│   ├── storage.py      # Database operations
│   └── ui.py           # GUI (Tkinter)
├── dataset/            # Stores user face images
├── attendance.db       # SQLite database
├── trainer.yml         # Trained recognition model
├── main.py             # Entry point
└── documentation.md    # Detailed technical docs
```

## ⚠️ Understanding ML Limitations
Honesty about system constraints is key to engineering.
1.  **Similar Faces**: LBPH uses texture patterns. Twins or siblings with extremely similar facial structures might result in false positives.
2.  **Lighting Sensitivity**: Extreme backlighting or pitch-black conditions can degrade accuracy. The system works best in standard indoor lighting.
3.  **Video Replay**: While our **Active Liveness (Challenge-Response)** blocks most spoofing, a sophisticated attacker with a high-resolution, interactive screen setup could theoretically bypass it given enough attempts.

## 🔮 Future Improvements
To scale this system for enterprise use, the following upgrades would be next on the roadmap:
1.  **Deep Learning Recognition**: Migrating from LBPH to **ArcFace/FaceNet** for higher accuracy on million-scale datasets.
2.  **Advanced Anti-Spoofing**: Implementing **CASIA-FASD** (CNN-based spoof detection) or using IR/Depth cameras (Intel RealSense) for hardware-level liveness.
3.  **Cloud Sync**: Encrypting and syncing the local `sqlite3` DB to a central cloud server for multi-site attendance.
4.  **Drift Detection**: Monitoring model confidence degradation over time to trigger auto-retraining.
