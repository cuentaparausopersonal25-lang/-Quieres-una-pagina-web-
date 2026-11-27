import os, re, secrets
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from flask import Flask, render_template, redirect, url_for, flash, request, abort, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

BASE_DIR = Path(__file__).resolve().parent
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'
csrf = CSRFProtect()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(90), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(90), unique=True, nullable=False)
    description = db.Column(db.String(300), default='')
    image = db.Column(db.String(120), default='')
    models = db.relationship('SiteModel', backref='category', cascade='all, delete-orphan')

class SiteModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    description = db.Column(db.Text, default='')
    price = db.Column(db.Integer, default=45000)
    features = db.Column(db.Text, default='Diseño adaptable, formulario de contacto, secciones personalizables')
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    accent = db.Column(db.String(20), default='#2878e8')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('site_model.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id','model_id'),)
    model = db.relationship('SiteModel')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    model_id = db.Column(db.Integer, db.ForeignKey('site_model.id'))
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(160), default='')
    details = db.Column(db.Text, default='')
    status = db.Column(db.String(30), default='Nuevo')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    model = db.relationship('SiteModel')
    user = db.relationship('User')

class Setting(db.Model):
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, default='')

class CodeDraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    note = db.Column(db.String(250), default='')
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User')

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

CATEGORY_DATA = [
('Restaurantes','restaurantes','Sitios para restaurantes, pizzerías, hamburgueserías, cafeterías, heladerías y panaderías.','restaurant.svg'),
('Tiendas','tiendas','Catálogos y tiendas online para ropa, tecnología, zapatillas, juguetes y decoración.','store.svg'),
('Profesionales','profesionales','Presencia profesional para abogados, arquitectos, contadores, fotógrafos y consultores.','professional.svg'),
('Belleza','belleza','Diseños elegantes para peluquerías, barberías, estética, uñas y maquillaje.','beauty.svg'),
('Deportes','deportes','Webs para gimnasios, clubes, escuelas deportivas y entrenadores.','sports.svg'),
('Educación','educacion','Academias, escuelas, cursos, institutos y profesores particulares.','education.svg'),
('Automotores','automotores','Concesionarias, talleres, lavaderos, alquiler y repuestos.','auto.svg'),
('Turismo','turismo','Hoteles, cabañas, agencias, alojamientos y excursiones.','tourism.svg'),
('Empresas','empresas','Webs corporativas para servicios, tecnología, industria y distribución.','company.svg'),
('Eventos','eventos','Sitios para casamientos, cumpleaños, fiestas y eventos empresariales.','events.svg'),
('Salud','salud','Presencia digital para consultorios, odontología, nutrición y centros médicos.','health.svg'),
('Personalizadas','personalizadas','Portfolios, blogs, comunidades y proyectos especiales.','custom.svg')]
MODEL_NAMES = {
'restaurantes':['Mesa & Sabor','Pizzería Central'], 'tiendas':['Nébula Store','Urban Market'],
'profesionales':['Estudio Norte','Portfolio Ejecutivo'], 'belleza':['Aura Beauty','Barber Club'],
'deportes':['FitZone Gym','Club Activo'], 'educacion':['Aula Abierta','Academia Pro'],
'automotores':['Motor House','Taller Express'], 'turismo':['Destino Andino','Cabañas del Lago'],
'empresas':['Nova Corporativa','Soluciones Integrales'], 'eventos':['Día Especial','Eventos Premium'],
'salud':['Centro Vital','Sonrisa Salud'], 'personalizadas':['Creative Folio','Blog Horizonte']}
ACCENTS=['#2878e8','#10a9c8','#7457d5','#e05c91','#16a085','#d08b2d']

def setting(key, default=''):
    row=db.session.get(Setting,key)
    return row.value if row else default

def whatsapp_url(message):
    number = re.sub(r'\D','',setting('whatsapp_number', os.getenv('WHATSAPP_NUMBER','5493874833799')))
    return 'https://wa.me/'+number+'?text='+quote(message)

