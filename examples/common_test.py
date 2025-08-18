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
            print(f"test {func.__name__}")
            print(func.__doc__)
            func()
            print("test done\n")


test = Test()

@test.test_case
def test1():
    """
    f-string测试
    """
    project_name = "Test"
    print(f'Alias test1 dose not exist {f"in {project_name}" if project_name else ""}')
    project_name = None
    print(f'Alias test1 dose not exist {f"in {project_name}" if project_name else ""}')

if __name__ == "__main__":
    test.test()