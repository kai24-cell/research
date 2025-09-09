import boto3 as sdk
import time
import subprocess
import os
s3operate=sdk.client("s3")
bucket ="rescorr"

#CPU高負荷
def CPUtra(core=None,donetime=5):
    basiccore =1#コア数1
    if core is None:
        core = os.core() or basiccore
    createfile = f"CPUtraffic{int(time.time())}.log" #ファイル名被り対策にtime使ってる
    try:
        with open(createfile, "w") as wfile:
            wfile.write("start,core:{core},donetime:{donetime}.\n")
            command =subprocess.run(["stress","--cpu",str(core),"--timeout",str(donetime)])
            print(f"Executing command: {' '.join(command)}")
            subprocess.run(command, check=True)
            wfile.write("finish.\n")
    except FileNotFoundError:
        print("nofile")
        return None
    except subprocess.CalledProcessError:
        print("cannt do command")
        return None
    return createfile

#ネットワーク切断
def Netkill(interface="enX0",waittime=5):
    createfile = f"Networkkill{int(time.time())}.log" #ファイル名被り対策にtime使ってる
    down =["sudo", "ip", "link", "set", interface, "down"]
    up=["sudo", "ip", "link", "set", interface, "up"]
    try:
        with open(createfile,"w") as wfile:
            wfile.write("start")
            wfile.flush()
            subprocess.run(down,check=True, stdout=wfile, stderr=wfile)
            time.sleep(waittime)      
    except FileNotFoundError:
            print("nofile")
            return None
    except subprocess.CalledProcessError:
        print("cannt do command")
    except KeyboardInterrupt:
        print("canceled")
    finally:
        try:
            subprocess.run(up,check=True, stdout=wfile, stderr=wfile,text=True)
            print("network success up")
        except Exception as dangerouserr:
            print("bigerr:{dangerouserr}")
            return None
    with open(createfile,"a"):
        wfile.write("finish")
    return createfile
#プロセスクラッシュ
def Processcra():
    createfile = f"ProcessCrash{int(time.time())}.log" #ファイル名被り対策にtime使ってる
    with open(createfile,"w") as wfile:
        wfile.write("start")
        subprocess.run(["kill", "-9", "99999"], wfile, wfile)
        wfile.write("finish")
    return createfile

if __name__ =="__main__":
    netinterface ="enX0"
    file =Netkill(netinterface,10)
    #file =CPUtra(2,5)
    #file =Netkill(netinterface,10)
    s3operate.upload_file(file,bucket,file)
    os.remove(file)

