import os
import argparse
import cv2
import numpy as np
import pandas as pd
import pytesseract
# Open the video file

def main():
    parser = argparse.ArgumentParser(description='blame cli tool')
    parser.add_argument('--video', action='store', help='video filepath', default='')
    parser.add_argument('--output-dir', action='store', help='output dir path')
    args = parser.parse_args()
    video_filepath = args.video
    output_dir = args.output_dir

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    video_capture = cv2.VideoCapture(video_filepath)

    # Check if the video file was opened successfully
    if not video_capture.isOpened():
        print("Error: Could not open video file.")
        exit()

    video_fps = video_capture.get(cv2.CAP_PROP_FPS)
    # print what is the video FPS
    print(f'video_fps: {video_fps}')
    voting_dict = {}
    # Loop through each frame of the video
    frame_count = 0
    while True:
        # Read the next frame
        ret, frame = video_capture.read()

        # If the frame was not read successfully, we've reached the end of the video
        if not ret:
            break

        time = np.floor(frame_count / video_fps)
        # Increment the frame count
        frame_count += 1

        # Save the frame as an image (adjust the filename format as needed)
        image_filename = os.path.join(output_dir, f'f_{frame_count}_raw.jpg')
        cv2.imwrite(image_filename, frame)

        # Define the coordinates of the top-left and bottom-right corners of the rectangle
        x_ratio_top, y_ratio_top = 0.96, 0.27
        x_ration_bottom, y_ration_bottom = 0.99 ,0.31
        top_left = int(np.floor(frame.shape[1] * x_ratio_top)), int(np.floor(frame.shape[0] * y_ratio_top))
        bottom_right = int(np.floor(frame.shape[1] * x_ration_bottom)), int(np.floor(frame.shape[0] * y_ration_bottom))
        # bottom_right = (837, 120)  # Adjust these values as needed
        roi_x = top_left[0]
        roi_width = bottom_right[0] - top_left[0]
        roi_y = top_left[1]
        roi_height = bottom_right[1] - top_left[1]

        roi = frame[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width]
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        image_filename = os.path.join(output_dir, f'f_{frame_count}_ping.jpg')
        cv2.imwrite(image_filename, gray_roi)

        color = (255, 0, 0)  # Blue: (B, G, R)

        # Define the thickness of the rectangle outline (use -1 for a filled rectangle)
        thickness = 2

        # Draw the rectangle on the frame
        cv2.rectangle(frame, top_left, bottom_right, color, thickness)
        image_filename = os.path.join(output_dir, f'f_{frame_count}_raw_rect_ping.jpg')
        cv2.imwrite(image_filename, frame)

        x_ratio_top, y_ratio_top = 0.001, 0.300
        x_ration_bottom, y_ration_bottom = 0.260 ,0.450
        top_left = int(np.floor(frame.shape[1] * x_ratio_top)), int(np.floor(frame.shape[0] * y_ratio_top))
        bottom_right = int(np.floor(frame.shape[1] * x_ration_bottom)), int(np.floor(frame.shape[0] * y_ration_bottom))
        
        roi_x = top_left[0]
        roi_width = bottom_right[0] - top_left[0]
        roi_y = top_left[1]
        roi_height = bottom_right[1] - top_left[1]

        roi = frame[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width]
        gray_roi2 = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        image_filename = image_filename = os.path.join(output_dir, f'f_{frame_count}_kill.jpg')
        cv2.imwrite(image_filename, gray_roi2)
        
        # create a yellow mask on gray_roi2
        
        # extracted_text = pytesseract.image_to_string(gray_roi2, config="-c tessedit_char_whitelist=[eRQ8E+TDE3 --psm 13").strip()
        # if len(extracted_text) > 5:
        #     print(f'kill extracted_text: {extracted_text}')

        # Use OCR to extract text from the green text region
        max_gray = gray_roi.max() 
        min_grap = gray_roi.min()
        if max_gray - min_grap < 100:
            continue
        elif gray_roi.mean() > 120:
            continue

        # percentile_90 = np.percentile(gray_roi, 90)
        # mask = gray_roi < percentile_90
        # gray_roi[mask] = 0
        
        # filter out the non green color
        # gray_roi
        
        ping_mask_filename = os.path.join(output_dir, f'f_{frame_count}_ping_mask.jpg')
        cv2.imwrite(ping_mask_filename, gray_roi)

        # Define the color of the rectangle in BGR format (e.g., blue color)
        color = (255, 0, 0)  # Blue: (B, G, R)

        # Define the thickness of the rectangle outline (use -1 for a filled rectangle)
        thickness = 2

        # Draw the rectangle on the frame
        cv2.rectangle(frame, top_left, bottom_right, color, thickness)
        image_filename = image_filename = os.path.join(output_dir, f'f_{frame_count}_rect_kill.jpg')
        cv2.imwrite(image_filename, frame)
        # Get the shape of the frame
        frame_height, frame_width, num_channels = frame.shape

        # filter out the non green color
        # only_green = 
        green_image_filename = os.path.join(output_dir, f'f_green_{frame_count}_kill.jpg')
        cv2.imwrite(green_image_filename, only_green)

        extracted_text = pytesseract.image_to_string(gray_roi, config="-c tessedit_char_whitelist=0123456789 --psm 13").strip()
        if extracted_text:
            if len(extracted_text) > 3:
                current_latency = int(extracted_text[:3])
            else:
                current_latency = int(extracted_text)

            if current_latency > 200:
                current_latency = int(extracted_text[:2])

            if current_latency < 50:
                continue
            
            if time in voting_dict:
                voting_dict[time].append(current_latency)
            else:
                voting_dict[time] = [current_latency]
            
            print(f'time: {time} frame #{frame_count}: extracted_text: {extracted_text}, current_latency: {current_latency}')

    # Release the video capture object and close any open windows
    video_capture.release()
    cv2.destroyAllWindows()

    # Print the total number of frames in the video
    print(f"Total frames: {frame_count}")

    game_log = []
    for time, latency_list in voting_dict.items():
        # set latency to be the most common value
        latency = max(set(latency_list), key=latency_list.count)
        game_log.append({'time': time, 'latency': latency})
    game_log_csv = os.path.join(output_dir, 'game_log.csv')
    game_df = pd.DataFrame.from_dict(game_log)
    game_df.to_csv(game_log_csv, index=False)


if __name__ == "__main__":
    main()
