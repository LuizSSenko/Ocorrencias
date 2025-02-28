
# app.py
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os, json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ocorrencias.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secretkey'

db = SQLAlchemy(app)

UPLOAD_FOLDER = 'upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Modelo para Ocorrência (armazenando arquivos, comentários e histórico em JSON)
class Ocorrencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    atualizado = db.Column(db.String(50), nullable=False)
    data_envio = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    resumo = db.Column(db.String(50), nullable=True)  # novo atributo resumo
    arquivos = db.Column(db.Text, nullable=True)       # JSON com lista de anexos
    comentarios = db.Column(db.Text, nullable=True)      # JSON com lista de comentários
    historico = db.Column(db.Text, nullable=True)        # JSON com lista de eventos

    def __init__(self, numero, tipo, estado, atualizado, data_envio, descricao, resumo, arquivos=None, comentarios=None, historico=None):
        self.numero = numero
        self.tipo = tipo
        self.estado = estado
        self.atualizado = atualizado
        self.data_envio = data_envio
        self.descricao = descricao
        self.resumo = resumo
        self.arquivos = json.dumps(arquivos) if arquivos is not None else json.dumps([])
        self.comentarios = json.dumps(comentarios) if comentarios is not None else json.dumps([])
        self.historico = json.dumps(historico) if historico is not None else json.dumps([])

    def get_arquivos(self):
        return json.loads(self.arquivos)

    def set_arquivos(self, arquivos):
        self.arquivos = json.dumps(arquivos)

    def get_comentarios(self):
        return json.loads(self.comentarios)

    def set_comentarios(self, comentarios):
        self.comentarios = json.dumps(comentarios)

    def get_historico(self):
        return json.loads(self.historico)

    def set_historico(self, historico):
        self.historico = json.dumps(historico)

@app.route('/')
def index():
    # Obtém parâmetros de ordenação via query string
    sort_by = request.args.get('sort_by', 'atualizado')
    order = request.args.get('order', 'desc')
    selected_sort_by = sort_by
    selected_order = order

    ocorrencias = Ocorrencia.query.all()
    if sort_by == 'atualizado':
        ocorrencias = sorted(ocorrencias, key=lambda o: datetime.strptime(o.atualizado, "%d/%m/%Y %H:%M"), reverse=(order=='desc'))
    elif sort_by == 'numero':
        ocorrencias = sorted(ocorrencias, key=lambda o: o.numero, reverse=(order=='desc'))
    elif sort_by == 'tipo':
        ocorrencias = sorted(ocorrencias, key=lambda o: o.tipo, reverse=(order=='desc'))
    elif sort_by == 'estado':
        ocorrencias = sorted(ocorrencias, key=lambda o: o.estado, reverse=(order=='desc'))
    return render_template('index.html', ocorrencias=ocorrencias, selected_sort_by=selected_sort_by, selected_order=selected_order)

@app.route('/ocorrencia/<int:ocorrencia_id>')
def ocorrencia(ocorrencia_id):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404
    return render_template('ocorrencia.html', ocorrencia=oc)

@app.route('/ocorrencia/nova', methods=['POST'])
def nova_ocorrencia():
    tipo = request.form.get('tipo')
    estado = request.form.get('estado')
    descricao = request.form.get('descricao')
    resumo = request.form.get('resumo')  # Recupera o resumo do formulário
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    novo_id = Ocorrencia.query.count() + 1
    numero = f"{novo_id:05d}"
    arquivos = []
    if 'arquivos' in request.files:
        uploaded_files = request.files.getlist('arquivos')
        for file in uploaded_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                arquivos.append({'nome': filename, 'upload_data': data_atual})
    historico = [{'data': data_atual, 'evento': 'Criação da Ocorrência'}]
    # Note que agora passamos 'resumo' na posição correta
    nova = Ocorrencia(numero, tipo, estado, data_atual, data_atual, descricao, resumo, arquivos, [], historico)
    db.session.add(nova)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/ocorrencia/<int:ocorrencia_id>/editar', methods=['POST'])
def editar_ocorrencia(ocorrencia_id):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404
    nova_descricao = request.form.get('descricao')
    oc.descricao = nova_descricao
    oc.atualizado = datetime.now().strftime("%d/%m/%Y %H:%M")
    hist = oc.get_historico()
    hist.append({'data': oc.atualizado, 'evento': 'Descrição editada'})
    oc.set_historico(hist)
    db.session.commit()
    return redirect(url_for('ocorrencia', ocorrencia_id=ocorrencia_id))

@app.route('/ocorrencia/<int:ocorrencia_id>/comentario/<int:comentario_index>/editar', methods=['POST'])
def editar_comentario(ocorrencia_id, comentario_index):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404
    comentarios = oc.get_comentarios()
    if comentario_index < 0 or comentario_index >= len(comentarios):
        return "Comentário não encontrado", 404
    novo_texto = request.form.get('comentario')
    comentarios[comentario_index]['texto'] = novo_texto
    comentarios[comentario_index]['editado'] = datetime.now().strftime("%d/%m/%Y %H:%M")
    oc.set_comentarios(comentarios)
    hist = oc.get_historico()
    hist.append({'data': datetime.now().strftime("%d/%m/%Y %H:%M"), 'evento': 'Comentário editado'})
    oc.set_historico(hist)
    db.session.commit()
    return redirect(url_for('ocorrencia', ocorrencia_id=ocorrencia_id))