def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin: abort(403)

def create_app():
    app=Flask(__name__)
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32), SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL','sqlite:///'+str(BASE_DIR/'instance'/'agencia.db')).replace('postgres://','postgresql://',1), SQLALCHEMY_TRACK_MODIFICATIONS=False, MAX_CONTENT_LENGTH=3*1024*1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','false').lower()=='true')
    Path(app.instance_path).mkdir(parents=True,exist_ok=True)
    db.init_app(app); login_manager.init_app(app); csrf.init_app(app)
    @app.context_processor
    def inject_globals(): return {'site_name':'¿Quieres una página web?','tagline':'Tu idea, nuestra creación.','wa_link':whatsapp_url('Hola, quiero consultar por una página web.'),'money':lambda n: '$'+format(n or 0,',').replace(',','.'),'current_year':datetime.now().year}
    with app.app_context():
        db.create_all()
        if not Category.query.first():
            for name,slug,desc,img in CATEGORY_DATA: db.session.add(Category(name=name,slug=slug,description=desc,image=img))
            db.session.commit()
        if not SiteModel.query.first():
            for cat in Category.query.all():
                for i,name in enumerate(MODEL_NAMES.get(cat.slug,['Modelo Inicial','Modelo Plus'])):
                    db.session.add(SiteModel(name=name,slug=f'{cat.slug}-{i+1}',description=f'Una propuesta visual para {cat.name.lower()}, con contenido claro y llamadas a la acción. Personalizable con la identidad de tu negocio.',price=45000+i*20000,features='Diseño responsive, secciones editables, contacto directo, optimización básica',category_id=cat.id,accent=ACCENTS[(cat.id+i)%len(ACCENTS)]))
            db.session.commit()
        if not Setting.query.get('whatsapp_number'):
            db.session.add(Setting(key='whatsapp_number',value=os.getenv('WHATSAPP_NUMBER','5493874833799'))); db.session.commit()
    @app.route('/')
    def index():
        categories=Category.query.order_by(Category.name).all(); models=SiteModel.query.filter_by(active=True).order_by(SiteModel.created_at.desc()).limit(8).all()
        return render_template('index.html',categories=categories,models=models)
    @app.route('/catalogo')
    def catalog():
        q=request.args.get('q','').strip(); cat=request.args.get('categoria','')
        query=SiteModel.query.filter_by(active=True)
        if q: query=query.filter(or_(SiteModel.name.ilike(f'%{q}%'),SiteModel.description.ilike(f'%{q}%')))
        if cat: query=query.join(Category).filter(Category.slug==cat)
        return render_template('catalog.html',models=query.order_by(SiteModel.name).all(),categories=Category.query.order_by(Category.name).all(),q=q,selected=cat)
    @app.route('/categoria/<slug>')
    def category_page(slug):
        category=Category.query.filter_by(slug=slug).first_or_404()
        return render_template('category.html',category=category,models=SiteModel.query.filter_by(category_id=category.id,active=True).all())
    @app.route('/demo/<slug>')
    def demo(slug): return render_template('demo.html',model=SiteModel.query.filter_by(slug=slug,active=True).first_or_404())
    @app.route('/solicitar/<slug>',methods=['GET','POST'])
    def request_model(slug):
        model=SiteModel.query.filter_by(slug=slug,active=True).first_or_404()
        if request.method=='POST':
            name=request.form.get('name','').strip()[:100]; email=request.form.get('email','').strip()[:160]; details=request.form.get('details','').strip()[:1500]
            if len(name)<2: flash('Escribí tu nombre para continuar.','error')
            else:
                order=Order(user_id=current_user.id if current_user.is_authenticated else None,model_id=model.id,customer_name=name,customer_email=email,details=details)
                db.session.add(order); db.session.commit()
                msg=f'Hola, quiero solicitar una página web. Modelo: {model.name}. Categoría: {model.category.name}. Precio publicado: ${model.price}. Cliente: {name}. Email: {email or "No indicado"}. Detalles: {details or "Sin detalles adicionales"}. Pedido #{order.id}'
                return redirect(whatsapp_url(msg))
        return render_template('request.html',model=model)
    @app.route('/registro',methods=['GET','POST'])
    def register():
        if current_user.is_authenticated: return redirect(url_for('index'))
        if request.method=='POST':
            name=request.form.get('name','').strip()[:90]; email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
            if len(name)<2 or len(password)<8 or '@' not in email: flash('Completá los datos. La contraseña debe tener al menos 8 caracteres.','error')
            else:
                user=User(name=name,email=email); user.set_password(password); db.session.add(user)
                try: db.session.commit(); login_user(user); return redirect(url_for('profile'))
                except IntegrityError: db.session.rollback(); flash('Ese correo ya está registrado.','error')
        return render_template('auth.html',mode='register')
    @app.route('/ingresar',methods=['GET','POST'])
    def login():
        if current_user.is_authenticated: return redirect(url_for('profile'))
        if request.method=='POST':
            user=User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
            if user and user.check_password(request.form.get('password','')): login_user(user); return redirect(url_for('admin' if user.is_admin else 'profile'))
            flash('Correo o contraseña incorrectos.','error')
        return render_template('auth.html',mode='login')
    @app.route('/salir',methods=['POST'])
    @login_required
    def logout(): logout_user(); return redirect(url_for('index'))
    @app.route('/mi-cuenta',methods=['GET','POST'])
    @login_required
    def profile():
        if request.method=='POST':
            current_user.name=request.form.get('name',current_user.name).strip()[:90]; db.session.commit(); flash('Perfil actualizado.','success')
        return render_template('profile.html',orders=Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all(),favorites=Favorite.query.filter_by(user_id=current_user.id).all())
    @app.route('/favorito/<int:model_id>',methods=['POST'])
    @login_required
    def favorite(model_id):
        model=db.session.get(SiteModel,model_id) or abort(404); fav=Favorite.query.filter_by(user_id=current_user.id,model_id=model.id).first()
        if fav: db.session.delete(fav)
        else: db.session.add(Favorite(user_id=current_user.id,model_id=model.id))
        db.session.commit(); return redirect(request.referrer or url_for('catalog'))
    @app.route('/admin')
    @login_required
    def admin():
        admin_required()
        return render_template('admin/dashboard.html',models=SiteModel.query.count(),categories=Category.query.count(),orders=Order.query.count(),users=User.query.count(),recent=Order.query.order_by(Order.created_at.desc()).limit(8).all())
    @app.route('/admin/modelos',methods=['GET','POST'])
    @login_required
    def admin_models():
        admin_required()
        if request.method=='POST':
            name=request.form.get('name','').strip(); cat=db.session.get(Category,int(request.form.get('category_id',0)))
            if not name or not cat: flash('Nombre y categoría son obligatorios.','error')
            else:
                slug=re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')+'-'+secrets.token_hex(3)
                db.session.add(SiteModel(name=name[:120],slug=slug,description=request.form.get('description','')[:2000],price=max(0,int(request.form.get('price',0))),features=request.form.get('features','')[:1000],category_id=cat.id,accent=request.form.get('accent','#2878e8'))); db.session.commit(); flash('Modelo creado.','success')
        return render_template('admin/models.html',models=SiteModel.query.order_by(SiteModel.id.desc()).all(),categories=Category.query.all())
    @app.route('/admin/modelo/<int:model_id>/eliminar',methods=['POST'])
    @login_required
    def delete_model(model_id):
        admin_required(); model=db.session.get(SiteModel,model_id) or abort(404); db.session.delete(model); db.session.commit(); flash('Modelo eliminado.','success'); return redirect(url_for('admin_models'))
    @app.route('/admin/categorias',methods=['GET','POST'])
    @login_required
    def admin_categories():
        admin_required()
        if request.method=='POST':
            name=request.form.get('name','').strip(); desc=request.form.get('description','').strip()
            if name:
                slug=re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')+'-'+secrets.token_hex(2); db.session.add(Category(name=name[:80],slug=slug,description=desc[:300],image='custom.svg')); db.session.commit(); flash('Categoría creada.','success')
        return render_template('admin/categories.html',categories=Category.query.all())
    @app.route('/admin/pedidos')
    @login_required
    def admin_orders():
        admin_required(); return render_template('admin/orders.html',orders=Order.query.order_by(Order.created_at.desc()).all())
    @app.route('/admin/pedido/<int:order_id>',methods=['POST'])
    @login_required
    def update_order(order_id):
        admin_required(); order=db.session.get(Order,order_id) or abort(404); status=request.form.get('status','Nuevo')
        if status in ['Nuevo','En conversación','Confirmado','Finalizado','Cancelado']: order.status=status; db.session.commit()
        return redirect(url_for('admin_orders'))
    @app.route('/admin/usuarios')
    @login_required
    def admin_users():
        admin_required(); return render_template('admin/users.html',users=User.query.order_by(User.created_at.desc()).all())
    @app.route('/admin/ajustes',methods=['GET','POST'])
    @login_required
    def admin_settings():
        admin_required()
        if request.method=='POST':
            number=re.sub(r'\D','',request.form.get('whatsapp_number',''))
            if len(number)<10 or len(number)>15: flash('Ingresá un número internacional válido, solo dígitos.','error')
            else:
                row=db.session.get(Setting,'whatsapp_number') or Setting(key='whatsapp_number'); row.value=number; db.session.add(row); db.session.commit(); flash('WhatsApp actualizado.','success')
        return render_template('admin/settings.html',number=setting('whatsapp_number'))
    @app.route('/admin/codigo',methods=['GET','POST'])
    @login_required
    def code_editor():
        admin_required()
        allowed={'static/css/style.css','templates/index.html','templates/demo.html'}
        if request.method=='POST':
            filename=request.form.get('filename',''); content=request.form.get('content','')
            if filename not in allowed: abort(400)
            if len(content)>50000: flash('El borrador supera el límite de 50 KB.','error')
            elif filename.endswith('.html') and ('<script' in content.lower() and 'nonce=' not in content.lower()): flash('Revisá el HTML: los scripts inline no están permitidos en borradores.','error')
            else:
                db.session.add(CodeDraft(filename=filename,content=content,note=request.form.get('note','')[:250],author_id=current_user.id)); db.session.commit(); flash('Borrador guardado como versión. No se ejecutó ni se publicó.','success')
        drafts=CodeDraft.query.order_by(CodeDraft.created_at.desc()).limit(30).all()
        selected=request.args.get('file','static/css/style.css')
        if selected not in allowed: selected='static/css/style.css'
        source=(BASE_DIR/selected).read_text(encoding='utf-8')
        return render_template('admin/code.html',allowed=sorted(allowed),selected=selected,source=source,drafts=drafts)
    @app.cli.command('create-admin')
    def create_admin():
        import getpass
        email=input('Correo del administrador: ').strip().lower(); name=input('Nombre: ').strip(); password=getpass.getpass('Contraseña (mínimo 12 caracteres): ')
        if len(password)<12: print('La contraseña debe tener al menos 12 caracteres.'); return
        if User.query.filter_by(email=email).first(): print('Ese correo ya existe.'); return
        user=User(name=name,email=email,is_admin=True); user.set_password(password); db.session.add(user); db.session.commit(); print('Administrador creado correctamente.')
    @app.errorhandler(403)
    def forbidden(e): return render_template('error.html',code=403,message='No tenés permiso para entrar acá.'),403
    @app.errorhandler(404)
    def not_found(e): return render_template('error.html',code=404,message='No encontramos esa página.'),404
    return app
