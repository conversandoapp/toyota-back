from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde cualquier origen

# Configurar OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# ID del GPT personalizado (Assistant)
ASSISTANT_ID = os.getenv('ASSISTANT_ID')

# Datos del inventario
INVENTARIO = {
    'filtros de aceite': {'stock': 45, 'precio': 'S/ 35.00', 'codigo': 'FO-2024'},
    'filtros de aire': {'stock': 32, 'precio': 'S/ 42.00', 'codigo': 'FA-2024'},
    'pastillas de freno': {'stock': 28, 'precio': 'S/ 180.00', 'codigo': 'PF-DELANTERAS'},
    'discos de freno': {'stock': 15, 'precio': 'S/ 320.00', 'codigo': 'DF-VENTILADOS'},
    'bujías': {'stock': 120, 'precio': 'S/ 25.00', 'codigo': 'BJ-IRIDIUM'},
    'aceite sintético': {'stock': 80, 'precio': 'S/ 165.00', 'codigo': 'AS-5W30'},
    'correas de distribución': {'stock': 12, 'precio': 'S/ 280.00', 'codigo': 'CD-ORIGINAL'},
    'batería': {'stock': 18, 'precio': 'S/ 450.00', 'codigo': 'BAT-12V'},
    'líquido de frenos': {'stock': 55, 'precio': 'S/ 38.00', 'codigo': 'LF-DOT4'},
    'refrigerante': {'stock': 65, 'precio': 'S/ 52.00', 'codigo': 'REF-TOYOTA'}
}

# Horarios del taller
HORARIOS = {
    'lunes': {'disponibles': ['09:00', '11:00', '15:00'], 'ocupados': ['08:00', '10:00', '14:00', '16:00']},
    'martes': {'disponibles': ['08:00', '10:00', '14:00', '16:00'], 'ocupados': ['09:00', '11:00', '15:00']},
    'miércoles': {'disponibles': ['09:00', '13:00', '15:00'], 'ocupados': ['08:00', '10:00', '11:00', '14:00']},
    'jueves': {'disponibles': ['08:00', '11:00', '14:00', '16:00'], 'ocupados': ['09:00', '10:00', '15:00']},
    'viernes': {'disponibles': ['09:00', '10:00', '13:00'], 'ocupados': ['08:00', '11:00', '14:00', '15:00', '16:00']},
    'sábado': {'disponibles': ['09:00', '10:00'], 'ocupados': ['08:00', '11:00']},
    'domingo': {'disponibles': [], 'ocupados': ['Cerrado']}
}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

@app.route('/api/inventario', methods=['GET'])
def get_inventario():
    """Obtener todo el inventario"""
    return jsonify(INVENTARIO), 200

@app.route('/api/horarios', methods=['GET'])
def get_horarios():
    """Obtener los horarios del taller"""
    return jsonify(HORARIOS), 200

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint principal del chatbot con GPT Assistant personalizado"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Se requiere un mensaje'}), 400
        
        user_message = data['message']
        
        # Verificar que ASSISTANT_ID esté configurado
        if not ASSISTANT_ID:
            return jsonify({
                'error': 'ASSISTANT_ID no está configurado. Por favor, configura tu ID de asistente en las variables de entorno.'
            }), 500
        
        # Verificar si la consulta es sobre inventario o horarios
        # Si es así, responder directamente sin usar el Assistant para ahorrar tokens
        msg_lower = user_message.lower()
        
        # Verificar si pregunta por inventario completo
        if any(word in msg_lower for word in ['inventario completo', 'todos los repuestos', 'lista de repuestos']):
            response_text = "📦 **INVENTARIO COMPLETO**\n\n"
            for item, data in INVENTARIO.items():
                response_text += f"**{item.upper()}**\n"
                response_text += f"• Precio: {data['precio']}\n"
                response_text += f"• Stock: {data['stock']} unidades\n\n"
            response_text += "💡 Para más detalles sobre un repuesto específico, pregúntame por él."
            return jsonify({'response': response_text}), 200
        
        # Verificar si pregunta por horarios completos
        if any(word in msg_lower for word in ['horarios completos', 'todos los horarios', 'cuándo abren', 'horario de atención']):
            response_text = "🕐 **HORARIOS DEL TALLER**\n\n"
            for dia, info in HORARIOS.items():
                response_text += f"**{dia.upper()}**\n"
                if info['disponibles']:
                    response_text += f"✅ Disponibles: {', '.join(info['disponibles'])}\n"
                    response_text += f"⏰ Ocupados: {', '.join(info['ocupados'])}\n\n"
                else:
                    response_text += "❌ Cerrado\n\n"
            response_text += "📞 Reservas: (01) 555-8888"
            return jsonify({'response': response_text}), 200
        
        # Para otras consultas, usar el Assistant personalizado
        try:
            # Crear un Thread (conversación)
            thread = client.beta.threads.create()
            
            # Agregar el mensaje del usuario al Thread
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_message
            )
            
            # Ejecutar el Assistant
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )
            
            # Esperar a que el Assistant termine de procesar
            max_attempts = 30  # 30 segundos máximo
            attempt = 0
            while attempt < max_attempts:
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    break
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    return jsonify({
                        'error': f'El asistente no pudo procesar la solicitud: {run_status.status}'
                    }), 500
                
                time.sleep(1)
                attempt += 1
            
            if attempt >= max_attempts:
                return jsonify({'error': 'Tiempo de espera agotado'}), 500
            
            # Obtener la respuesta del Assistant
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            
            # La respuesta más reciente es la del Assistant
            assistant_message = messages.data[0]
            response_text = assistant_message.content[0].text.value
            
            return jsonify({'response': response_text}), 200
            
        except Exception as openai_error:
            print(f"Error de OpenAI: {str(openai_error)}")
            return jsonify({
                'error': 'Error al procesar la consulta con el asistente',
                'details': str(openai_error)
            }), 500
        
    except Exception as e:
        print(f"Error general: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
