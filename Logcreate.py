import boto3 as sdk
import time
import subprocess
import os
s3operate=sdk.client("s3")
bucket ="rescorr"

#CPU高負荷
def CPUtra(core=None,donetime=5):
    basiccore =1
    if core is None:
        core = os.core() or basiccore
    createfile = f"CPUtraffic{int(time.time())}.log" #ファイル名被り対策にtime使ってる
    try:
        with open(createfile, "w") as wfile:
            wfile.write("start,core:{core},donetime:{donetime}.\n")
            subprocess.run(["stress","--cpu",str(core),"--timeout",str(donetime)])
            print(f"Executing command: {' '.join(command)}")
            subprocess.run(command, check=True)
            wfile.write("finish.\n")
    except:
    return createfile

#ネットワーク切断
def Netkill():
    createfile = f"Networkkill{int(time.time())}.log" #ファイル名被り対策にtime使ってる
    waittime=5
    with open(createfile,"w") as wfile:
        wfile.write("start")
        subprocess.run(["sudo", "ip", "link", "set", "eth0", "down"], wfile, wfile)
        time.sleep(waittime)
        subprocess.run(["sudo", "ip", "link", "set", "eth0", "up"], wfile, wfile)
        wfile.write("finish")
    return createfile
#プロセスクラッシュ(疑似)
def Processcra():
    createfile = f"ProcessCrash{int(time.time())}.log" #ファイル名被り対策にtime使ってる
    with open(createfile,"w") as wfile:
        wfile.write("start")
        subprocess.run(["kill", "-9", "99999"], wfile, wfile)
        wfile.write("finish")
    return createfile