import boto3 as sdk
import time
import subprocess
import os
import signal
s3operate=sdk.client("s3")
bucket ="rescorr"
PROCESSSCRIPT ="process.py"

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
            detail=subprocess.run(up,check=True, capture_output=True,text=True)#デバック用detail
            print("network success up")
        except Exception as dangerouserr:
            print("bigerr:{dangerouserr}\n")
            return None
    with open(createfile,"a") as wfile:
        wfile.write("finish")
    return createfile
#プロセスクラッシュ
def Processcra():
    monitoringtime =30
    createfile = f"ProcessCrash{int(time.time())}.log" #ファイル名被り対策にtime使ってる        
    with open(createfile,"w") as wfile:
        wfile.write("start\n")
    try:
        PROCESS = subprocess.Popen(["python","-u",PROCESSSCRIPT])
        killprocess =PROCESS.pid
    except FileNotFoundError:
        print("nofile{PROCESSSCRIPT}")
        return None
    wfile.write("{PROCESSSCRIPT}killstart{killprocess}")
    time.sleep(monitoringtime)
    
    print("clash")
    wfile.write("{killprocess}\n")

    try:
        os.kill(killprocess,signal.SIGILL)
        wfile.write("kill process\n")
    except ProcessLookupError:
        wfile.write("process already ended")
    wfile.write("finish")
    return createfile

if __name__ =="__main__":
    netinterface ="enX0"
    file =Netkill(netinterface,10)
    s3operate.upload_file(file,bucket,file)
    os.remove(file)

