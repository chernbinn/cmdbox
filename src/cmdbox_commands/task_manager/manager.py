import os, sys
import json
import time
import atexit
import signal
from datetime import datetime
import subprocess
import atexit
import psutil
from pathlib import Path
from jinja2 import Template

TASKBM_DB = os.environ.get("TASKBM_DB", os.fspath(Path.home() / ".cmdbox"/ "task_manager"))
class TaskManager:
    def __init__(self):
        self.db_file = os.fspath(Path(TASKBM_DB) / "taskdb.json")
        self.log_dir = os.fspath(Path(TASKBM_DB) / "logs")

        os.makedirs(self.log_dir, exist_ok=True)
        self._init_db()
        atexit.register(self._cleanup)

    def _init_db(self):
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump({"tasks": {}}, f)

    def _save_db(self, data):
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_db(self):
        with open(self.db_file) as f:
            return json.load(f)

    def _generate_wrapper_script(self, task_id, command, db_file, log_file, name, until_succeed=True, interval=30, tee_out_error=False):
        template_path = os.path.join(os.path.dirname(__file__), "wrapper_template.py.j2")
        with open(template_path, "r", encoding="utf-8") as f:
            template = Template(f.read())

        rendered = template.render(
            task_id=task_id,
            command=command,
            db_file=db_file,
            log_file=log_file,
            name=name or command,
            until_succeed=until_succeed,
            interval=interval,
            tee_out_error=tee_out_error
        )
        return rendered

    def submit_task(self, command, name=None, until_succeed=False, interval=30, tee_out_error=False):
        timestamp = int(time.time())
        task_id = f"task_{timestamp}"
        log_file = os.path.join(self.log_dir, f"{task_id}.log")
        
        # 构造自维持脚本（解决进程生命周期问题）
        wrapper_script = self._generate_wrapper_script(
            task_id, command, self.db_file, log_file, 
            name or command, until_succeed, interval, tee_out_error
        )
        
        # 启动独立进程（不依赖Python主进程）
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        proc = subprocess.Popen(
            [sys.executable, "-c", wrapper_script],
            stdin=subprocess.DEVNULL,
            #stdout=subprocess.DEVNULL,
            #stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0,
            cwd=os.getcwd()
        )
        
        # 记录任务信息（此时PID为wrapper进程的PID）
        db = self._load_db()
        db["tasks"][task_id] = {
            "pid": proc.pid,
            "command": command,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "log_file": log_file,
            "name": name or command
        }
        self._save_db(db)
        return task_id, db["tasks"][task_id]

    def list_tasks(self):
        """列出所有任务"""
        db = self._load_db()
        return db["tasks"]
    
    def _answer_yes_no(self, question):
        while True:
            print(question + " (y/n)")
            choice = input().strip().lower()
            if choice in ["y", "n"]:
                return choice == "y"
            print("Invalid input. Please enter 'y' or 'n'.")
    
    def _remove_log_file(self, log_file):
        try:
            os.remove(log_file)
        except:
            pass

    def clean_tasks(self):
        """清理已完成任务"""
        db = self._load_db()
        delete_failed = None
        for task_id, task in list(db["tasks"].items()):
            if self._is_process_running(task["pid"]):
                continue
            
            if any([
                task["status"] == "killed",
                task["status"] == "completed"
            ]):
                del db["tasks"][task_id]
                if os.path.exists(task["log_file"]):
                    self._remove_log_file(task["log_file"])
            elif task["status"] == "failed":
                # 检查日志文件是否存在，不存在则删除任务
                if not os.path.exists(task["log_file"]):
                    del db["tasks"][task_id]
                else:
                    if delete_failed is None:
                        delete_failed = self._answer_yes_no(
                            "Found failed tasks. Do you want to delete them?"
                        )
                    if delete_failed:
                        print(f"Deleting \033[31m[failed]\033[0m task: {task_id}")  
                        del db["tasks"][task_id]
                        if os.path.exists(task["log_file"]):
                            self._remove_log_file(task["log_file"])
            elif not self._is_process_running(task["pid"]):
                print(f"Task pid({task['pid']}) have \033[31mterminated\033[0m: {task_id}")
                if self._answer_yes_no(f"Do you want to delete task: {task_id}"):
                    del db["tasks"][task_id]
                    if os.path.exists(task["log_file"]):
                        self._remove_log_file(task["log_file"])
        self._save_db(db)
        # print(f"len(db['tasks']): {len(db['tasks'])}")
        # db = self._load_db()
        if not db["tasks"]:
            # 删除logs目录下剩余文件，确保删除失败的情况下，在后续的执行中可以清除掉
            for file in os.listdir(self.log_dir):
                file_path = os.path.join(self.log_dir, file)
                if os.path.isfile(file_path):
                    self._remove_log_file(file_path)

    def kill_task(self, task_id):
        """终止任务"""
        db = self._load_db()
        if task_id not in db["tasks"]:
            raise ValueError("Task not found")
        
        pid = db["tasks"][task_id]["pid"]
        try:
            if pid is not None and self._is_process_running(pid):
                if os.name == 'posix':
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                else:
                    os.kill(pid, signal.CTRL_BREAK_EVENT)
                db["tasks"][task_id]["status"] = "killed"
                db["tasks"][task_id]["end_time"] = datetime.now().isoformat()
                self._save_db(db)
            return True
        except Exception as e:
            print(f"Error killing task {task_id}: {e}")
            return False

    def _cleanup(self):
        """清理已完成进程"""
        #print("Cleaning up tasks...")
        db = self._load_db()
        for task_id, task in list(db["tasks"].items()):
            if (task["status"] == "running"):
                pid = task.get("pid")
                if pid is None:
                    continue  # 没有 PID 无需处理
                try:
                    if not self._is_process_running(pid):
                        # 已结束
                        if task["status"] == "running":
                            task["status"] = "terminated"
                        task["end_time"] = datetime.now().isoformat()
                except Exception as e:
                    print(f"Error checking task {task_id}: {e}")
        self._save_db(db)

    def _is_process_running(self, pid):
        """跨平台判断进程是否还在运行"""
        if os.name == 'nt':  # Windows
            return psutil.pid_exists(pid)
        else:  # Unix/Linux/Mac
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False