import mediapipe as mp
import cv2
import numpy as np

class LivenessDetector:
    def __init__(self, ear_threshold=0.25):
        self.ear_threshold = ear_threshold
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Indices for EAR (approximate compatible with 468 mesh)
        # Left Eye (Horizontal: 33-133, Vertical: 159-145)
        # Right Eye (Horizontal: 362-263, Vertical: 386-374)
        self.LEFT_EYE = [33, 133, 159, 145]
        self.RIGHT_EYE = [362, 263, 386, 374]

    def get_ear(self, landmarks, indices):
        # indices: [p1, p2, p3, p4] -> p1,p2 horizontal, p3,p4 vertical
        # Actually simplified EAR: Vertical / Horizontal
        
        p1 = np.array([landmarks[indices[0]].x, landmarks[indices[0]].y])
        p2 = np.array([landmarks[indices[1]].x, landmarks[indices[1]].y])
        p3 = np.array([landmarks[indices[2]].x, landmarks[indices[2]].y])
        p4 = np.array([landmarks[indices[3]].x, landmarks[indices[3]].y])

        dist_h = np.linalg.norm(p1 - p2)
        dist_v = np.linalg.norm(p3 - p4)

        if dist_h == 0: return 0.0
        return dist_v / dist_h

    def get_mar(self, landmarks):
        # Mouth Aspect Ratio for smile/open mouth
        # Outer lips: 61 (left), 291 (right), 0 (top), 17 (bottom)
        p_left = np.array([landmarks[61].x, landmarks[61].y])
        p_right = np.array([landmarks[291].x, landmarks[291].y])
        p_top = np.array([landmarks[0].x, landmarks[0].y])
        p_btm = np.array([landmarks[17].x, landmarks[17].y])
        
        dist_h = np.linalg.norm(p_left - p_right)
        dist_v = np.linalg.norm(p_top - p_btm)
        
        if dist_h == 0: return 0
        return dist_v / dist_h

    def get_orientation(self, landmarks):
        # Estimate head yaw using nose and cheek/ear landmarks
        # Nose tip: 1
        # Left cheek/ear area: 234
        # Right cheek/ear area: 454
        
        nose = landmarks[1].x
        left_side = landmarks[234].x
        right_side = landmarks[454].x
        
        # Calculate relative distances (horizontal)
        dist_to_left = abs(nose - left_side)
        dist_to_right = abs(nose - right_side)
        
        ratio = dist_to_left / (dist_to_right + 1e-6)
        
        if ratio > 2.0:
            return "TURN_LEFT" # Actually user turning left (camera view right)
        elif ratio < 0.5:
            return "TURN_RIGHT"
        else:
            return "CENTER"

    def process_frame(self, frame):
        """
        Process frame to check liveness attributes.
        Returns: {is_blinking, is_smiling, orientation, ear, mar, landmarks}
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        info = {
            "is_blinking": False,
            "is_smiling": False,
            "orientation": "CENTER",
            "ear": 0.0,
            "mar": 0.0,
            "landmarks": None
        }
        
        if not results.multi_face_landmarks:
            return info

        landmarks = results.multi_face_landmarks[0].landmark
        info["landmarks"] = landmarks
        
        # EAR (Blink)
        left_ear = self.get_ear(landmarks, self.LEFT_EYE)
        right_ear = self.get_ear(landmarks, self.RIGHT_EYE)
        avg_ear = (left_ear + right_ear) / 2.0
        info["ear"] = avg_ear
        info["is_blinking"] = avg_ear < 0.18
        
        # MAR (Smile)
        mar = self.get_mar(landmarks)
        info["mar"] = mar
        info["is_smiling"] = mar > 0.35 # Threshold for smile
             
        # Orientation
        info["orientation"] = self.get_orientation(landmarks)
        
        return info
