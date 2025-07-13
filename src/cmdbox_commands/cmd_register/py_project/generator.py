def generator_src(command: str, description: str):
    return fr"""        
import sys,os
import click
import subprocess
import threading
from pathlib import Path

def stderr_print(line):
    print(line, file=sys.stdout, flush=True)

def read_stream(stream, output_file, is_stderr=False):
    for line in iter(stream.readline, ''):
        if not line:
            break
        if output_file:
            output_file.write(line)
            output_file.flush()
        if is_stderr:
            stderr_print(line)

@click.command(context_settings={{"ignore_unknown_options": True}}, help="{description}")
@click.pass_context
@click.option("-v", 'verbose', count=True, show_default=True, help="Enable debug mode, more log use -vv, max count 2")
@click.option("--log-file", 'log_file', type=click.Path(), help="Log file")
@click.option('--run-sync', 'run_sync', is_flag=True, help="同步运行命令，可能会阻塞命令行直到命令执行完成。默认后台执行命令")
@click.option("--command", 'act_command', is_flag=True, help="获取alias对应的真实命令")
@click.option('--help', 'help', is_flag=True, help="Show help message")
@click.argument("args", nargs=-1)
def main(ctx, args, verbose, log_file, help, act_command, run_sync):
    command = r"{command}"
    if act_command:
        click.echo(command)
        return command
    if verbose > 0:
        #stderr_print(f"command: {{command}}")
        stderr_print(f"verbose: {{verbose}}")
        stderr_print(f"log_file: {{log_file}}")
    _args = [item for item in args]
    if help:
        #click.echo(f"help: {{help}}")
        _args.extend(['--help'])
    command = " ".join([command] + _args)
    if verbose > 0:
        stderr_print(f"Excute command: {{command}}")
        if help: stderr_print("")
    if help:
            stderr_print(ctx.get_help())
    
    try:
        proc = subprocess.Popen(
                [r"{command}"] + _args,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
        stderr_thread = None
        stdout_thread = None

        f = None
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            f = open(log_file, "w", encoding="utf-8")

        if verbose > 0 and verbose < 2:
            stderr_thread = threading.Thread(
                    target=read_stream, 
                    args=(proc.stderr, f, True), daemon=True)
            stderr_thread.start()
        if verbose > 1 or help:
            stdout_thread = threading.Thread(
                    target=read_stream, 
                    args=(proc.stdout, f, True), daemon=True)
            stdout_thread.start()
        if run_sync:
            proc.wait()
            if stderr_thread:
                stderr_thread.join()
            if stdout_thread:
                stdout_thread.join()
        if f:
            f.close()        
        stderr_print("\nCommand success")
    except Exception as e:
        stderr_print(f"Excute command '{{command}}' failed: {{e}}")
        stderr_print(ctx.get_help())
        sys.exit(1)

if __name__ == "__main__":
    main()
        """