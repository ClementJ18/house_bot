import cv2
import numpy as np
import random

img = cv2.imread('map.png')
img_gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
ret, thresh = cv2.threshold(img_gray, 127, 255,0)
contours,hierarchy = cv2.findContours(thresh,2,1)
# cnt = contours[0]
number = 0
to_ignore = [394, 395, 389]

for c in contours:
    # compute the center of the contour
    if not number in to_ignore:
        M = cv2.moments(c)
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])

        # if not number in [394, 395, 391, 339, 309]:
        cv2.drawContours(img, [c], -1, (0, 255, 0), 2)
        cv2.circle(img, (cX, cY), 7, (255, 255, 255), -1)
        cv2.putText(img, str(number), (cX - 6, cY - 6),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    number += 1

# img = cv2.resize(img, (1280, 720))
img = cv2.resize(img, (1920, 1280))
cv2.imshow('img', img)
cv2.waitKey(0)
cv2.destroyAllWindows()