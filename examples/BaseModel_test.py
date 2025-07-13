from pydantic import BaseModel

class Command(BaseModel):
    alias: str
    command: str
    is_gui: bool = False
    description: str = ''    

    def src_file_name(self):
        return f'{self.alias}_{"gui_" if self.is_gui else ""}cli.py'

class AliasCMD(Command):
    project_name: str = 'default' 
    # 继承了BaseModel，project_name不再是类属性，是BaseModel的模型字段
    # 类属性必须声明模型字段，不再具备类属性，比如这里注释掉project_name，__init__中初始化project_name会报错

    def __init__(self, alias: str, 
            command: str, 
            is_gui: bool = False, 
            description: str = '', 
            project_name: str = 'default'):
        super().__init__(
            alias=alias,
            command=command,
            is_gui=is_gui,
            description=description
        )
        self.project_name = project_name

if __name__ == '__main__':
    print(Command.model_fields)
    print(AliasCMD.model_fields)
    alias_cmd = AliasCMD(
        alias='alias_cmd',
        command='command',
        is_gui=True,
        description='description',
        project_name='project_name'
    )
    print(alias_cmd)
    print(alias_cmd.model_dump())
    #print(AliasCMD.project_name)
    print(alias_cmd.project_name)
    print(alias_cmd.alias)
    alias_cmd = AliasCMD(
        alias='alias_cmd',
        command='command',
        is_gui=True,
        description='description'
    )
    print(alias_cmd.project_name)
