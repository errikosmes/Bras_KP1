import cv2
import numpy as np 

#define the events for the 
# mouse_click. 
def mouse_click(event, x, y, flags, param): 

    global coord

    # to check if left mouse  
    # button was clicked 
    if event == cv2.EVENT_LBUTTONDOWN:
        coord = [x, y]; 
  
# init
img = np.zeros((512,512,3), np.uint8)
coord = [0, 0]
  
# show image 
cv2.imshow('image', img)         
  
cv2.setMouseCallback('image', mouse_click) 
   
# keep looping until the 'q' key is pressed
while True:
	# display the image and wait for a keypress
    cv2.imshow("image", img)
    key = cv2.waitKey(1) & 0xFF
    print(coord)

  
# close all the opened windows. 
cv2.destroyAllWindows() 