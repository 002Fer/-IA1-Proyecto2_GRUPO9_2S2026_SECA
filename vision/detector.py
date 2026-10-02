from vision.camera import Camera
from vision.landmarks import HandLandmarks
from vision.pose import PoseLandmarks
from vision.gestures import GestureRecognizer

class VisionDetector:

    def __init__(
        self,
        camera_index=0,
        hand_model_path="models/hand_landmarker.task",
        pose_model_path="models/pose_landmarker.task"
    ):
        self.camera = Camera(camera_index)
        self.hand_detector = HandLandmarks(
            model_path=hand_model_path
        )
        self.pose_detector = PoseLandmarks(
            model_path=pose_model_path
        )
        self.gesture_recognizer = GestureRecognizer()

    def open(self):
        self.camera.open()

    #Probabilidades
    def calculate_gesture_confidence(
        self,
        gesture,
        hand_landmarks=None,
        pose_landmarks=None
    ):

        if gesture == "UNKNOWN":
            return 0.0

        # Brazos cruzados
        if gesture == "ARMS_CROSSED":
            if pose_landmarks is None or len(pose_landmarks) < 17:
                return 0.0

            ls, rs = pose_landmarks[11], pose_landmarks[12]
            le, re = pose_landmarks[13], pose_landmarks[14]
            lw, rw = pose_landmarks[15], pose_landmarks[16]

            center_x = (ls.x + rs.x) / 2
            shoulder_width = abs(ls.x - rs.x)

            if shoulder_width == 0:
                return 0.0

            center_ratio = (abs(lw.x - center_x) + abs(rw.x - center_x)) / (2 * shoulder_width)

            center_score = max(0.0, min(1.0, 1.0 - center_ratio))

            elbows_score = 1.0
            if le.y <= ls.y:
                elbows_score -= 0.5
            if re.y <= rs.y:
                elbows_score -= 0.5

            wrists_score = 1.0
            if lw.y <= ls.y:
                wrists_score -= 0.5
            if rw.y <= rs.y:
                wrists_score -= 0.5

            score = (
                center_score * 0.50
                + max(elbows_score, 0.0) * 0.25
                + max(wrists_score, 0.0) * 0.25
            )

            return round(min(0.70 + score * 0.25, 0.95), 2)

        if hand_landmarks is None or len(hand_landmarks) < 21:
            return 0.0

        # Índice arriba / abajo
        if gesture in ("INDEX_UP", "INDEX_DOWN"):
            tip, pip = hand_landmarks[8], hand_landmarks[6]
            dx, dy = abs(tip.x - pip.x), abs(tip.y - pip.y)
            total = dx + dy

            if total == 0:
                return 0.0

            vertical_ratio = dy / total
            confidence = 0.75 + (vertical_ratio - 0.5) * 0.40

            return round(max(0.75, min(confidence, 0.95)), 2)

        # Señalar izquierda / derecha
        if gesture in ("POINT_LEFT", "POINT_RIGHT"):
            tip, pip = hand_landmarks[8], hand_landmarks[6]
            dx, dy = abs(tip.x - pip.x), abs(tip.y - pip.y)
            total = dx + dy

            if total == 0:
                return 0.0

            horizontal_ratio = dx / total
            confidence = 0.75 + (horizontal_ratio - 0.5) * 0.40

            return round(max(0.75, min(confidence, 0.95)), 2)

        # Pulgar arriba / abajo
        if gesture in ("THUMBS_UP", "THUMBS_DOWN"):
            tip, ip, mcp = (
                hand_landmarks[4],
                hand_landmarks[3],
                hand_landmarks[2]
            )

            extension = self.gesture_recognizer.distance(tip, mcp)
            segment = self.gesture_recognizer.distance(ip, mcp)

            if segment == 0:
                return 0.0

            extension_score = max(0.0, min(extension / segment / 1.5, 1.0))

            vertical = abs(tip.y - mcp.y)
            horizontal = abs(tip.x - mcp.x)
            total = vertical + horizontal

            if total == 0:
                return 0.0

            direction_score = vertical / total
            score = extension_score * 0.60 + direction_score * 0.40

            return round(min(0.75 + score * 0.20, 0.95), 2)

        # Mano levantada
        if gesture == "HAND_RAISED":
            wrist = hand_landmarks[0]
            fingertips = [
                hand_landmarks[8],
                hand_landmarks[12],
                hand_landmarks[16],
                hand_landmarks[20]
            ]

            average_distance = sum(
                self.gesture_recognizer.distance(finger, wrist)
                for finger in fingertips
            ) / len(fingertips)

            openness_score = max(
                0.0,
                min(average_distance / 0.35, 1.0)
            )
            return round(min(0.75 + openness_score * 0.20, 0.95), 2)

        # Escritura
        if gesture == "WRITE_GESTURE":
            return 0.85

        return 0.0


    def process(self):
        frame = self.camera.read()
        
        # 1. PROCESAR MANOS
        hand_results = (
            self.hand_detector.process(frame)
        )
        
        # 2. PROCESAR POSE
        pose_results = (
            self.pose_detector.process(frame)
        )
        if pose_results.pose_landmarks:
            pose_landmarks = (
                pose_results.pose_landmarks[0]
            )
            person_detected = (
                self.gesture_recognizer
                .update_person_presence(
                    pose_landmarks
                )
            )
            proximity = (
                self.gesture_recognizer
                .update_proximity(
                    pose_landmarks
                )
            )
        else:
            pose_landmarks = None
            person_detected = (
                self.gesture_recognizer
                .update_person_presence(
                    None
                )
            )
            proximity = (
                self.gesture_recognizer
                .update_proximity(
                    None
                )
            )

        # 3. RESULTADO INICIAL
        gesture = "UNKNOWN"
        confidence = 0.0
        
        # 4. BRAZOS CRUZADOS
        if pose_landmarks is not None:
            arms_crossed = (
                self.gesture_recognizer
                .is_arms_crossed(
                    pose_landmarks
                )
            )
            if arms_crossed:
                gesture = "ARMS_CROSSED"
                confidence = (
                    self.calculate_gesture_confidence(
                        gesture,
                        pose_landmarks=pose_landmarks
                    )
                )
        
        # 5. GESTOS DE MANO
        if (
            gesture == "UNKNOWN"
            and hand_results.hand_landmarks
        ):
            hand_landmarks = (
                hand_results.hand_landmarks[0]
            )

            # ----------------------------------------------
            # ESCRITURA
            index_extended = (
                self.gesture_recognizer
                .index_extended(
                    hand_landmarks
                )
            )
            if index_extended:
                writing = (
                    self.gesture_recognizer
                    .update_write_gesture(
                        hand_landmarks
                    )
                )
                if writing:
                    gesture = "WRITE_GESTURE"
                    confidence = (
                        self.calculate_gesture_confidence(
                            gesture,
                            hand_landmarks
                            =hand_landmarks
                        )
                    )
            else:
                self.gesture_recognizer.index_history.clear()
                self.gesture_recognizer.write_detected = False

            # ----------------------------------------------
            # GESTOS ESTÁTICOS

            if gesture == "UNKNOWN":
                result = (
                    self.gesture_recognizer
                    .recognize(
                        hand_landmarks
                    )
                )
                gesture = result["gesture"]
                confidence = (
                    self.calculate_gesture_confidence(
                        gesture,
                        hand_landmarks=hand_landmarks
                    )
                )
        
        # 6. NO HAY MANO
        elif not hand_results.hand_landmarks:
            self.gesture_recognizer.index_history.clear()
            self.gesture_recognizer.write_detected = False

        # 7. LIMPIAR RESULTADO SI NO HAY PERSONA CONFIRMADA
        if not person_detected:

            gesture = "UNKNOWN"
            confidence = 0.0
            proximity = "UNKNOWN"

        # 8. RESULTADO INTEGRADO
        return {
            "person_detected": person_detected,
            "gesture": gesture,
            "confidence": confidence,
            "proximity": proximity,
            "frame": frame,
            "hand_results": hand_results,
            "pose_results": pose_results
        }

    def get_perception(self, result):
        return {
            "person_detected": result["person_detected"],
            "gesture": result["gesture"],
            "confidence": result["confidence"],
            "proximity": result["proximity"]
        }

    def release(self):
        self.camera.release()
        self.hand_detector.close()
        self.pose_detector.close()
