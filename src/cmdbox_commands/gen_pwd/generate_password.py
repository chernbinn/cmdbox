import random
import string
import click
import time

@click.command(help='生成由数字、字符、特殊字符组成的密码')
@click.option('-l', '--length', default=6, show_default=True, help='密码长度。')
@click.option('-n', '--number', is_flag=True, default=False, help='仅由数字组成的密码')
@click.option('--special', is_flag=True, default=False, help='仅由特殊字符组成的密码')
@click.option('-s', '--ascii', is_flag=True, default=False, help='仅由ASCII字符组成的密码')
@click.option('--upper', is_flag=True, default=False, help='仅包含大写ASCII字符')
@click.option('--lower', is_flag=True, default=False, help='仅包含小写ASCII字符')
@click.option('--no-digits', is_flag=True, default=False, help='不包含数字')
@click.option('--no-letters', is_flag=True, default=False, help='不包含字母')
@click.option('--no-punctuation', is_flag=True, default=False, help='不包含特殊符号')
def generate_password(length, number, special, ascii, upper, lower, no_digits, no_letters, no_punctuation):
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

    else:
        characters = string.ascii_letters + string.digits + string.punctuation
        if not no_digits:
            characters = characters.replace(string.digits, '')
        if not no_letters:
            characters = characters.replace(string.ascii_letters, '')
        if not no_punctuation:
            characters = characters.replace(string.punctuation, '')
    
    random.seed(time.time())
    password = ''.join(random.choice(characters) for _ in range(length))
    click.echo(password)

def cli():
    generate_password()

if __name__ == '__main__':
    cli()