import os
import requests
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash, check_password_hash
from estructuras import ArbolProductos, GrafoZonas
from datetime import datetime, timedelta

# ================================================================
# 1. CONFIGURACIÓN INICIAL DEL ENTORNO Y SEGURIDAD
# ================================================================

app = Flask(__name__)

# Clave secreta para la protección de sesiones y cifrado de mensajes flash
app.secret_key = "dont_waste_it_pro_full_logic_validated_final_2024"

# Configuración de rutas para la base de datos persistente en la carpeta 'instance'
# Esto asegura que la base de datos sea independiente del código fuente
base_path = os.path.abspath(os.path.dirname(__file__))
instance_directory = os.path.join(base_path, 'instance')

# Verificación y creación automática del directorio de instancia
if not os.path.exists(instance_directory):
    os.makedirs(instance_directory)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_directory, 'dont_waste_it.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialización de SQLAlchemy para el manejo de modelos y persistencia
db = SQLAlchemy(app)

# Configuración del endpoint para el asistente de IA (LM Studio Bionic en puerto 1235)
LM_STUDIO_URL = "http://localhost:1235/v1/chat/completions"

# ================================================================
# 2. MODELOS DE DATOS (ESTRUCTURA DE LA BASE DE DATOS)
# ================================================================

class Usuario(db.Model):
    """ Almacena la información de Clientes y Dueños de Establecimientos """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    clave = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False) # 'dueño' o 'cliente'
    zona = db.Column(db.String(50), default='Centro')
    
    # Atributos específicos del perfil comercial (solo dueños)
    nombre_establecimiento = db.Column(db.String(100), nullable=True)
    direccion_establecimiento = db.Column(db.String(200), nullable=True)
    tipo_establecimiento = db.Column(db.String(50), nullable=True)
    
    # Métricas de Gamificación, Impacto Ambiental y Ahorro
    puntos = db.Column(db.Integer, default=0)
    kg_rescatados = db.Column(db.Float, default=0.0)
    ahorro_total = db.Column(db.Float, default=0.0)

class Producto(db.Model):
    """ Representa los excedentes alimentarios publicados por los locales """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50)) # Ejemplo: Panadería, Plato Preparado, Pack Sorpresa
    precio_original = db.Column(db.Float, nullable=False)
    precio_oferta = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, default=1)
    estado = db.Column(db.String(20), default='Activo') # 'Activo' o 'Agotado'
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    zona = db.Column(db.String(50))

class Transaccion(db.Model):
    """ Registra el historial de rescates y gestiona el flujo de entrega física """
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'))
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    # HU-03: Tiempo límite para que el cliente recoja el pedido
    fecha_limite = db.Column(db.DateTime, nullable=True)
    
    cantidad = db.Column(db.Integer, default=1)
    precio_pagado = db.Column(db.Float)
    nombre_producto = db.Column(db.String(100))
    
    # RF-05: Código único de validación para confirmar la entrega presencial
    codigo_recogida = db.Column(db.String(10), unique=True, nullable=True)
    
    # Flujo de estados: 'Pendiente', 'Completado', 'Expirado'
    estado = db.Column(db.String(20), default='Pendiente')

# ================================================================
# 3. LÓGICA DE NEGOCIO (ALGORITMOS Y SOPORTE)
# ================================================================

def generar_codigo_recogida():
    """ RF-05: Genera un identificador único alfanumérico de 6 caracteres """
    caracteres_validos = string.ascii_uppercase + string.digits
    while True:
        codigo = ''.join(random.choices(caracteres_validos, k=6))
        if not Transaccion.query.filter_by(codigo_recogida=codigo).first():
            return codigo

def limpiar_reservas_expiradas():
    """ HU-03: Libera el stock de productos cuyas reservas no fueron recogidas a tiempo """
    momento_actual = datetime.utcnow()
    expirados = Transaccion.query.filter_by(estado='Pendiente').filter(Transaccion.fecha_limite < momento_actual).all()
    
    for reserva in expirados:
        reserva.estado = 'Expirado'
        # Devolución de la unidad al inventario del establecimiento
        p_original = Producto.query.get(reserva.producto_id)
        if p_original:
            p_original.cantidad += reserva.cantidad
            p_original.estado = 'Activo'
            
    db.session.commit()

