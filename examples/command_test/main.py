try:
    from .utils import child_run, ChildResult
except:
    from utils import child_run, ChildResult

from typing import Literal

class Test():
    def __init__(self):
        self.test_list = []

    def test_case(self, func):
        self.test_list.append(func)
        def wrapper(*args, **kwargs):
            self.test_list.append(func)
            return func(*args, **kwargs)
        return wrapper
    
    def test(self):
        for func in self.test_list:
            func()

test = Test()

def test_command(cmd: str, verbose:Literal[0,1,2]=0):
    def old(func):
        def wapper():
            print(f"Test command: {cmd}, {func.__name__}")
            print(f"{func.__doc__}")
            result = child_run(cmd, verbose)
            print("------ handle result -------")
            func(result)
            print(f"Test command: {cmd} end\n")
        return wapper
    return old

#@test.test_case
@test_command(cmd="pipx uninstall testtest")
def test_uninstall_installed(result: ChildResult):
    """ 卸载已安装包 """
    print("result.stdout:\n", result.stdout)
    print("result.stderr:\n", result.stderr)
    print("result.returncode: ", result.returncode)

#@test.test_case
@test_command(cmd="pipx uninstall alkdfj")
def test_uninstall_uninstalled(result: ChildResult):
    """ 卸载未安装包 """
    print("result.stdout:\n", result.stdout)
    print("result.stderr:\n", result.stderr)
    print("result.returncode: ", result.returncode)

@test.test_case
@test_command(cmd="pipx runpip None show -f None")
def test_show_installed(result: ChildResult):
    """ 查看已安装包详细信息 """
    print("result.stdout:\n", result.stdout)
    print("result.stderr:\n", result.stderr)
    print("result.returncode: ", result.returncode)

@test.test_case
@test_command(cmd="pipx runpip Nadfafone show -f Noadfafne")
def test_show_uninstalled(result: ChildResult):
    """ 查看未安装包详细信息 """
    print("result.stdout:\n", result.stdout)
    print("result.stderr:\n", result.stderr)
    print("result.returncode: ", result.returncode)

@test.test_case
@test_command(cmd="myls --icommand")
def test_alias_command(result: ChildResult):
    """ 查看已安装命令的内部命令 """
    print("result.stdout:\n", result.stdout)
    print("result.stderr:\n", result.stderr)
    print("result.returncode: ", result.returncode)

@test.test_case
@test_command(cmd="myrm --icommand")
def test_nonalias_command(result: ChildResult):
    """ 查看未安装命令的内部命令 """
    print("result.stdout:\n", result.stdout)
    print("result.stderr:\n", result.stderr)
    print("result.returncode: ", result.returncode)

@test.test_case
@test_command(cmd="myls --oproject-name")
def test_alias_command(result: ChildResult):
    """ 查看已安装命令的包名 """
    print("result.stdout:\n", result.stdout)
    print("result.stderr:\n", result.stderr)
    print("result.returncode: ", result.returncode)

@test.test_case
@test_command(cmd="myrm --oproject-name")
def test_nonalias_command(result: ChildResult):
    """ 查看未安装命令的包名 """
    print("result.stdout:\n", result.stdout)
    print("result.stderr:\n", result.stderr)
    print("result.returncode: ", result.returncode)

def main():
    test.test()

if __name__ == '__main__':
    main()