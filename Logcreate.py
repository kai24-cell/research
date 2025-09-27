import boto3 as sdk
import time
import subprocess
import os
import signal
from botocore.exceptions import NoCredentialsError, BotoCoreError 
import psutil#pip install pstil
import threading
from datetime import datetime
import csv

#CPU高負荷
def stress_cpu(core=None,duration=5):
    """
    stressコマンドを使い、指定されたコア数と時間でCPUに負荷をかける。
    """     
    command =["stress","--cpu",str(core),"--timeout",str(duration)]
    subprocess.run(command, check=True,capture_output=True)
#ネットワーク切断
def disrupt_network(interface="enX0",duration=5):
    """
    指定されたネットワークインターフェースを一度ダウンさせ、指定時間後にアップさせる。
    注意: この関数は 'sudo' を必要とする。パスワードなしで 'ip' コマンドが実行できるか確認。
    """
    down =["sudo", "ip", "link", "set", interface, "down"]
    up=["sudo", "ip", "link", "set", interface, "up"]
    try:
        subprocess.run(down, check=True, capture_output=True)
        time.sleep(duration)
    except subprocess.CalledProcessError:
         print("cannt do command")
    except KeyboardInterrupt:
        print("canceled")      
    finally:
        subprocess.run(up,check=True, capture_output=True)
#プロセスクラッシュ
def crash_process(process_script ="process.py",duration =30):
    """
    指定されたPythonスクリプトをサブプロセスとして起動し、一定時間後にSIGKILLで強制終了させる。
    """  
    process=None
    try:      
        process = subprocess.Popen(["python","-u",process_script])
        time.sleep(duration)
    finally:
        if process and process.poll() is None:
            os.kill(process.pid,signal.SIGKILL)
        elif process:
            print("  - Process had already terminated.")
        else:
            print("process is not started")
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
            timestanp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            #cpuメトリクス
            cpu_percent = psutil.cpu_percent()
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

            self.correct_log.append({
                "timestanp":timestanp,
                "cpu_percent":cpu_percent,
                "cpu_times_user":cpu_times.user,
                "cpu_times_system":cpu_times.system,
                "cpu_times_idle":cpu_times.idle,
                "cpu_times_iowait":cpu_times.iowait,#ローカルじゃテストできない。Linaxでしか実行できないから
                "load_avg_1m":load_avg[0],#1分
                "load_avg_5m":load_avg[1],#5分
                "load_avg_15m":load_avg[2],#15分
                "memory_percent":memory_percent,
                "swap_percent":swap_percent,
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
        collector.stop()
        collector.join()
    file_path =save_to_csv(collector.correct_log,csv_filename,local_dir)
    return file_path

if __name__ =="__main__":
    net_interface ="enX0"
    s3_bucket ="rescorr"
    LOCAL_LOG_DIR = "experiment_logs"
    try:
        s3operate=sdk.client("s3")

        #実行部分
        cpu_log_filepath = run_experiment(
            func = stress_cpu,
            args = {'core':1,'duration':15},
            type = 'cpu_stress',
            local_dir = LOCAL_LOG_DIR
        )
        if cpu_log_filepath:
            
            s3_key =  f"raw-data/cpu_stress/{os.path.basename(cpu_log_filepath)}"
            s3operate.upload_file(Filename = cpu_log_filepath,Bucket=s3_bucket,Key =s3_key)
            os.remove(cpu_log_filepath)

        network_log_filepath = run_experiment(
            func =disrupt_network,
            args ={'interface':net_interface,'duration':5},
            type = 'disrupt_network',
            local_dir = LOCAL_LOG_DIR
        )
        if network_log_filepath:

            s3_key =f"raw-data/disrupt_network/{os.path.basename(network_log_filepath)}"
            s3operate.upload_file(Filename = network_log_filepath,Bucket=s3_bucket,Key =s3_key)
            os.remove(network_log_filepath)

        process_log_filepath = run_experiment(
            func=crash_process,
            args={'process_script':"process.py",'duration': 30},
            type='crash_process',
            local_dir=LOCAL_LOG_DIR
        )
        if process_log_filepath:
            s3_key =f"raw-data/crash_process/{os.path.basename(process_log_filepath)}"
            s3operate.upload_file(Filename = process_log_filepath,Bucket=s3_bucket,Key =s3_key)
            os.remove(process_log_filepath)


    except NoCredentialsError:
            print("aws is not found")
    except FileNotFoundError:
            print("dont found upload file")
    except BotoCoreError:
            print("error about boto3")
