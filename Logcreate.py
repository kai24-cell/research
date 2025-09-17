import boto3 as sdk
import time
import subprocess
import os
import signal
from botocore.exceptions import NoCredentialsError, BotoCoreError 
import psutil#pip install pstil
import threading

#CPU高負荷
def stress_cpu(core=None,donetime=5):
    """
    stressコマンドを使い、指定されたコア数と時間でCPUに負荷をかける。
    """
    try:         
        command =["stress","--cpu",str(core),"--timeout",str(donetime)]
        print(f"Executing command: {' '.join(command)}")
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print("nofile")
        return None
    except subprocess.CalledProcessError:
        print("cannt do command")
        return None
#ネットワーク切断
def disrupt_network(interface="enX0",waittime=5):
    """
    指定されたネットワークインターフェースを一度ダウンさせ、指定時間後にアップさせる。
    注意: この関数は 'sudo' を必要とする。パスワードなしで 'ip' コマンドが実行できるか確認。
    """
    createfile = f"disrupt_network{int(time.time())}.log" #ファイル名被り対策にtime使ってる
    down =["sudo", "ip", "link", "set", interface, "down"]
    up=["sudo", "ip", "link", "set", interface, "up"]
    try:
        with open(createfile,"w") as wfile:
            wfile.write("start")
            wfile.flush()
            subprocess.run(down, check=True, stdout=wfile, stderr=wfile)
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
            result=subprocess.run(up,check=True, capture_output=True,text=True)#デバック用detail
            print("network success up")
            with open(createfile,"a") as wfile:
                wfile.write("finish")
        except Exception as dangerouserr:
            print(f"bigerr:{dangerouserr}\n")
    return createfile
#プロセスクラッシュ
def crash_process(process_script ="process.py",monitoringtime =30):
    """
    指定されたPythonスクリプトをサブプロセスとして起動し、一定時間後にSIGKILLで強制終了させる。
    """
    createfile = f"crash_process{int(time.time())}.log" #ファイル名被り対策にtime使ってる  
    pid=None
    try:      
        with open(createfile,"w") as wfile:
            wfile.write("start\n")
            try:
                PROCESS = subprocess.Popen(["python","-u",process_script])
                pid =PROCESS.pid
                wfile.write(f"pid:{pid}\n")
            except FileNotFoundError:
                print("nofile")
                wfile.write(f"notfound{process_script}\n")
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
#データ記録クラス   
class MetricsCollector(threading.Thread):
    def __init__(self,interval=1.0):
        super().__init__()
        self.interval=interval
        self.correct_log = []
        self._stop_event =threading.Event()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_net_io =psutil.net_io_counters()
    def run(self):
        print("start")
        while not self._stop_event.is_set():
            timestanp = time.time()
            cpu_percent = psutil.cpu_percent
            memory_percent = psutil.virtual_memory().percent

            self.correct_log({
                "timestanp":timestanp,
                "cpu_percent":cpu_percent,
                "memory_percent":memory_percent,
            })
            time.sleep(self.interval)
    def stop(self):
        self._stop_event.set()
if __name__ =="__main__":
    net_interface ="enX0"
try:
    s3operate=sdk.client("s3")
    bucket ="rescorr"
    collector = MetricsCollector(interval=1.0)

    #stress_cpuの実行部分
    collector.start()
    createfile = f"stress_cpu{int(time.time())}.log" #ファイル名被り対策にtime使ってる
    with open(createfile, "w") as wfile:
        basiccore =1#コア数1
        core =1#コア数ここで指定
        donetime=10
        if core is None:
            core = os.cpu_count() or basiccore
        wfile.write(f"start,core:{core},donetime:{donetime}.\n")
        stress_cpu(core,donetime)
    
        collector.stop()
        collector.join()
        print(f"Collected data:{len(collector.correct_log)}")
        for x in collector.correct_log:
            print(x)
            wfile.write(f"{x}\n")
        wfile.write("finish.\n")

    logfile =crash_process(process_script="process.py",monitoringtime=10)
except NoCredentialsError:
    print("AWS account not found")
    exit(1)
if createfile:
    try:
        s3operate.upload_file(Filename = createfile,Bucket=bucket,Key =createfile)
        os.remove(createfile)
    except FileNotFoundError:
        print("dont found upload file")
    except BotoCoreError:
        print("error about boto3")