import sys
import time
import numpy as np
import cv2
import mss

# --- CONFIGURATION SETTINGS ---
PRIMARY_MONITOR_INDEX = 1    # The screen playing your movie
VIBRANCY_BOOST = 1.6         # Restored back to 1.6 to keep colors rich and vivid

# --- NON-LINEAR BRIGHTNESS (GAMMA) ---
# Lower value = brighter display. 
# 1.0 is completely untouched. 
# 0.55 makes darks/midtones much brighter without washing out colors into white.
GAMMA_VALUE = 0.55           

# --- ADAPTIVE TRANSITION SMOOTHING ---
SMOOTHING_ALPHA = 0.16       
# ------------------------------

def apply_gamma_and_vibrancy(img, saturation_scale, gamma):
    """
    Applies non-linear gamma correction to expand brightness safely 
    while preserving deep color profiles.
    """
    # Convert matrix to HSV color space
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    
    # 1. Apply Vibrancy Boost to Saturation channel
    hsv[:, :, 1] *= saturation_scale
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
    
    # 2. Apply Non-Linear Gamma Correction to Value (Brightness) channel
    # This prevents highlights from clipping into flat white blocks
    hsv[:, :, 2] = 255.0 * ((hsv[:, :, 2] / 255.0) ** gamma)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2], 0, 255)
    
    # Convert back to standard 8-bit BGR format
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def run_perfected_backlight():
    with mss.mss() as sct:
        monitors = sct.monitors
        
        if len(monitors) < 3:
            print("[-] Error: Dual/Multi monitors not detected via Spacedesk.")
            sys.exit(1)
            
        try:
            prim_mon = monitors[PRIMARY_MONITOR_INDEX]
        except IndexError:
            print(f"[-] Error: Invalid primary monitor index {PRIMARY_MONITOR_INDEX}.")
            sys.exit(1)

        backlight_monitors = []
        for i in range(1, len(monitors)):
            if i != PRIMARY_MONITOR_INDEX:
                backlight_monitors.append((i, monitors[i]))

        print("[+] Gamma-Corrected Ambient Engine Active!")
        print(f"[+] Sampling Primary Monitor [{PRIMARY_MONITOR_INDEX}]")
        
        for index, mon in backlight_monitors:
            window_name = f"Backlight_Display_Device_{index}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.moveWindow(window_name, mon["left"], mon["top"])

        downsample_size = (64, 36)
        previous_smoothed_state = None

        while True:
            # 1. Grab raw desktop pixels
            screenshot = sct.grab(prim_mon)
            frame = np.array(screenshot)[:, :, :3]

            # 2. Downsample early
            small_frame = cv2.resize(frame, downsample_size, interpolation=cv2.INTER_AREA)

            # 3. Apply the safe Gamma brightening engine
            enhanced_small = apply_gamma_and_vibrancy(small_frame, VIBRANCY_BOOST, GAMMA_VALUE)

            # 4. Standard spatial blur
            current_blurred_frame = cv2.GaussianBlur(enhanced_small, (25, 25), 0)

            # 5. Continuous Temporal Smoothing (EMA)
            if previous_smoothed_state is None:
                previous_smoothed_state = current_blurred_frame.astype(np.float32)
            else:
                cv2.accumulateWeighted(current_blurred_frame, previous_smoothed_state, SMOOTHING_ALPHA)

            smoothed_frame = cv2.convertScaleAbs(previous_smoothed_state)

            # 6. Horizontal Axis Flip (Mirroring for wall projection)
            mirrored_frame = cv2.flip(smoothed_frame, 1)

            # 7. Project across all active Spacedesk target monitors
            for index, mon in backlight_monitors:
                window_name = f"Backlight_Display_Device_{index}"
                target_size = (mon["width"], mon["height"])
                
                output_display = cv2.resize(mirrored_frame, target_size, interpolation=cv2.INTER_LINEAR)
                
                cv2.imshow(window_name, output_display)
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run_perfected_backlight()
