import boto3 as sdk
import time
import subprocess
import os
import signal
from botocore.exceptions import NoCredentialsError, BotoCoreError 


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
def Processcra(PROCESSSCRIPT ="process.py",monitoringtime =30):
    
    createfile = f"ProcessCrash{int(time.time())}.log" #ファイル名被り対策にtime使ってる  
    try:      
        with open(createfile,"w") as wfile:
            wfile.write("start\n")
            try:
                PROCESS = subprocess.Popen(["python","-u",PROCESSSCRIPT])
                pid =PROCESS.pid
                wfile.write(f"pid:{pid}\n")
            except FileNotFoundError:
                print("nofile")
                wfile.write(f"notfound{PROCESSSCRIPT}\n")
                return None
        wfile.write(f"monitoring:{monitoringtime}\n")
        wfile.flush()
        time.sleep(monitoringtime)
    except KeyboardInterrupt:
        print("process canceled")
    finally:
        if pid:
            print("ready crash")
            try:
                os.kill(pid,signal.SIGKILL)
                print("kill success")
                with open(createfile,"a") as wfile:
                    wfile.write(f"kill success {pid} ")
            except ProcessLookupError:
                with open(createfile,"a") as wfile:
                    wfile.write(f"already ended:{pid} ")
        else:
            print("PID is not start")
    with open(createfile, "a") as wfile:
        wfile.write("finish\n")
    return createfile
if __name__ =="__main__":
    netinterface ="enX0"
    #file =Netkill(netinterface,10)
try:
    s3operate=sdk.client("s3")
    bucket ="rescorr"
    logfile =Processcra(PROCESSSCRIPT="process.py",monitoringtime=10)
except NoCredentialsError:
    print("AWS account not found")
    exit(1)
if logfile:
    try:
        s3operate.upload_file(File_name = logfile,Bucket=bucket,Objectname =logfile)
        os.remove(logfile)
    except FileNotFoundError:
        print("dont found upload file")
    except BotoCoreError:
        print("error about boto3")