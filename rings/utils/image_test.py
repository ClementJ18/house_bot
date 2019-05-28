# import cv2
# import numpy as np
# font = cv2.FONT_HERSHEY_COMPLEX
# img = cv2.imread("rings/utils/map.png", cv2.IMREAD_GRAYSCALE)
# _, threshold = cv2.threshold(img, 240, 255, cv2.THRESH_BINARY)
# thing, contours = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

# for cnt in contours:
#     approx = cv2.approxPolyDP(cnt, 0.01*cv2.arcLength(cnt, True), True)
#     cv2.drawContours(img, [approx], 0, (0), 5)
#     x = approx.ravel()[0]
#     y = approx.ravel()[1]
#     cv2.putText(img, "Country", (x, y), font, 1, (0))

# cv2.imshow("shapes", img)
# cv2.imshow("Threshold", threshold)
# cv2.waitKey(0)
# cv2.destroyAllWindows()


import cv2
import numpy as np

img = cv2.imread('map.png')
img_gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
ret, thresh = cv2.threshold(img_gray, 127, 255,0)
contours,hierarchy = cv2.findContours(thresh,2,1)
# cnt = contours[0]

for cnt in contours:
    cv2.putText(img, "country", )

    hull = cv2.convexHull(cnt,returnPoints = False)
    defects = cv2.convexityDefects(cnt,hull)
    if defects is not None:
        for i in range(defects.shape[0]):
            s,e,f,d = defects[i,0]
            start = tuple(cnt[s][0])
            end = tuple(cnt[e][0])
            far = tuple(cnt[f][0])
            cv2.line(img,start,end,[0,255,0],2)
            cv2.circle(img,far,5,[0,0,255],-1)

img = cv2.resize(img, (1280, 720))
cv2.imshow('img',img)
cv2.waitKey(0)
cv2.destroyAllWindows()