@app.route('/ocorrencia/<int:ocorrencia_id>/comentario/adicionar', methods=['POST'])
def adicionar_comentario(ocorrencia_id):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404
    novo_texto = request.form.get('comentario')
    if novo_texto:
        comentarios = oc.get_comentarios()
        comentarios.append({'texto': novo_texto, 'data': datetime.now().strftime("%d/%m/%Y %H:%M"), 'editado': None})
        oc.set_comentarios(comentarios)
        hist = oc.get_historico()
        hist.append({'data': datetime.now().strftime("%d/%m/%Y %H:%M"), 'evento': 'Comentário adicionado'})
        oc.set_historico(hist)
        db.session.commit()
    return redirect(url_for('ocorrencia', ocorrencia_id=ocorrencia_id))

@app.route('/ocorrencia/<int:ocorrencia_id>/comentario/<int:comentario_index>/excluir', methods=['POST'])
def excluir_comentario(ocorrencia_id, comentario_index):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404
    comentarios = oc.get_comentarios()
    if comentario_index < 0 or comentario_index >= len(comentarios):
        return "Comentário não encontrado", 404
    comentarios.pop(comentario_index)
    oc.set_comentarios(comentarios)
    hist = oc.get_historico()
    hist.append({'data': datetime.now().strftime("%d/%m/%Y %H:%M"), 'evento': 'Comentário removido'})
    oc.set_historico(hist)
    db.session.commit()
    return redirect(url_for('ocorrencia', ocorrencia_id=ocorrencia_id))

@app.route('/ocorrencia/<int:ocorrencia_id>/excluir', methods=['POST'])
def excluir_ocorrencia(ocorrencia_id):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404

    # Remove os arquivos anexados, se existirem
    arquivos = oc.get_arquivos()
    for arquivo in arquivos:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], arquivo['nome'])
        if os.path.exists(file_path):
            os.remove(file_path)

    # Exclui a ocorrência do banco de dados
    db.session.delete(oc)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/upload/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Rota para alterar o estado da ocorrência e registrar o evento no histórico
@app.route('/ocorrencia/<int:ocorrencia_id>/alterar_estado', methods=['POST'])
def alterar_estado(ocorrencia_id):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404
    novo_estado = request.form.get('estado')
    if novo_estado and novo_estado != oc.estado:
        oc.estado = novo_estado
        oc.atualizado = datetime.now().strftime("%d/%m/%Y %H:%M")
        hist = oc.get_historico()
        hist.append({'data': oc.atualizado, 'evento': 'Estado da ocorrência alterado'})
        oc.set_historico(hist)
        db.session.commit()
    return redirect(url_for('ocorrencia', ocorrencia_id=ocorrencia_id))

@app.route('/ocorrencia/<int:ocorrencia_id>/alterar_tipo', methods=['POST'])
def alterar_tipo(ocorrencia_id):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404
    novo_tipo = request.form.get('tipo')
    if novo_tipo and novo_tipo != oc.tipo:
        oc.tipo = novo_tipo
        oc.atualizado = datetime.now().strftime("%d/%m/%Y %H:%M")
        hist = oc.get_historico()
        hist.append({'data': oc.atualizado, 'evento': 'Tipo da ocorrência alterado'})
        oc.set_historico(hist)
        db.session.commit()
    return redirect(url_for('ocorrencia', ocorrencia_id=ocorrencia_id))

@app.route('/ocorrencia/<int:ocorrencia_id>/alterar_resumo', methods=['POST'])
def alterar_resumo(ocorrencia_id):
    oc = Ocorrencia.query.get(ocorrencia_id)
    if oc is None:
        return "Ocorrência não encontrada", 404
    novo_resumo = request.form.get('resumo', '').strip()
    oc.resumo = novo_resumo if novo_resumo else ""
    oc.atualizado = datetime.now().strftime("%d/%m/%Y %H:%M")
    hist = oc.get_historico()
    hist.append({'data': oc.atualizado, 'evento': 'Resumo alterado'})
    oc.set_historico(hist)
    db.session.commit()
    return redirect(url_for('ocorrencia', ocorrencia_id=ocorrencia_id))



@app.route('/imprimir_ocorrencias')
def imprimir_ocorrencias():
    # Obter filtros via query string (ex.: ?data_inicio=01/01/2025&data_fim=31/01/2025&estado=Pendente&tipo=Acidentes de Trabalho)
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    estado = request.args.get('estado')
    tipo = request.args.get('tipo')
    
    # Inicia a consulta
    ocorrencias_query = Ocorrencia.query

    # Exemplo simplificado de filtro por estado e tipo (ajuste conforme necessário para datas)
    if estado:
        ocorrencias_query = ocorrencias_query.filter(Ocorrencia.estado == estado)
    if tipo:
        ocorrencias_query = ocorrencias_query.filter(Ocorrencia.tipo == tipo)
    
    ocorrencias = ocorrencias_query.all()
    return render_template('imprimir.html', ocorrencias=ocorrencias)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
