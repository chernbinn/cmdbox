from typing import Optional, Callable, Any

class ClickOption:
    @staticmethod
    def _generic_callback(ctx, param, value):
        if value:
            # 这里实现一个通用的option回调函数
            ctx.obj[param.name] = value

    def generate_option(
        self,
        name: str,
        param_name: str,
        help: str,
        short: Optional[str] = None,
        opt_type: Optional[Callable] = None,        
        is_flag: Optional[bool] = None,
        default: Optional[Any] = None,
        show_default: Optional[bool] = None,
        required: Optional[bool] = None,
        is_eager: bool = True,
        expose_value: bool = True,        
        enabled: bool = True
    ) -> str:
        """通用选项生成器
        
        Args:
            name: 选项名称 (e.g. '--irun-sync')
            param_name: 参数名称 (e.g. 'run_sync')
            help: 帮助文本
            short: 短选项名称 (e.g. '-s')
            opt_type: 参数类型 (e.g. click.Path())
            is_flag: 是否作为标志选项
            default: 默认值
            show_default: 是否显示默认值
            required: 是否必须
            is_eager: 是否优先处理
            expose_value: 是否暴露值
            enabled: 是否启用该选项
        """
        if not enabled:
            return ""
            
        callback_ref = f"callback={self.__class__.__name__}._generic_callback"
        
        parts = [
            f"'{name}', '{param_name}'",
            f"is_eager={is_eager}",
            f"expose_value={expose_value}",
            callback_ref,
        ]
        insert_index = 0
        if short:
            parts.insert(insert_index, f"'{short}'")
            insert_index += 1
        
        if opt_type:
            parts.insert(1+insert_index, f"type={opt_type.__name__}")
            insert_index += 1
        
        if is_flag is not None:
            parts.insert(1+insert_index, f"is_flag={is_flag}")
            insert_index += 1

        if default is not None:
            parts.insert(1+insert_index, f"default={default}")
            insert_index += 1
        
        if show_default is not None:
            parts.insert(1+insert_index, f"show_default={show_default}")
            insert_index += 1

        if required is not None:
            parts.insert(1+insert_index, f"required={required}")
            insert_index += 1
        
        parts.append(f'help="""{help}"""')

        # 指定位置换行或者每三个参数换一行，help独占一行
        new_parts = ["@click.option("]
        new_line = 0
        for i in range(0, len(parts)-1):
            new_parts[-1] =  f"{new_parts[-1]}{parts[i]}, "
            if any([
                parts[i].startswith("default"),
                parts[i].startswith("required"),
                parts[i].startswith("callback"),
            ]):
                new_parts.append("")
                new_line = 0

            new_line += 1
            if new_line == 3:
                new_parts.append("")
                new_line = 0

        if not new_parts[-1]:
            new_parts.pop()
        new_parts.append(f"{parts[-1]}")
        return "\n    ".join(new_parts) + ")"
    
    def generate_option_is_gui(self, is_gui:bool) -> str:
        if is_gui:
            """生成GUI相关选项"""
            return self.generate_option(
                name='--irun-sync',
                param_name='run_sync',
                help="同步运行内部命令。阻塞命令行直到内部命令执行完成，比较耗资源。未说明同步执行，默认后台执行内部命令",
                is_flag=True,
                is_eager=True,
                expose_value=False,
                enabled=is_gui
            )
        return ""

click_option = ClickOption()
def test_is_gui_True():
    print("test_is_gui_True-----")

    print(fr"""{click_option.generate_option_is_gui(True)}
{click_option.generate_option("--overbose", "verbose", help="同步执行内部命令，输出命令执行信息",
    short="-ov", is_flag=True, show_default=True, enabled=True)}
{click_option.generate_option("--olog-file", "log_file", help="同步执行内部命令，输出命令执行信息",
        is_flag=True, show_default=True, enabled=True)}
"""
    )
    # @click.option("-ov", 'verbose', is_flag=True, show_default=True, help="同步执行内部命令，输出命令执行信息")
    # @click.option("--olog-file", 'log_file', type=click.Path(), help="同步执行内部命令，并输出log到文件")

def test_is_gui_False():
    print("\ntest_is_gui_False-----")

    print(fr"""{click_option.generate_option_is_gui(False)}
{click_option.generate_option("--overbose", "verbose", help="同步执行内部命令，输出命令执行信息",
    short="-ov", is_flag=True, show_default=True, enabled=False)}
{click_option.generate_option("--olog-file", "log_file", help="同步执行内部命令，输出命令执行信息",
        is_flag=True, show_default=True, enabled=False)}
"""
    )
    # @click.option("-ov", 'verbose', is_flag=True, show_default=True, help="同步执行内部命令，输出命令执行信息")
    # @click.option("--olog-file", 'log_file', type=click.Path(), help="同步执行内部命令，并输出log到文件")


if __name__ == "__main__":
    test_is_gui_True()
    test_is_gui_False()

    