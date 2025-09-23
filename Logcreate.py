import boto3 as sdk
import time
import subprocess
import os
import signal
from botocore.exceptions import NoCredentialsError, BotoCoreError 
import psutil#pip install pstil
import threading
from datetime import datetime
import zoneinfo
import csv

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
            japan = zoneinfo.ZoneInfo("Asia/Tokyo")
            timestanp = datetime.now(japan).isoformat() 
            #cpuメトリクス
            cpu_percent = psutil.cpu_percent
            cpu_times = psutil.cpu_times_percent()#cpu使用時間
            load_avg = psutil.getloadavg()#処理待ちで何件タスクたまってるかの平均
            #メモリメトリクス
            memory_percent = psutil.virtual_memory().percent
            swap_percent = psutil.swap_memory().percent

            #ディスクI/Oレート (差分を計算) 
            current_disk_io = psutil.disk_io_counters()
            disk_read_rate = (current_disk_io.read_bytes - self.last_disk_io.read_bytes) / self.interval
            disk_write_rate = (current_disk_io.write_bytes - self.last_disk_io.write_bytes) / self.interval
            self.last_disk_io = current_disk_io
            
            #ネットワークI/Oレート (差分を計算)
            current_net_io = psutil.net_io_counters()
            net_sent_rate = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / self.interval
            net_recv_rate = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / self.interval
            self.last_net_io = current_net_io

            #プロセス数
            process_count = len(psutil.pids())

            self.correct_log({
                "timestanp":timestanp,
                "cpu_percent":cpu_percent,
                "cpu_times_user":cpu_times.user,
                "cpu_times_system":cpu_times.system,
                "cpu_times_idle":cpu_times.idle,
                "cpu_times_iowait":cpu_times.iowait,#ローカルじゃテストできない。Linaxでしか実行できないから
                "load_avg":load_avg[0],
                "memory_percent":memory_percent,
                "swap_percent":swap_percent,
                "current_disk_io":current_disk_io,
                "disk_read_rate":disk_read_rate,
                "disk_write_rate":disk_write_rate,
                "net_sent_rate":net_sent_rate,
                "net_recv_rate":net_recv_rate,
                "process_count":process_count,

            })
            time.sleep(self.interval)
    def stop(self):
        self._stop_event.set()
def save_to_csv(data,file_name,local_directry):
    if not data:
        print("no data")
        return
    os.makedirs(local_directry,exist_ok=True)
    filepath =os.path.join(local_directry,file_name)

    headers =data[0].keys()

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    return filepath
def run_experiment(func,args,type,local_dir):
    collector = MetricsCollector(interval=1.0)

    filename_time = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    csv_filename = f"{type}_{filename_time}.csv"

    try:
        collector.start()
        func(**args)
    except Exception as e:
        print(f"error{e}")
    finally:
        collector.join
        collector.stop
    file_path =save_to_csv(collector.correct_log,csv_filename,local_dir)
    return file_path

if __name__ =="__main__":
    net_interface ="enX0"
    s3_bucket ="rescorr"
    LOCAL_LOG_DIR = "experiment_logs"
    try:
        s3operate=sdk.client("s3")

        #実行部分
        experience_do = run_experiment{
            func = stress_cpu,
            args = {'core':1,'duration':15},
            type = 'cpu_stress',
            local_dir = LOCAL_LOG_DIR
        }
        if experience_do:
            
            s3_key = f""
            s3operate.upload_file(Filename = experience_do,Bucket=s3_bucket,Key =s3_key)
    except NoCredentialsError:
            print("aws is not found")
    except FileNotFoundError:
            print("dont found upload file")
    except BotoCoreError:
            print("error about boto3")
    finally:
            os.remove(experience_do)