# ================================================================
# 4. LÓGICA DE INTELIGENCIA ARTIFICIAL (IA CÁLIDA Y PUNTUAL)
# ================================================================

@app.route('/ia_chat', methods=['POST'])
def ia_chat():
    """ 
    Procesa preguntas de usuario inyectando contexto real de la DB.
    Optimizado para LM Studio Bionic (Puerto 1235).
    """
    if 'user_id' not in session:
        return jsonify({"respuesta": "¡Hola! Por favor, inicia sesión para poder darte información precisa."}), 401
    
    u_sesion = Usuario.query.get(session['user_id'])
    pregunta_texto = request.json.get('mensaje')
    
    # Contexto geográfico (Grafos) y hechos de la DB
    motor_grafo = GrafoZonas()
    entorno_cercano = motor_grafo.obtener_zonas_cercanas(u_sesion.zona)
    
    locales_db = Usuario.query.filter_by(rol='dueño').all()
    ctx_locales = ", ".join([f"{d.nombre_establecimiento} (Zona: {d.zona}, Dir: {d.direccion_establecimiento})" for d in locales_db])
    
    ofertas_db = Producto.query.filter_by(estado='Activo').all()
    ctx_ofertas = ", ".join([f"{p.nombre} a ${int(p.precio_oferta)} en {p.zona}" for p in ofertas_db])

    # Instrucciones estrictas para Llama 3
    prompt_maestro = (
        f"Eres el asistente virtual amable de 'DON'T WASTE IT'. "
        f"Tu usuario está en {u_sesion.zona}. Zonas colindantes: {', '.join(entorno_cercano)}. \n"
        f"DATOS REALES: LOCALES: {ctx_locales if ctx_locales else 'Ninguno'}. "
        f"PRODUCTOS: {ctx_ofertas if ctx_ofertas else 'Ninguna oferta'}. \n"
        "REGLAS: 1. Sé servicial, puntual y usa un tono positivo. "
        "2. Responde en máximo 2 frases. 3. Solo usa datos anteriores. "
        "4. No hables en formato técnico ni JSON."
    )
    
    if 'historial_ia' not in session: session['historial_ia'] = []
    cuerpo_chat = [{"role": "system", "content": prompt_maestro}]
    for h in session['historial_ia'][-3:]: cuerpo_chat.append(h)
    cuerpo_chat.append({"role": "user", "content": pregunta_texto})

    try:
        solicitud_api = requests.post(LM_STUDIO_URL, json={
            "model": "local-model", "messages": cuerpo_chat, "temperature": 0.3, "max_tokens": 150, "tool_choice": "none"
        }, timeout=60)
        
        resultado_ia = solicitud_api.json()['choices'][0]['message']['content'].strip()
        
        session['historial_ia'].append({"role": "user", "content": pregunta_texto})
        session['historial_ia'].append({"role": "assistant", "content": resultado_ia})
        session.modified = True 
        
        return jsonify({"respuesta": resultado_ia})
    except Exception as error:
        print(f"Error IA: {error}")
        return jsonify({"respuesta": "¡Uy! Parece que tengo problemas para conectarme, ¿me preguntas de nuevo en un momento?"}), 503

@app.route('/limpiar_chat')
def limpiar_chat():
    """ Elimina la memoria del chat de la sesión actual """
    if 'historial_ia' in session:
        session.pop('historial_ia')
    return redirect(request.referrer or url_for('dashboard'))

# ================================================================
# 5. RUTAS DE NAVEGACIÓN Y LOGIN
# ================================================================

