from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS manufacturers (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 manufacturer_id INTEGER,
                 commercial_name TEXT NOT NULL,
                 technical_name TEXT,
                 counter_type TEXT,
                 description TEXT,
                 FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS synonyms (
                 product_id INTEGER,
                 synonym_product_id INTEGER,
                 FOREIGN KEY (product_id) REFERENCES products(id),
                 FOREIGN KEY (synonym_product_id) REFERENCES products(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 contact TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS characteristics (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 product_id INTEGER,
                 name TEXT NOT NULL,
                 unit TEXT,
                 min_value REAL,
                 max_value REAL,
                 FOREIGN KEY (product_id) REFERENCES products(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS bulletins (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 entry_type TEXT,
                 invoice_pdc TEXT,
                 supplier_id INTEGER,
                 invoice_number TEXT,
                 supplier_lot TEXT,
                 manufacturing_date TEXT,
                 expiration_date TEXT,
                 unit_measure TEXT,
                 quantity REAL,
                 packaging TEXT,
                 conversion_factor REAL,
                 erp_code TEXT,
                 internal_lot TEXT,
                 product_id INTEGER,
                 receipt_date TEXT,
                 pdf_path TEXT,
                 status TEXT,
                 FOREIGN KEY (product_id) REFERENCES products(id),
                 FOREIGN KEY (supplier_id) REFERENCES suppliers(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS bulletin_characteristics (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 bulletin_id INTEGER,
                 characteristic_id INTEGER,
                 value REAL,
                 FOREIGN KEY (bulletin_id) REFERENCES bulletins(id),
                 FOREIGN KEY (characteristic_id) REFERENCES characteristics(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 cnpj TEXT,
                 address TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT b.*, p.commercial_name, s.name FROM bulletins b JOIN products p ON b.product_id = p.id JOIN suppliers s ON b.supplier_id = s.id")
    bulletins = c.fetchall()
    conn.close()
    return render_template('index.html', bulletins=bulletins)

@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        cnpj = request.form['cnpj']
        address = request.form['address']
        conn = sqlite3.connect('chemicals.db')
        c = conn.cursor()
        c.execute("INSERT INTO clients (name, cnpj, address) VALUES (?, ?, ?)", (name, cnpj, address))
        conn.commit()
        conn.close()
        return redirect(url_for('list_clients'))
    return render_template('add_client.html')

@app.route('/list_clients')
def list_clients():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT id, name, cnpj, address FROM clients")
    clients = c.fetchall()
    conn.close()
    return render_template('list_clients.html', clients=clients)

@app.route('/delete_client/<int:id>', methods=['POST'])
def delete_client(id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_clients'))

@app.route('/add_manufacturer', methods=['GET', 'POST'])
def add_manufacturer():
    if request.method == 'POST':
        name = request.form['name']
        conn = sqlite3.connect('chemicals.db')
        c = conn.cursor()
        c.execute("INSERT INTO manufacturers (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_manufacturer.html')

@app.route('/list_manufacturers')
def list_manufacturers():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM manufacturers")
    manufacturers = c.fetchall()
    conn.close()
    return render_template('list_manufacturers.html', manufacturers=manufacturers)

@app.route('/delete_manufacturer/<int:id>', methods=['POST'])
def delete_manufacturer(id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products WHERE manufacturer_id = ?", (id,))
    product_count = c.fetchone()[0]
    if product_count == 0:
        c.execute("DELETE FROM manufacturers WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('list_manufacturers'))

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM manufacturers")
    manufacturers = c.fetchall()
    c.execute("SELECT id, commercial_name FROM products")
    products = c.fetchall()
    conn.close()

    if request.method == 'POST':
        manufacturer_id = request.form['manufacturer_id']
        commercial_name = request.form['commercial_name']
        technical_name = request.form['technical_name']
        counter_type = request.form['counter_type']
        description = request.form['description']
        synonym_ids = request.form.getlist('synonym_ids')
        conn = sqlite3.connect('chemicals.db')
        c = conn.cursor()
        c.execute("INSERT INTO products (manufacturer_id, commercial_name, technical_name, counter_type, description) VALUES (?, ?, ?, ?, ?)",
                  (manufacturer_id, commercial_name, technical_name, counter_type, description))
        product_id = c.lastrowid
        for synonym_id in synonym_ids:
            c.execute("INSERT INTO synonyms (product_id, synonym_product_id) VALUES (?, ?)", (product_id, synonym_id))
            c.execute("INSERT INTO characteristics (product_id, name, unit, min_value, max_value) SELECT ?, name, unit, min_value, max_value FROM characteristics WHERE product_id = ?", (product_id, synonym_id))
        conn.commit()
        conn.close()
        return redirect(url_for('list_products'))
    return render_template('add_product.html', manufacturers=manufacturers, products=products)

@app.route('/list_products')
def list_products():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT p.id, p.commercial_name, m.name FROM products p JOIN manufacturers m ON p.manufacturer_id = m.id")
    products = c.fetchall()
    conn.close()
    return render_template('list_products.html', products=products)

@app.route('/delete_product/<int:id>', methods=['POST'])
def delete_product(id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM bulletins WHERE product_id = ?", (id,))
    bulletin_count = c.fetchone()[0]
    if bulletin_count == 0:
        c.execute("DELETE FROM products WHERE id = ?", (id,))
        c.execute("DELETE FROM characteristics WHERE product_id = ?", (id,))
        c.execute("DELETE FROM synonyms WHERE product_id = ? OR synonym_product_id = ?", (id, id))
        conn.commit()
    conn.close()
    return redirect(url_for('list_products'))

@app.route('/view_characteristics/<int:product_id>')
def view_characteristics(product_id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT c.id, c.name, c.unit, c.min_value, c.max_value FROM characteristics c WHERE c.product_id = ?", (product_id,))
    characteristics = c.fetchall()
    c.execute("SELECT commercial_name FROM products WHERE id = ?", (product_id,))
    product_name = c.fetchone()[0]
    conn.close()
    return render_template('view_characteristics.html', characteristics=characteristics, product_id=product_id, product_name=product_name)

@app.route('/delete_characteristic/<int:characteristic_id>', methods=['POST'])
def delete_characteristic(characteristic_id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM bulletin_characteristics WHERE characteristic_id = ?", (characteristic_id,))
    usage_count = c.fetchone()[0]
    if usage_count == 0:
        c.execute("SELECT product_id FROM characteristics WHERE id = ?", (characteristic_id,))
        product_id = c.fetchone()[0]
        c.execute("DELETE FROM characteristics WHERE id = ?", (characteristic_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('view_characteristics', product_id=product_id))
    conn.close()
    return redirect(url_for('view_characteristics', product_id=request.form.get('product_id')), code=303)

@app.route('/add_supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        conn = sqlite3.connect('chemicals.db')
        c = conn.cursor()
        c.execute("INSERT INTO suppliers (name, contact) VALUES (?, ?)", (name, contact))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_supplier.html')

@app.route('/list_suppliers')
def list_suppliers():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT id, name, contact FROM suppliers")
    suppliers = c.fetchall()
    conn.close()
    return render_template('list_suppliers.html', suppliers=suppliers)

@app.route('/delete_supplier/<int:id>', methods=['POST'])
def delete_supplier(id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM bulletins WHERE supplier_id = ?", (id,))
    bulletin_count = c.fetchone()[0]
    if bulletin_count == 0:
        c.execute("DELETE FROM suppliers WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('list_suppliers'))

@app.route('/add_characteristic/<int:product_id>', methods=['GET', 'POST'])
def add_characteristic(product_id):
    if request.method == 'POST':
        name = request.form['name']
        unit = request.form['unit']
        min_value = float(request.form['min_value']) if request.form['min_value'] else None
        max_value = float(request.form['max_value']) if request.form['max_value'] else None
        method = request.form['method']  # Novo campo
        conn = sqlite3.connect('chemicals.db')
        c = conn.cursor()
        c.execute("INSERT INTO characteristics (product_id, name, unit, min_value, max_value, method) VALUES (?, ?, ?, ?, ?, ?)",
                  (product_id, name, unit, min_value, max_value, method))
        conn.commit()
        conn.close()
        return redirect(url_for('view_characteristics', product_id=product_id))
    return render_template('add_characteristic.html', product_id=product_id)

@app.route('/edit_characteristic/<int:characteristic_id>', methods=['GET', 'POST'])
def edit_characteristic(characteristic_id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        unit = request.form['unit']
        min_value = float(request.form['min_value']) if request.form['min_value'] else None
        max_value = float(request.form['max_value']) if request.form['max_value'] else None
        method = request.form['method']
        c.execute("UPDATE characteristics SET name = ?, unit = ?, min_value = ?, max_value = ?, method = ? WHERE id = ?",
                  (name, unit, min_value, max_value, method, characteristic_id))
        conn.commit()
        c.execute("SELECT product_id FROM characteristics WHERE id = ?", (characteristic_id,))
        product_id = c.fetchone()[0]
        conn.close()
        return redirect(url_for('view_characteristics', product_id=product_id))
    
    c.execute("SELECT id, name, unit, min_value, max_value, method, product_id FROM characteristics WHERE id = ?", (characteristic_id,))
    characteristic = c.fetchone()
    conn.close()
    return render_template('edit_characteristic.html', characteristic=characteristic)

@app.route('/add_bulletin', methods=['GET', 'POST'])
def add_bulletin():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT id, commercial_name FROM products")
    products = c.fetchall()
    c.execute("SELECT id, name FROM suppliers")
    suppliers = c.fetchall()
    
    product_id = request.args.get('product_id')
    if request.method == 'POST' and not product_id:
        product_id = request.form.get('product_id')

    characteristics = []
    if product_id:
        try:
            product_id = int(product_id)
            c.execute("SELECT id, name, unit, min_value, max_value FROM characteristics WHERE product_id = ?", (product_id,))
            characteristics = c.fetchall()
        except ValueError:
            characteristics = []
    
    conn.close()

    if request.method == 'POST':
        entry_type = request.form['entry_type']
        invoice_pdc = request.form['invoice_pdc']
        supplier_id = request.form['supplier_id']
        invoice_number = request.form['invoice_number']
        supplier_lot = request.form['supplier_lot']
        manufacturing_date = request.form['manufacturing_date']
        expiration_date = request.form['expiration_date']
        unit_measure = request.form['unit_measure']
        quantity = float(request.form['quantity']) if request.form['quantity'] else None
        packaging = request.form['packaging']
        conversion_factor = float(request.form['conversion_factor']) if request.form['conversion_factor'] else None
        erp_code = request.form['erp_code']
        internal_lot = request.form['internal_lot']
        product_id = request.form['product_id']
        receipt_date = datetime.now().strftime("%Y-%m-%d")

        pdf_path = None
        if 'pdf_file' in request.files:
            file = request.files['pdf_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{internal_lot or supplier_lot}_{filename}")
                file.save(pdf_path)

        conn = sqlite3.connect('chemicals.db')
        c = conn.cursor()
        c.execute("""INSERT INTO bulletins (entry_type, invoice_pdc, supplier_id, invoice_number, supplier_lot, manufacturing_date, expiration_date, unit_measure, quantity, packaging, conversion_factor, erp_code, internal_lot, product_id, receipt_date, pdf_path, status) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (entry_type, invoice_pdc, supplier_id, invoice_number, supplier_lot, manufacturing_date, expiration_date, unit_measure, quantity, packaging, conversion_factor, erp_code, internal_lot, product_id, receipt_date, pdf_path, "Pendente"))
        bulletin_id = c.lastrowid

        for char_id in request.form.getlist('characteristic_ids'):
            value = request.form.get(f'value_{char_id}')
            if value:
                c.execute("INSERT INTO bulletin_characteristics (bulletin_id, characteristic_id, value) VALUES (?, ?, ?)",
                          (bulletin_id, char_id, float(value) if value else None))

        new_char_names = request.form.getlist('new_char_name[]')
        new_char_units = request.form.getlist('new_char_unit[]')
        new_char_min_values = request.form.getlist('new_char_min_value[]')
        new_char_max_values = request.form.getlist('new_char_max_value[]')
        new_char_values = request.form.getlist('new_char_value[]')

        for name, unit, min_val, max_val, value in zip(new_char_names, new_char_units, new_char_min_values, new_char_max_values, new_char_values):
            if name:
                c.execute("INSERT INTO characteristics (product_id, name, unit, min_value, max_value) VALUES (?, ?, ?, ?, ?)",
                          (product_id, name, unit, float(min_val) if min_val else None, float(max_val) if max_val else None))
                char_id = c.lastrowid
                if value:
                    c.execute("INSERT INTO bulletin_characteristics (bulletin_id, characteristic_id, value) VALUES (?, ?, ?)",
                              (bulletin_id, char_id, float(value) if value else None))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add_bulletin.html', products=products, suppliers=suppliers, characteristics=characteristics, product_id=product_id)

@app.route('/list_bulletins')
def list_bulletins():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT b.id, b.supplier_lot, b.internal_lot, p.commercial_name, s.name, b.entry_type, b.invoice_pdc, b.receipt_date, b.status, b.pdf_path FROM bulletins b JOIN products p ON b.product_id = p.id JOIN suppliers s ON b.supplier_id = s.id")
    bulletins = c.fetchall()
    conn.close()
    return render_template('list_bulletins.html', bulletins=bulletins)

@app.route('/delete_bulletin/<int:id>', methods=['POST'])
def delete_bulletin(id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("DELETE FROM bulletin_characteristics WHERE bulletin_id = ?", (id,))
    c.execute("DELETE FROM bulletins WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_bulletins'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/generate_certificate/<int:bulletin_id>', methods=['GET', 'POST'])
def generate_certificate(bulletin_id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT b.*, p.commercial_name, s.name AS supplier_name, m.name AS manufacturer_name FROM bulletins b JOIN products p ON b.product_id = p.id JOIN suppliers s ON b.supplier_id = s.id JOIN manufacturers m ON p.manufacturer_id = m.id WHERE b.id = ?", (bulletin_id,))
    bulletin = c.fetchone()
    c.execute("SELECT c.id, c.name, c.unit, c.min_value, c.max_value, bc.value, c.method FROM characteristics c LEFT JOIN bulletin_characteristics bc ON c.id = bc.characteristic_id AND bc.bulletin_id = ? WHERE c.product_id = ?", (bulletin_id, bulletin[14]))
    characteristics = c.fetchall()
    c.execute("SELECT id, name FROM clients")
    clients = c.fetchall()
    conn.close()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        if client_id:
            conn = sqlite3.connect('chemicals.db')
            c = conn.cursor()
            c.execute("SELECT name FROM clients WHERE id = ?", (client_id,))
            client_name = c.fetchone()[0]
            conn.close()
        else:
            client_name = request.form['client_name']
        quantity_sold = float(request.form['quantity_sold'])
        invoice_number = request.form['invoice_number']
        issue_date = request.form['issue_date']

        certificate_data = {
            'emitter': 'AGLUTINA',
            'client_name': client_name,
            'invoice_number': invoice_number,
            'issue_date': issue_date,
            'product': bulletin[18],
            'quantity_sold': quantity_sold,
            'manufacturing_date': bulletin[6],
            'expiration_date': bulletin[7],
            'characteristics': []
        }

        for char in characteristics:
            char_id, char_name, char_unit, char_min, char_max, char_value, char_method = char
            status = "APROVADO" if (char_value is not None and char_min <= char_value <= char_max) else "REPROVADO" if char_value is not None else "NÃO TESTADO"
            certificate_data['characteristics'].append({
                'name': char_name,
                'unit': char_unit,
                'min': char_min,
                'max': char_max,
                'value': char_value,
                'method': char_method or 'N/A',
                'status': status
            })

        return render_template('certificate.html', certificate=certificate_data)

    return render_template('generate_certificate.html', bulletin=bulletin, clients=clients)

@app.route('/generate_original_certificate/<int:bulletin_id>')
def generate_original_certificate(bulletin_id):
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT b.*, p.commercial_name, s.name AS supplier_name, m.name AS manufacturer_name FROM bulletins b JOIN products p ON b.product_id = p.id JOIN suppliers s ON b.supplier_id = s.id JOIN manufacturers m ON p.manufacturer_id = m.id WHERE b.id = ?", (bulletin_id,))
    bulletin = c.fetchone()
    c.execute("SELECT c.id, c.name, c.unit, c.min_value, c.max_value, bc.value FROM characteristics c LEFT JOIN bulletin_characteristics bc ON c.id = bc.characteristic_id AND bc.bulletin_id = ? WHERE c.product_id = ?", (bulletin_id, bulletin[14]))
    characteristics = c.fetchall()
    conn.close()

    certificate_data = {
        'emitter': bulletin[19],  # Nome do fabricante original
        'supplier_name': bulletin[18],  # Nome do fornecedor
        'invoice_number': bulletin[4],
        'issue_date': bulletin[15],  # Data de recebimento
        'product': bulletin[17],
        'quantity': bulletin[9],
        'unit_measure': bulletin[8],
        'supplier_lot': bulletin[5],
        'internal_lot': bulletin[13],
        'manufacturing_date': bulletin[6],
        'expiration_date': bulletin[7],
        'characteristics': []
    }

    for char in characteristics:
        char_id, char_name, char_unit, char_min, char_max, char_value = char
        certificate_data['characteristics'].append({
            'name': char_name,
            'unit': char_unit,
            'min': char_min,
            'max': char_max,
            'value': char_value,
            'method': 'N/A'
        })

    return render_template('original_certificate.html', certificate=certificate_data)

@app.route('/search_bulletins', methods=['GET', 'POST'])
def search_bulletins():
    conn = sqlite3.connect('chemicals.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM suppliers")
    suppliers = c.fetchall()
    c.execute("SELECT id, name FROM manufacturers")
    manufacturers = c.fetchall()

    bulletins = []
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id', '')
        manufacturer_id = request.form.get('manufacturer_id', '')
        invoice_pdc = request.form.get('invoice_pdc', '')
        invoice_number = request.form.get('invoice_number', '')

        query = """SELECT b.id, b.supplier_lot, b.internal_lot, p.commercial_name, s.name, b.entry_type, b.invoice_pdc, b.receipt_date, b.status, b.invoice_number, m.name
                   FROM bulletins b 
                   JOIN products p ON b.product_id = p.id 
                   JOIN suppliers s ON b.supplier_id = s.id 
                   JOIN manufacturers m ON p.manufacturer_id = m.id 
                   WHERE 1=1"""
        params = []

        if supplier_id:
            query += " AND b.supplier_id = ?"
            params.append(supplier_id)
        if manufacturer_id:
            query += " AND p.manufacturer_id = ?"
            params.append(manufacturer_id)
        if invoice_pdc:
            query += " AND b.invoice_pdc LIKE ?"
            params.append(f"%{invoice_pdc}%")
        if invoice_number:
            query += " AND b.invoice_number LIKE ?"
            params.append(f"%{invoice_number}%")

        c.execute(query, params)
        bulletins = c.fetchall()

    conn.close()
    return render_template('search_bulletins.html', suppliers=suppliers, manufacturers=manufacturers, bulletins=bulletins)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)