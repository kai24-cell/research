import math
import time
#プロセスクラッシュをするためのプロセス部分
try:
    i=0
    while True:
        x+=math.sqrt(i)#計算自体に意味は無い。ただ計算してCPUを使わせたい
        i+=1
        time.sleep(0.01)
except KeyboardInterrupt:
    print("process cancell")
