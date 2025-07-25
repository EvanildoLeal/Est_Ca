from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:621329@localhost/db_estoque'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # Mostra SQL no console (útil para debug)

db = SQLAlchemy(app)

# Modelos
class Produto(db.Model):
    __tablename__ = 'tbl_produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    quantidade = db.Column(db.Integer, default=0)
    quantidade_minima = db.Column(db.Integer, default=1)

class Usuario(db.Model):
    __tablename__ = 'tbl_usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    login = db.Column(db.String(50), nullable=False, unique=True)
    senha = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.Enum('admin', 'comum'), nullable=False)

class Movimentacao(db.Model):
    __tablename__ = 'tbl_movimentacoes'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Enum('entrada', 'saida'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    data_movi = db.Column(db.DateTime, default=datetime.utcnow)
    id_usuarios = db.Column(db.Integer, db.ForeignKey('tbl_usuarios.id'), nullable=False)
    id_produtos = db.Column(db.Integer, db.ForeignKey('tbl_produtos.id'), nullable=False)
    
    produto = db.relationship('Produto', backref='movimentacoes')
    usuario = db.relationship('Usuario', backref='movimentacoes')

# Rotas básicas
@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('estoque'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(login=login, senha=senha).first()
        
        if usuario:
            session['usuario'] = usuario.nome
            session['perfil'] = usuario.perfil
            session['id_usuario'] = usuario.id
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('estoque'))
        flash('Login ou senha incorretos', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Rotas de produtos
@app.route('/estoque')
def estoque():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    produtos = Produto.query.all()
    return render_template('estoque.html', produtos=produtos)

@app.route('/adicionar_produto', methods=['POST'])
def adicionar_produto():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    nome = request.form['nome']
    quantidade = int(request.form['quantidade'])
    
    novo_produto = Produto(nome=nome, quantidade=quantidade)
    db.session.add(novo_produto)
    db.session.commit()
    
    # Registrar movimentação de entrada inicial
    nova_mov = Movimentacao(
        tipo='entrada',
        quantidade=quantidade,
        id_usuarios=session['id_usuario'],
        id_produtos=novo_produto.id
    )
    db.session.add(nova_mov)
    db.session.commit()
    
    flash('Produto adicionado com sucesso!', 'success')
    return redirect(url_for('estoque'))

@app.route('/remover_produto/<int:id>')
def remover_produto(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    flash('Produto removido com sucesso!', 'success')
    return redirect(url_for('estoque'))

# Rotas de movimentação
@app.route('/movimentar', methods=['POST'])
def movimentar():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    produto_id = int(request.form['produto_id'])
    tipo = request.form['tipo']
    quantidade = int(request.form['quantidade'])
    
    produto = Produto.query.get_or_404(produto_id)
    
    if tipo == 'entrada':
        produto.quantidade += quantidade
    else:
        if produto.quantidade < quantidade:
            flash('Quantidade em estoque insuficiente!', 'danger')
            return redirect(url_for('estoque'))
        produto.quantidade -= quantidade
    
    # Registrar movimentação
    nova_mov = Movimentacao(
        tipo=tipo,
        quantidade=quantidade,
        id_usuarios=session['id_usuario'],
        id_produtos=produto_id
    )
    
    db.session.add(nova_mov)
    db.session.commit()
    flash('Movimentação registrada com sucesso!', 'success')
    return redirect(url_for('estoque'))

@app.route('/movimentacoes')
def movimentacoes():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    movs = Movimentacao.query.order_by(Movimentacao.data_movi.desc()).all()
    return render_template('movimentacoes.html', movimentacoes=movs)

# Rotas de usuários
@app.route('/usuarios')
def usuarios():
    if 'perfil' not in session or session['perfil'] != 'admin':
        flash('Acesso restrito a administradores', 'danger')
        return redirect(url_for('estoque'))
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/adicionar_usuario', methods=['POST'])
def adicionar_usuario():
    if 'perfil' not in session or session['perfil'] != 'admin':
        flash('Acesso restrito a administradores', 'danger')
        return redirect(url_for('estoque'))
    
    novo_usuario = Usuario(
        nome=request.form['nome'],
        login=request.form['login'],
        senha=request.form['senha'],
        perfil=request.form['perfil']
    )
    db.session.add(novo_usuario)
    db.session.commit()
    flash('Usuário cadastrado com sucesso!', 'success')
    return redirect(url_for('usuarios'))

@app.route('/remover_usuario/<int:id>')
def remover_usuario(id):
    if 'perfil' not in session or session['perfil'] != 'admin':
        flash('Acesso restrito a administradores', 'danger')
        return redirect(url_for('estoque'))
    
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuário removido com sucesso!', 'success')
    return redirect(url_for('usuarios'))

# Criar banco de dados (executar apenas uma vez)
def criar_banco():
    with app.app_context():
        db.create_all()
        # Criar usuário admin padrão se não existir
        if not Usuario.query.filter_by(login='admin').first():
            admin = Usuario(
                nome='Administrador',
                login='admin',
                senha='admin123',
                perfil='admin'
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    criar_banco()
    app.run(debug=True)