import click
from flask.cli import with_appcontext
from app import db
from app.models import User, Sample, MLModel

@click.command('init-db')
@with_appcontext
def init_db_command():
    """初始化数据库架构"""
    db.create_all()
    click.echo('数据库初始化完成')

@click.command('create-admin')
@click.option('--username', prompt=True, help='管理员用户名')
@click.option('--password', prompt=True, hide_input=True, help='管理员密码')
@with_appcontext
def create_admin_command(username, password):
    """创建管理员或科研人员主账户"""
    if User.query.filter_by(username=username).first():
        click.echo(f'用户 {username} 已存在')
        return
    
    admin = User(username=username, role='admin')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f'管理员 {username} 创建成功')

@click.command('list-models')
@with_appcontext
def list_models_command():
    """列出系统中注册的所有机器学习模型"""
    models = MLModel.query.all()
    if not models:
        click.echo('没有找到已注册的模型')
        return
    
    for model in models:
        status = '✓ 激活' if model.is_active else '  未激活'
        click.echo(f'{status} | ID: {model.id} | {model.name} v{model.version} | {model.model_type}')

def register_commands(app):
    """向 Flask CLI 注册自定义命令"""
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(list_models_command)

