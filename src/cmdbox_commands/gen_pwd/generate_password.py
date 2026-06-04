import random
import string
import click
import time
import sys

@click.command(help='生成由数字、字符、特殊字符组成的密码')
@click.option('-l', '--length', default=6, show_default=True, help='密码长度。')
@click.option('-n', '--number', is_flag=True, default=False, show_default=True, help='仅由数字组成的密码')
@click.option('--special', is_flag=True, default=False, help='仅由特殊字符组成的密码')
@click.option('-s', '--ascii', is_flag=True, default=False, help='仅由ASCII字符组成的密码')
@click.option('--upper', is_flag=True, default=False, help='不包含小写ASCII字符')
@click.option('--lower', is_flag=True, default=False, help='不包含大写ASCII字符')
@click.option('--no-number', is_flag=True, default=False, help='不包含数字')
@click.option('--no-ascii', is_flag=True, default=False, help='不包含字母')
@click.option('--no-special', is_flag=True, default=False, help='不包含特殊符号')
@click.option('--repeat-num', default=0, help='密码中可重复的字符个数')
@click.option('--max-repeat', default=2, show_default=True, help='密码中单个字符最大可重复次数')
@click.option('--min-repeat', default=1, show_default=True, help='密码中单个字符最小可重复次数')
def generate_password(length, number, special, ascii, upper, lower, 
        no_number, no_ascii, no_special, repeat_num, max_repeat, min_repeat):
    characters = string.ascii_letters + string.digits + string.punctuation
    if number:
        characters = string.digits
    elif special:
        characters = string.punctuation
    elif ascii:
        characters = string.ascii_letters

    if upper:
        characters = characters.replace(string.ascii_letters, '')
        _characters = string.ascii_letters
        _characters = characters.upper()[:26]
        characters = characters + _characters
    if lower:
        characters = characters.replace(string.ascii_letters, '')
        _characters = string.ascii_letters
        _characters = characters.lower()[:26]
        characters = characters + _characters

    if no_number:
        if number:
            print("-n 与 --no-number 不能同时使用")
            return
        characters = characters.replace(string.digits, '')
    if no_ascii:
        if ascii:
            print("-s 与 --no-ascii 不能同时使用")
            return
        characters = characters.replace(string.ascii_letters, '')
    if no_special:
        if special:
            print("--special 与 --no-special 不能同时使用")
            return
        characters = characters.replace(string.punctuation, '')
    
    # 检查参数的基本有效性
    if repeat_num < 0:
        print(f'repeat-num({repeat_num}) 不能为负数')
        return
    if max_repeat < 1:
        print(f'max-repeat({max_repeat}) 不能小于1')
        return
    if min_repeat < 1:
        print(f'min-repeat({min_repeat}) 不能小于1')
        return
    
    # 检查参数之间的关系
    if min_repeat > max_repeat:
        print(f'min-repeat({min_repeat}) 不能大于 max-repeat({max_repeat})')
        return
    
    # 检查与密码长度的关系
    if repeat_num > length/2:
        print(f'repeat-num({repeat_num}) 不能大于密码长度({length})的一半')
        return
    if max_repeat > length:
        print(f'max-repeat({max_repeat}) 不能大于密码长度({length})')
        return
    
    # 当min_repeat > 1时，需要确保密码长度足够支持重复模式
    # 例如，如果min_repeat=2且length=3，那么最多只能有1个唯一字符
    # 但这可能导致无法生成符合条件的密码，所以需要检查
    # 计算最大可能的唯一字符数：length // min_repeat
    max_unique_chars = length // min_repeat
    if max_unique_chars < 0:
        print(f'密码长度{length}过短，无法满足min-repeat={min_repeat}的要求')
        return
    
    # 检查repeat_num与min_repeat的关系
    # 当设置了min_repeat>1时，repeat_num应该适当调整或限制
    if min_repeat > 1 and repeat_num > 0:
        # 当有最小重复要求时，repeat_num的实际有效范围会受到限制
        # 这里可以添加更复杂的验证，或者在生成逻辑中处理
        pass

    is_valid = False
    while not is_valid:
        random.seed(time.time())
        password = ''.join(random.choice(characters) for _ in range(length))
        repeat_dict = {}
        is_valid = True

        for i, char in enumerate(password):
            if char in repeat_dict:
                repeat_dict[char] += 1
            else:
                repeat_dict[char] = 1
            if any([
                max(repeat_dict.values()) > max_repeat, 
                min(repeat_dict.values()) < min_repeat,
                repeat_num != 0 and len(repeat_dict) > length - repeat_num,
                repeat_num != 0 and (i == length - 1) and (len(repeat_dict) < length - repeat_num)
            ]):
                is_valid = False
                break
        
    click.echo(password)

def cli():
    try:
        generate_password()
    except KeyboardInterrupt:
        print("\nCtrl+C")
        sys.exit(0)

if __name__ == '__main__':
    sys.exit(cli())