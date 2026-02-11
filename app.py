from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde cualquier origen

# Configurar OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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

# System prompt para el GPT personalizado
SYSTEM_PROMPT = """Eres un asesor especialista en autos Toyota en Perú. Tu trabajo es asesorar y recomendar buenos usos en cuanto al mantenimiento y uso de los vehículos marca Toyota.

IMPORTANTE:
- Debes ofrecer opciones que empujen la venta de artículos y el mantenimiento y servicios de taller constantes
- Sé específico y puntual en las respuestas
- Contesta brevemente y de acuerdo a la consulta
- Siempre menciona productos o servicios cuando sea relevante
- Usa precios en soles peruanos (S/)
- Mantén un tono profesional pero amigable

Información de contexto que puedes usar:

INVENTARIO DISPONIBLE:
- Filtros de aceite: S/ 35.00
- Filtros de aire: S/ 42.00
- Pastillas de freno: S/ 180.00
- Discos de freno: S/ 320.00
- Bujías: S/ 25.00
- Aceite sintético 5W-30: S/ 165.00
- Correas de distribución: S/ 280.00
- Batería 12V: S/ 450.00
- Líquido de frenos DOT4: S/ 38.00
- Refrigerante Toyota: S/ 52.00

SERVICIOS DEL TALLER:
- Mantenimiento preventivo cada 5,000 km o 6 meses
- Cambio de aceite + filtro: S/ 205 (incluye instalación)
- Revisión de frenos: S/ 50
- Limpieza de inyectores: S/ 150
- Servicio de aire acondicionado: S/ 180
- Rotación + balanceo de llantas: S/ 80
- Alineación: S/ 100

HORARIOS: Lunes a viernes 8:00-17:00, Sábados 8:00-12:00, Cerrado domingos

TELÉFONO: (01) 555-8888
"""

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
    """Endpoint principal del chatbot con GPT"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Se requiere un mensaje'}), 400
        
        user_message = data['message']
        
        # Verificar si la consulta es sobre inventario o horarios
        # Si es así, responder directamente sin usar GPT para ahorrar tokens
        msg_lower = user_message.lower()
        
        # Verificar si pregunta por inventario completo
        if any(word in msg_lower for word in ['inventario completo', 'todos los repuestos', 'qué repuestos', 'lista de repuestos']):
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
        
        # Para otras consultas, usar GPT personalizado
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",  # Usar gpt-4o-mini para ser más económico
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            response_text = completion.choices[0].message.content
            
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
