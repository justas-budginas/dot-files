import pyautogui as pg
import random
import time

#y = pg.size()
#x = pg.position()

#print ("size")
#print (y)
#print (x)
print ("Running...");

while True:
    pg.moveTo(80,406,4)
    pg.click()

    #here 60 refer to 60 seconds to hold up and then move the mouse cursor to a new location

    time.sleep(15)
    pg.moveTo(98,525,4)
    pg.click()
    time.sleep(60)
