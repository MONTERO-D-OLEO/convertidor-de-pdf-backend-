"""
ConvertidorPro — Backend Flask
Convierte PDF a Word usando pdf2docx para máxima calidad.
"""

import os
import uuid
import tempfile
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pdf2docx import Converter

# ─── Configuración ───────────────────────────────────
app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# Límite de 500MB para subida de archivos
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Directorio temporal para las conversiones
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'convertidorpro')
os.makedirs(TEMP_DIR, exist_ok=True)


# ─── Endpoint: PDF a Word ───────────────────────────
@app.route('/convert/pdf-to-word', methods=['POST'])
def pdf_to_word():
    """
    Recibe un PDF, lo convierte a .docx con pdf2docx y devuelve el archivo.
    Los archivos temporales se borran después de la conversión.
    """
    pdf_path = None
    docx_path = None

    try:
        # Validar que se envió un archivo
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'El archivo no tiene nombre'}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Solo se aceptan archivos PDF'}), 400

        # Generar nombres únicos para evitar colisiones
        unique_id = str(uuid.uuid4())
        pdf_path = os.path.join(TEMP_DIR, f'{unique_id}.pdf')
        docx_path = os.path.join(TEMP_DIR, f'{unique_id}.docx')

        # Guardar el PDF subido
        file.save(pdf_path)

        # Convertir PDF a Word usando pdf2docx
        cv = Converter(pdf_path)
        cv.convert(docx_path)
        cv.close()

        # Preparar nombre del archivo de salida
        output_name = file.filename.rsplit('.', 1)[0] + '.docx'

        # Enviar el archivo convertido
        response = send_file(
            docx_path,
            as_attachment=True,
            download_name=output_name,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

        # Borrar archivos temporales después de enviar la respuesta
        @response.call_on_close
        def cleanup():
            _safe_delete(pdf_path)
            _safe_delete(docx_path)

        return response

    except Exception as e:
        # Limpiar en caso de error
        _safe_delete(pdf_path)
        _safe_delete(docx_path)

        error_msg = str(e)
        if 'MAX_CONTENT_LENGTH' in error_msg or '413' in error_msg:
            return jsonify({'error': 'El archivo supera el límite de 500MB'}), 413

        app.logger.error(f'Error en conversión: {error_msg}')
        return jsonify({'error': f'Error al convertir: {error_msg}'}), 500


# ─── Servir el frontend ─────────────────────────────
@app.route('/')
def index():
    return app.send_static_file('index.html')


# ─── Health check ────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'ConvertidorPro Backend'})


# ─── Utilidades ──────────────────────────────────────
def _safe_delete(path):
    """Borra un archivo de forma segura, ignorando errores."""
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ─── Manejo de errores ──────────────────────────────
@app.errorhandler(413)
def file_too_large(e):
    return jsonify({'error': 'El archivo supera el límite de 500MB'}), 413


@app.errorhandler(404)
def not_found(e):
    return app.send_static_file('index.html')


# ─── Iniciar servidor ───────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f'[OK] ConvertidorPro Backend iniciado en http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
