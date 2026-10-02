import cv2
from vision.detector import VisionDetector

def main():
    detector = VisionDetector()
    try:
        detector.open()
        print("VisionDetector iniciado.")
        print("Presiona Q para salir.")

        while True:
            # Procesar frame
            result = detector.process()

            # Obtener únicamente la percepción que expondrá el módulo de visión
            perception = detector.get_perception(result)

            # print("Percepción:", perception)   #<---- Imprime el JSON puro

            print(f"Persona: {perception['person_detected']} | "
                  f"Gesto: {perception['gesture']} | "
                  f"Confianza: {perception['confidence']} | "
                  f"Proximidad: {perception['proximity']}")

            # --------------------------------------
            # Visualización para pruebas
            frame = result["frame"]

            frame = detector.hand_detector.draw(
                frame,
                result["hand_results"]
            )
            frame = detector.pose_detector.draw(
                frame,
                result["pose_results"]
            )
            cv2.imshow(
                "AURA - Vision Detector",
                frame
            )
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        detector.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()