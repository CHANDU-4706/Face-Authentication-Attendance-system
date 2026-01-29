# Face Authentication Attendance System - In-Depth Documentation

## 1. Project Overview & Architecture
This project is an **AI-powered Biometric Attendance System** designed to solve the problem of proxy attendance and streamline the check-in/out process. It moves beyond simple face detection by integrating **Liveness Detection** to prevent spoofing attacks (e.g., holding up a photo).

The system is built using a modular architecture:
- **`src.face_core`**: Handles face detection (MediaPipe) and recognition (LBPH).
- **`src.liveness`**: Computes EAR (Blink), MAR (Smile), and Head Orientation (Yaw) for liveness checks.
- **`src.storage`**: Manages the SQLite database for users and logs.
- **`src.ui`**: The Tkinter-based frontend that orchestrates the workflow.

## 2. workflow & Features

### A. The "Verify-Then-Action" Workflow
To ensure valid inputs, the system strictly follows a state-based workflow:
1.  **Face Detection**: The camera continuously scans for faces.
2.  **Recognition**: If a face is found, the **LBPH Face Recognizer** attempts to match it against the registered dataset.
3.  **Active Liveness Challenge**:
    - Even if recognized, the system **blocks** any action.
    - The system issues a **Randomized 2-Step Challenge** (e.g., "Step 1: Smile" -> "Step 2: Turn Left").
    - The user must perform these actions in sequence.
    - **MediaPipe Face Mesh** tracks landmarks (Eyes, Lips, Head Pose) to verify each step.
4.  **Action Authorization**:
    - Only *after* the full sequence is passed, the **Punch In** and **Punch Out** buttons become active.
    - A **30-second cooldown** is enforced between punches to prevent spamming.

### B. Punch In / Punch Out
- **Punch In**: Logs the entry time. System checks for cooldowns (preventing double punches within 60s).
- **Punch Out**: Logs the exit time.
- **Data Integrity**: All logs are timestamped and stored in a local SQLite database (`attendance.db`), ensuring reliable record-keeping.

## 3. Technologies & Models Used
This system chooses **efficiency and speed** over heavy deep learning models to ensure it runs smoothly on standard CPUs without GPUs.

| Component | Technology / Model | Why this choice? |
| :--- | :--- | :--- |
| **Face Detection** | **MediaPipe Face Detection** (BlazeFace) | Extremely lightweight (~0.6KB model), specifically optimized for mobile/CPU inference. It is much faster and more robust to occlusion than OpenCV's older Haar Cascades. |
| **Face Recognition** | **OpenCV LBPH (Local Binary Patterns Histograms)** | Works well with small datasets (50 images/user) and requires no GPU training. Deep Learning models (ResNet/FaceNet) often require thousands of images or transfer learning which is overkill for this scope. |
| **Liveness Check** | **MediaPipe Face Mesh** (468 landmarks) | Provides precise 3D-like landmarks for eyes (EAR) and lips (MAR), enabling subtle gesture detection (Blink/Smile) that bounding-box detectors cannot do. |
| **GUI** | **Tkinter** | Native Python library, lightweight, and thread-safe for simple video application loops. |
| **Database** | **SQLite3** | Serverless, zero-configuration database perfect for single-system deployment. |

## 4. Technical Depth & Algorithms

### A. Feature Extraction & Recognition (LBPH)
We utilize **Local Binary Patterns Histograms (LBPH)** for face recognition. 
- **Why LBPH?**: Unlike deep learning models (like ResNet) that require massive datasets and GPUs, LBPH is efficient for CPU-based systems and works well with small datasets (50 images per user).
- **Mechanism**:
    1.  The face image is divided into a grid.
    2.  For each pixel, it compares intensity with neighbors to generate a binary pattern.
    3.  Histograms of these patterns are concatenated to form a feature vector.
    4.  **Matching**: We use Chi-square distance to compare the current face's histogram with the stored user histograms. A lower distance means a better match (High Confidence).

### B. Anti-Spoofing: Active Liveness Detection
We implement **Active Liveness Detection** (Challenge-Response) to prevent sophisticated spoofing attacks.
- **Mechanism**: The system randomly issues a challenge command to the user.
- **Challenges**:
    1.  **"Blink"**: Detected via Eye Aspect Ratio (EAR).
    2.  **"Smile"**: Detected via Mouth Aspect Ratio (MAR) using lips landmarks.
    3.  **"Turn Left" / "Turn Right"**: Detected via Head Pose Estimation (Yaw) by comparing the relative distance of the nose tip to cheek/ear landmarks.
- **Liveness Stability**: A 30-frame (approx. 1 second) buffer prevents the system from resetting the "Verified" state if the user's face is briefly lost or unrecognized during a challenge.
- **Why Active?**: Passive blinking can sometimes be spoofed by a video. Random challenges require real-time interaction, making it extremely difficult to spoof with static photos or pre-recorded videos.

## 4. Evaluation Criteria & Performance

This project was built to meet specific engineering criteria:

| Criterion | Implementation Details |
| :--- | :--- |
| **Functional Accuracy** | High accuracy achieved by using high-contrast registration (50 samples) and strict confidence thresholds (< 70 for match). |
| **System Reliability** | - **Crash Prevention**: `WM_DELETE_WINDOW` handling ensures camera resource release.<br>- **Persistence**: Startup diagnostics verify `trainer.yml` and `attendance.db` integrity.<br>- **Error Handling**: Hardened training logic with type-casting (np.int32) to prevent C++ exceptions. |
| **User Experience** | - **Feedback**: Visual bounding boxes, confidence scores, and instruction text.<br>- **Control**: Manual Punch In/Out buttons prevent accidental logs. |
| **Code Quality** | Modular design (separation of UI, Logic, Data), PEP-8 compliance, and documented classes. |

## 5. Future Scope
- **Cloud Sync**: Uploading `attendance.db` logs to a central server.
- **Encryption**: Encrypting the `dataset` folder to protect user privacy.
