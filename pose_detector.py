# pose_detector.py
import cv2
import mediapipe as mp
import numpy as np

class PoseDetector:
    def __init__(self, mode=False, model_complexity=1, smooth_landmarks=True, enable_segmentation=False, smooth_segmentation=True,
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):
        # Inizializza i parametri per il rilevamento della posa
        self.mode = mode
        self.model_complexity = model_complexity
        self.smooth_landmarks = smooth_landmarks
        self.enable_segmentation = enable_segmentation
        self.smooth_segmentation = smooth_segmentation
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

        # Configura MediaPipe per il rilevamento della posa
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5,
                                     min_tracking_confidence=0.5,
                                     enable_segmentation=False,
                                     model_complexity=1)
        self.mp_draw = mp.solutions.drawing_utils
        self.results = None

        # Colori per la posa dell'utente
        self.color_correct = (0, 255, 0)      # Verde
        self.color_incorrect = (0, 0, 255)    # Rosso
        self.color_neutral = (255, 255, 0)    # Giallo/Ciano

        # Colore per i punti target successivi
        self.color_target = (0, 255, 255) # Giallo/Ciano per i punti target

    def find_pose(self, img):
        """
        Elabora l'immagine per trovare i landmark della posa, ma non disegna nulla.
        Salva i risultati nell'attributo 'self.results'.
        """
        # CORREZIONE: Rimosso il doppio ritaglio. Ora 'img' è già l'area video corretta.
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)
        return self.results

    def draw_user_pose(self, img, exercise_success=None):
        """
        Disegna i landmark dell'utente e un bordo colorato sull'immagine
        in base ai risultati salvati.
        """
        h, w, _ = img.shape
        video_width = int(w * 0.8)
        img_to_draw_on = img[:, :video_width]

        current_color = self.color_neutral
        if exercise_success is not None:
            current_color = self.color_correct if exercise_success else self.color_incorrect

        border_thickness = 10
        if exercise_success is not None:
            overlay = img_to_draw_on.copy()
            h_vid, w_vid = img_to_draw_on.shape[:2]
            cv2.rectangle(overlay, (0, 0), (w_vid, h_vid), current_color, border_thickness)
            img_to_draw_on = cv2.addWeighted(overlay, 0.3, img_to_draw_on, 0.7, 0)

        if self.results and self.results.pose_landmarks:
            landmark_drawing_spec = self.mp_draw.DrawingSpec(
                color=current_color, thickness=1, circle_radius=3
            )
            connection_drawing_spec = self.mp_draw.DrawingSpec(
                color=current_color, thickness=2
            )
            self.mp_draw.draw_landmarks(
                img_to_draw_on,
                self.results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec,
                connection_drawing_spec
            )
        img[:, :video_width] = img_to_draw_on
        return img

    def draw_error_skeleton(self, img):
        """
        Disegna lo scheletro dell'utente (landmark e connessioni) in rosso
        in modo marcato sull'immagine fornita, limitatamente all'area video.
        """
        h, w, _ = img.shape
        video_width = int(w * 0.8)
        # Isola l'area video e crea una copia per disegnarci sopra
        img_to_draw_on = img[:, :video_width].copy()

        if self.results and self.results.pose_landmarks:
            red_color = (0, 0, 255) # BGR per Rosso
            landmark_drawing_spec = self.mp_draw.DrawingSpec(
                color=red_color, thickness=2, circle_radius=4
            )
            connection_drawing_spec = self.mp_draw.DrawingSpec(
                color=red_color, thickness=3
            )
            self.mp_draw.draw_landmarks(
                img_to_draw_on,
                self.results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec,
                connection_drawing_spec
            )
        # Ricombina l'immagine con lo scheletro rosso nell'immagine originale
        img_with_skeleton = img.copy()
        img_with_skeleton[:, :video_width] = img_to_draw_on
        return img_with_skeleton

    def draw_squat_depth_widget(self, img, squat_range_info):
        """
        Disegna un widget sul lato destro per visualizzare la profondità dello squat.
        """
        if squat_range_info['current_hip_y'] is None:
            return img

        h, w, _ = img.shape
        
        # Definisci l'area del widget (il 20% destro dello schermo)
        panel_width = w - int(w * 0.8)
        panel_x_start = int(w * 0.8)
        
        # Disegna lo sfondo nero del pannello
        cv2.rectangle(img, (panel_x_start, 0), (w, h), (0, 0, 0), -1)

        # Estrai i dati di profondità
        current_y_norm = squat_range_info['current_hip_y']
        upper_bound_norm = squat_range_info['upper_bound_y']
        lower_bound_norm = squat_range_info['lower_bound_y']

        # Mappa le coordinate normalizzate all'altezza del pannello
        upper_px = int(upper_bound_norm * h)
        lower_px = int(lower_bound_norm * h)
        current_y_px = int(current_y_norm * h)

        # Disegna i rettangoli rossi per i limiti
        limit_color = (0, 0, 255) # Rosso
        cv2.rectangle(img, (panel_x_start, upper_px - 2), (w, upper_px + 2), limit_color, -1)
        cv2.rectangle(img, (panel_x_start, lower_px - 2), (w, lower_px + 2), limit_color, -1)

        # Determina il colore e la posizione del punto
        dot_color = (255, 255, 255) # Bianco di default
        is_out_of_bounds = False
        # NEW: Extract correct bound
        correct_bound_norm = squat_range_info['correct_bound_y']
        
        # MODIFIED: Draw correct bound (green line)
        if correct_bound_norm is not None:
            correct_bound_px = int(correct_bound_norm * h)
            cv2.rectangle(img, (panel_x_start, correct_bound_px - 2), 
                         (w, correct_bound_px + 2), (0, 255, 0), -1)  # Green
        if current_y_norm < upper_bound_norm or current_y_norm > lower_bound_norm:
            dot_color = (0, 0, 255) # Rosso se fuori dai limiti
            is_out_of_bounds = True
            
        dot_x = panel_x_start + panel_width // 2
        dot_radius = 8
        cv2.circle(img, (dot_x, current_y_px), dot_radius, dot_color, -1)

        # Se il punto è fuori, disegna la linea di distanza dal limite più vicino
        if is_out_of_bounds:
            line_color = (0, 0, 255) # Rosso
            line_thickness = 2
            if current_y_px < upper_px:
                # Disegna linea verso il limite superiore
                cv2.line(img, (dot_x, current_y_px), (dot_x, upper_px), line_color, line_thickness)
            elif current_y_px > lower_px:
                # Disegna linea verso il limite inferiore
                cv2.line(img, (dot_x, current_y_px), (dot_x, lower_px), line_color, line_thickness)

        return img

    def draw_target_landmarks(self, img, target_landmarks_dict):
        """
        Disegna i punti chiave target sull'immagine (nell'area video).
        """
        h, w_total, _ = img.shape
        w_vid = int(w_total * 0.8)
        
        target_radius = 10
        target_thickness = 2

        for lm_id, coords in target_landmarks_dict.items():
            # Le coordinate sono normalizzate, quindi le scaliamo per la larghezza del video
            x = int(coords[0] * w_vid) 
            y = int(coords[1] * h)
            
            if x < w_vid: # Assicurati di disegnare solo nell'area video
                cv2.circle(img, (x, y), target_radius, self.color_target, target_thickness, cv2.LINE_AA)
                cv2.line(img, (x - target_radius + 3, y), (x + target_radius - 3, y), self.color_target, target_thickness, cv2.LINE_AA)
                cv2.line(img, (x, y - target_radius + 3), (x, y + target_radius - 3), self.color_target, target_thickness, cv2.LINE_AA)
        return img

    def find_position(self, img):
        # Estrae le coordinate dei landmark dall'area video
        landmarks_list = {}
        if self.results and self.results.pose_landmarks:
            h, w, _ = img.shape # L'immagine passata è l'area video
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                if lm.visibility > 0.3:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    landmarks_list[id] = [cx, cy, lm.z, lm.visibility, lm.x, lm.y]
        return landmarks_list

    def calculate_angle(self, p1, p2, p3):
        p1, p2, p3 = np.array(p1[:2]), np.array(p2[:2]), np.array(p3[:2])
        radians = np.arctan2(p3[1]-p2[1], p3[0]-p2[0]) - \
                 np.arctan2(p1[1]-p2[1], p1[0]-p2[0])
        angle = np.abs(radians*180.0/np.pi)
        if angle > 180.0:
            angle = 360-angle
        return angle

    def release(self):
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()
            self.pose = None