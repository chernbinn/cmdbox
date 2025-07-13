import base64
from abc import ABC, abstractmethod

class V(ABC):
    @staticmethod
    @abstractmethod
    def encrypt_version(base_version: str, secret: str) -> str:
        pass

    @staticmethod
    @abstractmethod
    def decrypt_version(full_version: str) -> (str, str):
        pass

class Base64V(V):
    @staticmethod
    def encrypt_version(base_version: str, secret: str) -> str:
        encrypted = base64.b64encode(secret.encode()).decode().rstrip('=')
        return f"{base_version}+{encrypted}"

    @staticmethod
    def decrypt_version(full_version: str) -> (str, str):
        if '+' not in full_version:
            return full_version, None
        base, _, local = full_version.partition('+')
        try:
            decoded = base64.b64decode(local + '==').decode()
            return base, decoded
        except Exception:
            return base, None

class Base32V(V):
    @staticmethod
    def encrypt_version(base_version: str, secret: str) -> str:
        # 使用 base32 编码并转为小写
        encoded = base64.b32encode(secret.encode()).decode().lower().rstrip("=")
        return f"{base_version}+{encoded}"

    @staticmethod
    def decrypt_version(full_version: str) -> (str, str):
        if '+' not in full_version:
            return full_version, None
        base, _, local = full_version.partition('+')
        # 补全 padding =
        padded = local + "=" * ((8 - len(local) % 8) % 8)
        try:
            decoded = base64.b32decode(padded.upper()).decode()
            return base, decoded
        except Exception:
            return base, None

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
versionV = Base32V()

def log_func(func):
    def inner(*args, **kwargs):
        print(f"------Start {func.__name__}")
        # 打印函数的简述
        print(func.__doc__)
        print()
        result = func(*args, **kwargs)
        print(f"------End {func.__name__}\n")
        return result
    return inner

@test.test_case
@log_func
def test1():
    """ 正常加解密测试 """
    base_version = '0.1.0'
    secret = 'cmdbox'
    encrypted = versionV.encrypt_version(base_version, secret)
    print(encrypted)
    base, secret = versionV.decrypt_version(encrypted)
    print(base, secret)

@test.test_case
@log_func
def test2():
    """ 异常加解密测试 """
    base_version = '0.1.0'
    secret = 'cmdbox'
    encrypted = versionV.encrypt_version(base_version, secret)

    print("正常加密后的版本号")
    print(encrypted)
    print("异常测试，随手写的")
    encrypted = '0.1.0.alkdfjaf'
    print(encrypted)
    base, secret = versionV.decrypt_version(encrypted)
    print(base, secret)
    print("异常测试，正常版本号随便该字母后的")
    encrypted = '0.1.0+alkdfjaf'
    print(encrypted)
    base, secret = versionV.decrypt_version(encrypted)
    print(base, secret)

@test.test_case
@log_func
def test3():
    """ 组合加密信息 """
    base_version = '0.1.0'
    secret = 'cmdr_afdaf'
    encrypted = versionV.encrypt_version(base_version, secret)
    print(encrypted)
    base, secret = versionV.decrypt_version(encrypted)
    print(base, secret)

def _test4():
    base_version = '0.1.0'
    secret = 'cmdr_default'
    encrypted = versionV.encrypt_version(base_version, secret)
    print(encrypted)
    return encrypted.lower()

@test.test_case
@log_func
def test4():
    """ 加密 """    
    _test4()

@test.test_case
@log_func
def test5():
    """ 解密 """
    encrypted = _test4()
    base, secret = versionV.decrypt_version(encrypted)
    print(base, secret)

import random
def generate_str(len: int) -> str:
    import string
    return ''.join(random.choices(string.ascii_letters, k=len)).lower()

#@test.test_case
@log_func
def test6():
    """ 随机生成scret,进行加解密压力测试 """
    base_version = '0.1.0'
    for i in range(100):
        print(f"------{i}------")
        secret = f'cmdr_{generate_str(random.randint(3, 10))}'
        print(secret)
        encrypted = versionV.encrypt_version(base_version, secret)
        print(encrypted)
        base, de_secret = versionV.decrypt_version(encrypted)
        print(base, de_secret)
        assert base == base_version
        assert secret == de_secret


def main():
    test.test()

if __name__ == '__main__':
    main()