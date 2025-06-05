import cv2
import mediapipe as mp
import numpy as np

class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5,
                                     min_tracking_confidence=0.5,
                                     enable_segmentation=False, # Disabilita per performance se non serve maschera
                                     model_complexity=1) # 0, 1, or 2. Higher = more accurate but slower.
        self.mp_draw = mp.solutions.drawing_utils
        # self.mp_draw_styles = mp.solutions.drawing_styles # Non usato direttamente

        self.color_correct = (0, 255, 0)
        self.color_incorrect = (0, 0, 255)
        self.color_neutral = (255, 255, 0) # Giallo/Ciano per neutro

    def find_pose(self, img, draw=True, exercise_success=None):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)

        current_color = self.color_neutral
        if exercise_success is not None:
            current_color = self.color_correct if exercise_success else self.color_incorrect

        if draw:
            # Disegna il bordo colorato
            border_thickness = 10
            h, w = img.shape[:2]
            
            # Per evitare che il bordo venga tagliato, disegnalo leggermente all'interno.
            # Il centro della linea del bordo sarà spostato verso l'interno.
            # pt1_offset = border_thickness // 2
            # pt2_offset_w = w - border_thickness // 2
            # pt2_offset_h = h - border_thickness // 2

            # Disegna il rettangolo di bordo sull'immagine originale (o su un overlay)
            # Se disegniamo direttamente su img, non serve addWeighted per il solo bordo
            if exercise_success is not None: # Applica bordo solo se c'è un feedback di successo/errore
                # Per far sì che l'intero spessore sia visibile, disegnamo N rettangoli sottili
                # o un singolo rettangolo spesso ma ci assicuriamo che i suoi limiti siano visibili.
                # Il modo più semplice per avere un bordo visibile di spessore T è disegnarlo
                # da (T/2, T/2) a (W-T/2, H-T/2) con spessore T.
                # Questo significa che il bordo si estenderà da 0 a T e da W-T a W.
                
                # Soluzione: Disegna il bordo su un overlay che viene poi fuso.
                # Per garantire che il bordo sia completamente visibile e non "tagliato" ai lati:
                # Il rettangolo di OpenCV viene disegnato con il centro della linea sulle coordinate date.
                # Quindi, se disegniamo da (0,0) a (w,h) con spessore 10, 5 pixel sono "fuori" dall'immagine.
                # Disegniamo il rettangolo in modo che i suoi estremi siano all'interno.
                # Punto iniziale (x1,y1) e finale (x2,y2) per il rettangolo.
                # Lo spessore si estende t/2 da ogni lato della linea.
                # Per avere un bordo visibile di spessore 'border_thickness',
                # il centro della linea del bordo deve essere a border_thickness/2 dai bordi dell'immagine.
                
                # Copia per l'overlay del bordo
                overlay = img.copy()
                
                # Rettangolo per il bordo: usa i punti che definiscono il centro della linea del bordo
                # Spostati all'interno di half_thickness per il primo punto
                # e all'esterno di half_thickness (rispetto al centro) per il secondo punto
                half_thickness = border_thickness // 2
                pt1_border = (half_thickness, half_thickness)
                pt2_border = (w - half_thickness, h - half_thickness)
                
                cv2.rectangle(overlay, pt1_border, pt2_border, current_color, border_thickness)
                img = cv2.addWeighted(overlay, 0.3, img, 0.7, 0) # Riduci alpha per bordo più tenue

            # Disegna i landmark della posa
            if self.results.pose_landmarks:
                landmark_drawing_spec = self.mp_draw.DrawingSpec(
                    color=current_color, thickness=1, circle_radius=3 # Cerchi più piccoli
                )
                connection_drawing_spec = self.mp_draw.DrawingSpec(
                    color=current_color, thickness=2
                )
                self.mp_draw.draw_landmarks(
                    img,
                    self.results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec,
                    connection_drawing_spec
                )
        return img

    def find_position(self, img): # img non è usato qui, ma passato per consistenza
        landmarks_list = {}
        if self.results and self.results.pose_landmarks:
            # Considera tutti i landmark disponibili se necessario, o filtra
            # body_landmarks_indices = [11, 12, 23, 24, 25, 26, 27, 28] # Esempio
            h, w, _ = img.shape # Prendi le dimensioni dall'immagine passata
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                # Filtra per i landmark che ti interessano se non li vuoi tutti
                # if id not in body_landmarks_indices:
                # continue
                
                # Controlla visibilità prima di usare il landmark (anche se MediaPipe lo fa)
                if lm.visibility > 0.3: # Soglia di visibilità, puoi regolarla
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    landmarks_list[id] = [cx, cy, lm.z, lm.visibility] # Aggiungi z e visibilità
                # else:
                    # landmarks_list[id] = [None, None, None, lm.visibility] # Segna come non affidabile
        return landmarks_list


    def calculate_angle(self, p1, p2, p3):
        p1, p2, p3 = np.array(p1[:2]), np.array(p2[:2]), np.array(p3[:2]) # Usa solo x,y per angolo 2D
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