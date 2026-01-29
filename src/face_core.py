import cv2
import numpy as np
import os
import mediapipe as mp
import shutil

class FaceSystem:
    def __init__(self, dataset_path="dataset", trainer_path="trainer.yml"):
        self.dataset_path = dataset_path
        self.trainer_path = trainer_path
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.mp_face_detection = mp.solutions.face_detection
        self.detector = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5)
        
        self.load_model()

    def load_model(self):
        if os.path.exists(self.trainer_path):
            try:
                self.recognizer.read(self.trainer_path)
                print("Model loaded.")
            except Exception as e:
                print(f"Error loading model: {e}")
                
    def get_face_crop(self, frame):
        """
        Returns (gray_face_crop, rect_coords) or (None, None)
        rect_coords: (x, y, w, h)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.detector.process(rgb_frame)
        
        if results.detections:
            # Get largest face
            # detection relative bounding box
            detection = results.detections[0] # Assume 1 face
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = frame.shape
            x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)
            
            # Padding/Margin to ensure full face
            # Ensure within bounds
            x = max(0, x)
            y = max(0, y)
            w = min(iw - x, w)
            h = min(ih - y, h)
            
            if w > 0 and h > 0:
                face_crop = frame[y:y+h, x:x+w]
                gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                return gray_crop, (x, y, w, h)
                
        return None, None

    def save_samples(self, user_id, samples):
        """
        Save list of face images for a user.
        samples: list of gray_scale face images
        """
        user_dir = os.path.join(self.dataset_path, str(user_id))
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            
        for i, face in enumerate(samples):
            path = os.path.join(user_dir, f"{i}.jpg")
            cv2.imwrite(path, face)

    def train_model(self):
        """
        Traverse dataset, load all images, train recognizer, save trainer.yml.
        """
        faces = []
        ids = []
        
        if not os.path.exists(self.dataset_path):
            print("No dataset found.")
            return

        try:
            for user_id in os.listdir(self.dataset_path):
                user_dir = os.path.join(self.dataset_path, user_id)
                if not os.path.isdir(user_dir):
                    continue
                    
                try:
                    uid = int(user_id)
                except ValueError:
                    continue

                for file_name in os.listdir(user_dir):
                    if file_name.endswith("jpg"):
                        path = os.path.join(user_dir, file_name)
                        try:
                            # Verify file size
                            if os.path.getsize(path) == 0:
                                continue
                                
                            face = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                            if face is not None and face.size > 0:
                                # Resize validation if needed, but usually LBPH handles it if consistent
                                faces.append(face)
                                ids.append(uid)
                        except Exception:
                            continue
            
            if faces:
                 # Explicitly cast IDs to int32 to avoid OpenCV C++ errors
                 ids_np = np.array(ids, dtype=np.int32)
                 self.recognizer.train(faces, ids_np)
                 self.recognizer.write(self.trainer_path)
                 print("Training complete and saved.")
            else:
                print("No data to train.")
        except Exception as e:
            print(f"Training Error: {e}")

    def recognize_face(self, frame):
        """
        Returns: user_id, confidence, location
        """
        gray_face, rect = self.get_face_crop(frame)
        if gray_face is None:
            return None, 0, None
            
        # Predict
        try:
            # confidence in LBPH: 0 is perfect match, higher is worse.
            # Usually < 50 is good, > 80 is unknown.
            id_, conf = self.recognizer.predict(gray_face)
            
            # Map confidence to standard 0-1 (inverse)
            # Or just return raw
            return id_, conf, rect
        except Exception as e:
            # Model not trained yet
            return None, 100, rect
