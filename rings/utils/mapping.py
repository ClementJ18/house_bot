import cv2
import numpy as np
from collections import defaultdict
import psycopg2

conn = psycopg2.connect(dbname="postgres", user="postgres", password=dbpass)
cur = conn.cursor()

#create server cache
kingdom = defaultdict(list)
cur.execute("SELECT id, owner FROM houses.Lands;")
for g in cur.fetchall():
    kingdom[g[1]].append(g[0])


img = cv2.imread('map.png')
img_gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
ret, thresh = cv2.threshold(img_gray, 127, 255,0)
contours,hierarchy = cv2.findContours(thresh,2,1)
number = 0
kingdom_map = {contours.index(c): {c} for x in contours}


cv2.drawContours(img, [np.unique(np.concatenate(kingdom_map), axis=1)], -1, (0, 255, 0), 2)
img = cv2.resize(img, (1920, 1280))
cv2.imshow('img', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