@app.route('/')
def inicio(): return render_template('inicio.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Captura extensiva de campos
        email_form = request.form.get('correo')
        if Usuario.query.filter_by(correo=email_form).first():
            flash("Este correo electrónico ya está registrado.", "danger")
            return redirect(url_for('registro'))
            
        u_nuevo = Usuario()
        u_nuevo.nombre = request.form.get('nombre')
        u_nuevo.correo = email_form
        u_nuevo.clave = generate_password_hash(request.form.get('clave'))
        u_nuevo.rol = request.form.get('rol')
        u_nuevo.zona = request.form.get('zona', 'Centro')
        
        if u_nuevo.rol == 'dueño':
            u_nuevo.nombre_establecimiento = request.form.get('nombre_establecimiento')
            u_nuevo.direccion_establecimiento = request.form.get('direccion_establecimiento')
            u_nuevo.tipo_establecimiento = request.form.get('tipo_establecimiento')
            
        db.session.add(u_nuevo); db.session.commit()
        flash("¡Bienvenido a la comunidad! Ya puedes iniciar sesión.", "success")
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u_login = Usuario.query.filter_by(correo=request.form.get('correo')).first()
        if u_login and check_password_hash(u_login.clave, request.form.get('clave')):
            session['user_id'] = u_login.id
            session['rol'] = u_login.rol
            session.pop('historial_ia', None) 
            return redirect(url_for('dashboard'))
        flash("Las credenciales son incorrectas. Inténtalo de nuevo.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('inicio'))

# ================================================================
# 6. DASHBOARDS (REPORTES Y FILTROS AVANZADOS)
# ================================================================

@app.route('/dashboard')
def dashboard():
    """ 
    Punto neurálgico del sistema. 
    Distribuye lógica de dueños (KPIs por fecha) y clientes (Filtros de rango). 
    """
    if 'user_id' not in session: return redirect(url_for('login'))
    
    u_perfil = Usuario.query.get(session.get('user_id'))
    if not u_perfil:
        session.clear(); return redirect(url_for('inicio'))
        
    seccion_ui = request.args.get('seccion', 'menu')
    chat_log_data = session.get('historial_ia', [])
    limpiar_reservas_expiradas() # Mantenimiento preventivo

    if u_perfil.rol == 'dueño':
        # --- LÓGICA DUEÑO: REPORTES POR PERIODO (RF-08) ---
        fecha_start = request.args.get('inicio')
        fecha_end = request.args.get('fin')
        
        q_ventas = db.session.query(
            Transaccion.nombre_producto, func.sum(Transaccion.cantidad).label('total'),
            func.sum(Transaccion.precio_pagado).label('dinero')
        ).filter(Transaccion.vendedor_id == u_perfil.id, Transaccion.estado == 'Completado')

        # Aplicación de filtros de fecha robustos
        if fecha_start and fecha_end:
            try:
                obj_i = datetime.strptime(fecha_start, '%Y-%m-%d')
                obj_f = datetime.strptime(fecha_end, '%Y-%m-%d') + timedelta(days=1)
                q_ventas = q_ventas.filter(Transaccion.fecha >= obj_i, Transaccion.fecha < obj_f)
            except ValueError: pass
        
        final_ventas = q_ventas.group_by(Transaccion.nombre_producto).all()
        orders_pendientes = Transaccion.query.filter_by(vendedor_id=u_perfil.id, estado='Pendiente').all()
        mis_items = Producto.query.filter_by(vendedor_id=u_perfil.id).all()
        
        return render_template('panel_dueño.html', user=u_perfil, ventas=final_ventas, 
                               pendientes=orders_pendientes, seccion=seccion_ui, productos=mis_items)
    
    else:
        # --- LÓGICA CLIENTE: FILTROS DE RANGO Y CATEGORÍA (RF-03) ---
        rango_p = request.args.get('rango', 'mi_zona') # Nuevo parámetro solicitado
        filtro_c = request.args.get('categoria')
        filtro_z = request.args.get('zona_filtro')
        
        # Consulta con JOIN para eficiencia de datos
        q_global = db.session.query(Producto, Usuario).join(Usuario, Producto.vendedor_id == Usuario.id).filter(Producto.estado == 'Activo')
        
        # Implementación de Filtros Lógicos
        if rango_p == 'mi_zona' and not filtro_c and not filtro_z:
            grafo_m = GrafoZonas()
            zonas_v = grafo_m.obtener_zonas_cercanas(u_perfil.zona)
            q_global = q_global.filter(Producto.zona.in_(zonas_v))
        
        # Si hay filtro de categoría, se busca de forma global tal como se pidió
        if filtro_c:
            q_global = q_global.filter(Producto.categoria == filtro_c)
            
        if filtro_z:
            q_global = q_global.filter(Producto.zona == filtro_z)

        # ORGANIZACIÓN POR PRECIO (ÁRBOL BINARIO DE BÚSQUEDA)
        arbol_bst = ArbolProductos()
        for prod_r, vend_r in q_global.all():
            arbol_bst.insertar({
                'id': prod_r.id, 'nombre': prod_r.nombre, 
                'precio_oferta': prod_r.precio_oferta, 'precio_original': prod_r.precio_original, 
                'zona': prod_r.zona, 'vendedor_nombre': vend_r.nombre_establecimiento or vend_r.nombre
            })
        
        res_ordenado = []
        if arbol_bst.raiz:
            arbol_bst.obtener_lista_ordenada(arbol_bst.raiz, res_ordenado)
        
        # Datos para selectores y secciones de la interfaz
        todas_categorias = [item[0] for item in db.session.query(Producto.categoria).distinct().all()]
        todas_zonas_db = [item[0] for item in db.session.query(Usuario.zona).filter(Usuario.rol == 'dueño').distinct().all()]
        
        # Navegación interna Establecimientos
        l_id_target = request.args.get('id_local')
        duenos_filtrados = Usuario.query.filter_by(rol='dueño', zona=filtro_z).all() if filtro_z else []
        items_local_target = Producto.query.filter_by(vendedor_id=l_id_target, estado='Activo').all() if l_id_target else []
        obj_local_target = Usuario.query.get(l_id_target) if l_id_target else None

        return render_template('panel_cliente.html', user=u_perfil, productos=res_ordenado, seccion=seccion_ui, 
                               compras=Transaccion.query.filter_by(cliente_id=u_perfil.id).order_by(Transaccion.fecha.desc()).all(),
                               categorias=todas_categorias, zonas=todas_zonas_db, dueños=duenos_filtrados, 
                               zona_sel=filtro_z, prods_local=items_local_target, local_sel=obj_local_target,
                               chat_log=chat_log_data, rango_sel=rango_p)

# ================================================================
# 7. ACCIONES DE PRODUCTO E INVENTARIO
# ================================================================

@app.route('/eliminar_producto/<int:id_p>')
def eliminar_producto(id_p):
    """ Permite al dueño borrar un excedente publicado (Nueva función) """
    p_item = Producto.query.get_or_404(id_p)
    # Validación de propiedad por seguridad
    if p_item.vendedor_id == session.get('user_id'):
        db.session.delete(p_item)
        db.session.commit()
        flash(f"El producto '{p_item.nombre}' ha sido eliminado exitosamente.", "info")
    return redirect(url_for('dashboard', seccion='productos'))

@app.route('/publicar', methods=['POST'])
def publicar():
    """ Procesa la creación de un nuevo excedente alimentario con manejo de errores """
    u_login = Usuario.query.get(session['user_id'])
    try:
        nom_p = request.form.get('nombre')
        # Captura y validación de campos obligatorios
        item_p = Producto(
            nombre=nom_p, categoria=request.form.get('categoria', 'Plato'),
            precio_original=float(request.form.get('original') or 0), 
            precio_oferta=float(request.form.get('oferta') or 0),
            cantidad=int(request.form.get('cantidad') or 1), 
            vendedor_id=u_login.id, zona=u_login.zona
        )
        db.session.add(item_p); db.session.commit()
        flash(f"¡Éxito! '{nom_p}' ya está publicado y listo para rescate.", "success")
    except Exception as e:
        print(f"Error publicación: {e}")
        flash("Hubo un error con los valores ingresados. Inténtalo de nuevo.", "danger")
    return redirect(url_for('dashboard', seccion='menu'))

@app.route('/editar_stock/<int:id_p>', methods=['POST'])
def editar_stock(id_p):
    """ Permite actualizar la cantidad de un excedente publicado """
    p_db = Producto.query.get_or_404(id_p)
    if p_db.vendedor_id == session.get('user_id'):
        cant_upd = int(request.form.get('nueva_cantidad') or 0)
        p_db.cantidad = cant_upd
        p_db.estado = 'Activo' if cant_upd > 0 else 'Agotado'
        db.session.commit()
        flash("El inventario ha sido actualizado correctamente.", "info")
    return redirect(url_for('dashboard', seccion='productos'))

# ================================================================
# 8. TRANSACCIONES Y VALIDACIONES (EL CORAZÓN DEL RESCATE)
# ================================================================

@app.route('/comprar/<int:id_p>')
def comprar(id_p):
    """ RF-04: Ejecuta la reserva, bloquea stock y genera el código de recogida """
    if 'user_id' not in session: return redirect(url_for('login'))
    
    p_rescue = Producto.query.get_or_404(id_p)
    if p_rescue.cantidad > 0:
        # Reducción inmediata de inventario
        p_rescue.cantidad -= 1
        if p_rescue.cantidad == 0: p_rescue.estado = 'Agotado'
        
        # Registro oficial de la reserva pendiente
        nueva_reserva = Transaccion(
            cliente_id=session['user_id'], producto_id=p_rescue.id, vendedor_id=p_rescue.vendedor_id,
            precio_pagado=p_rescue.precio_oferta, nombre_producto=p_rescue.nombre,
            codigo_recogida=generar_codigo_recogida(),
            # HU-03: Expiración en 2 horas para presionar la recogida real
            fecha_limite=datetime.utcnow() + timedelta(hours=2)
        )
        db.session.add(nueva_reserva); db.session.commit()
        flash(f"Reserva confirmada. Código: {nueva_reserva.codigo_recogida}. Tienes 2 horas para recogerlo.", "success")
        
    return redirect(url_for('dashboard', seccion='comprar'))

@app.route('/validar_codigo', methods=['POST'])
def validar_codigo():
    """ 
    RF-05 / RF-06: Validación de entrega y asignación de beneficios.
    Suma impacto ambiental tanto al CLIENTE como al DUEÑO.
    """
    input_cod = request.form.get('codigo', '').strip().upper()
    t_pend = Transaccion.query.filter_by(codigo_recogida=input_cod, estado='Pendiente').first()
    
    if t_pend and t_pend.vendedor_id == session['user_id']:
        # Paso 1: Finalizar la transacción
        t_pend.estado = 'Completado'
        
        # Paso 2: Identificación de actores para puntos/impacto
        c_obj = Usuario.query.get(t_pend.cliente_id)
        d_obj = Usuario.query.get(session['user_id']) # Dueño que valida
        p_obj = Producto.query.get(t_pend.producto_id)
        
        # Paso 3: Asignación de beneficios
        ahorro_val = p_obj.precio_original - p_obj.precio_oferta
        c_obj.puntos += 50
        c_obj.kg_rescatados += 0.5
        c_obj.ahorro_total += ahorro_val
        
        # CORRECCIÓN SOLICITADA: El dueño ahora también suma su impacto
        d_obj.kg_rescatados += 0.5 
        
        db.session.commit()
        flash(f"¡Rescate validado exitosamente! El impacto ambiental ha sido actualizado.", "success")
    else:
        flash("El código es inválido, ya fue usado o no corresponde a este local.", "danger")
        
    return redirect(url_for('dashboard', seccion='ventas'))

@app.route('/eliminar_compra/<int:id_t>')
def eliminar_compra(id_t):
    """ Permite cancelar rescates pendientes devolviendo stock al local """
    t_cancel = Transaccion.query.get_or_404(id_t)
    if t_cancel.cliente_id == session.get('user_id'):
        if t_cancel.estado == 'Pendiente':
            prod_ref = Producto.query.get(t_cancel.producto_id)
            if prod_ref: 
                prod_ref.cantidad += 1
                prod_ref.estado = 'Activo'
        db.session.delete(t_cancel)
        db.session.commit()
        flash("El registro ha sido eliminado del historial.", "info")
    return redirect(url_for('dashboard', seccion='comprar'))

# ================================================================
# 9. LANZAMIENTO DEL SERVIDOR
# ================================================================

if __name__ == '__main__':
    with app.app_context():
        # Sincronización automática de modelos con el archivo de base de datos
        db.create_all()
    # Ejecución en puerto 5000 (Modo Debug para desarrollo continuo)
    app.run(debug=True, port=5000)