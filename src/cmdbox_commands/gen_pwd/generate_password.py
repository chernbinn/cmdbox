import random
import string
import click
import time
import sys

@click.command(help='生成由数字、字符、特殊字符组成的密码')
@click.option('-l', '--length', default=6, show_default=True, help='密码长度。')
@click.option('-n', '--number', is_flag=True, default=True, show_default=True, help='仅由数字组成的密码')
@click.option('--special', is_flag=True, default=False, help='仅由特殊字符组成的密码')
@click.option('-s', '--ascii', is_flag=True, default=False, help='仅由ASCII字符组成的密码')
@click.option('--upper', is_flag=True, default=False, help='仅包含大写ASCII字符')
@click.option('--lower', is_flag=True, default=False, help='仅包含小写ASCII字符')
@click.option('--no-digits', is_flag=True, default=False, help='不包含数字')
@click.option('--no-letters', is_flag=True, default=False, help='不包含字母')
@click.option('--no-punctuation', is_flag=True, default=False, help='不包含特殊符号')
@click.option('--repeat-num', default=0, help='密码中可重复的字符个数')
@click.option('--max-repeat', default=2, show_default=True, help='密码中单个字符最大可重复次数')
@click.option('--min-repeat', default=1, show_default=True, help='密码中单个字符最小可重复次数')
def generate_password(length, number, special, ascii, upper, lower, 
        no_digits, no_letters, no_punctuation, repeat_num, max_repeat, min_repeat):
    characters = string.ascii_letters + string.digits + string.punctuation
    if number:
        characters = string.digits
    elif special:
        characters = string.punctuation
    elif ascii:
        characters = string.ascii_letters
    elif upper:
        characters = string.ascii_letters
        characters = characters.upper()[:26]
    elif lower:
        characters = string.ascii_letters
        characters = characters.lower()[:26]

    if no_digits:
        characters = characters.replace(string.digits, '')
    if no_letters:
        characters = characters.replace(string.ascii_letters, '')
    if no_punctuation:
        characters = characters.replace(string.punctuation, '')

    # 检查参数的基本有效性
    if repeat_num < 0:
        click.error('repeat-num 不能为负数')
        return
    if max_repeat < 1:
        click.error('max-repeat 不能小于1')
        return
    if min_repeat < 1:
        click.error('min-repeat 不能小于1')
        return
    
    # 检查参数之间的关系
    if min_repeat > max_repeat:
        click.error('min-repeat 不能大于 max-repeat')
        return
    
    # 检查与密码长度的关系
    if repeat_num > length/2:
        click.error('repeat-num 不能大于密码长度的一半')
        return
    if max_repeat > length:
        click.error('max-repeat 不能大于密码长度')
        return
    
    # 当min_repeat > 1时，需要确保密码长度足够支持重复模式
    # 例如，如果min_repeat=2且length=3，那么最多只能有1个唯一字符
    # 但这可能导致无法生成符合条件的密码，所以需要检查
    # 计算最大可能的唯一字符数：length // min_repeat
    max_unique_chars = length // min_repeat
    if max_unique_chars < 1:
        click.error(f'密码长度{length}过短，无法满足min-repeat={min_repeat}的要求')
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