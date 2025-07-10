import os
import json
import logging
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from app import app
from models import Transaction, BankTemplate, AccountingMapping, CustomRule
from utils.pdf_processor import PDFProcessor
from utils.transaction_mapper import TransactionMapper
from utils.file_handlers import FileHandler
from utils.export_manager import ExportManager

# Configure logging
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main dashboard"""
    try:
        # Get transaction statistics
        transactions = FileHandler.load_transactions()
        total_transactions = len(transactions)
        mapped_transactions = sum(1 for t in transactions if t.rotulo_contabil)
        
        # Get recent transactions
        recent_transactions = sorted(transactions, key=lambda x: x.data, reverse=True)[:5]
        
        stats = {
            'total_transactions': total_transactions,
            'mapped_transactions': mapped_transactions,
            'unmapped_transactions': total_transactions - mapped_transactions,
            'mapping_percentage': round((mapped_transactions / total_transactions * 100) if total_transactions > 0 else 0, 1)
        }
        
        return render_template('index.html', stats=stats, recent_transactions=recent_transactions)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('index.html', stats={'total_transactions': 0, 'mapped_transactions': 0, 'unmapped_transactions': 0, 'mapping_percentage': 0}, recent_transactions=[])

@app.route('/import', methods=['GET', 'POST'])
def import_statement():
    """Import bank statements"""
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(request.url)
            
            if file:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Get selected bank template
                bank_template = request.form.get('bank_template', 'auto')
                
                # Process the file
                processor = PDFProcessor()
                transactions = processor.process_file(filepath, bank_template)
                
                if transactions:
                    # Map transactions automatically
                    mapper = TransactionMapper()
                    mapped_transactions = []
                    for transaction in transactions:
                        mapped_transaction = mapper.map_transaction(transaction)
                        mapped_transactions.append(mapped_transaction)
                    
                    # Save transactions
                    existing_transactions = FileHandler.load_transactions()
                    all_transactions = existing_transactions + mapped_transactions
                    FileHandler.save_transactions(all_transactions)
                    
                    flash(f'Arquivo importado com sucesso! {len(mapped_transactions)} transações processadas.', 'success')
                    return redirect(url_for('transactions'))
                else:
                    flash('Não foi possível processar o arquivo. Verifique o formato e tente novamente.', 'error')
                    return redirect(request.url)
                    
        except Exception as e:
            logger.error(f"Error importing file: {str(e)}")
            flash(f'Erro ao importar arquivo: {str(e)}', 'error')
            return redirect(request.url)
    
    # Get available templates
    templates = FileHandler.load_bank_templates()
    return render_template('import.html', templates=templates)

@app.route('/transactions')
def transactions():
    """View and manage transactions"""
    try:
        # Get filter parameters
        bank_filter = request.args.get('bank', '')
        mapping_filter = request.args.get('mapping', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Load transactions
        all_transactions = FileHandler.load_transactions()
        
        # Apply filters
        filtered_transactions = all_transactions
        if bank_filter:
            filtered_transactions = [t for t in filtered_transactions if t.banco == bank_filter]
        if mapping_filter == 'mapped':
            filtered_transactions = [t for t in filtered_transactions if t.rotulo_contabil]
        elif mapping_filter == 'unmapped':
            filtered_transactions = [t for t in filtered_transactions if not t.rotulo_contabil]
        if date_from:
            filtered_transactions = [t for t in filtered_transactions if t.data >= date_from]
        if date_to:
            filtered_transactions = [t for t in filtered_transactions if t.data <= date_to]
        
        # Sort by date (newest first)
        filtered_transactions.sort(key=lambda x: x.data, reverse=True)
        
        # Get unique banks for filter
        banks = sorted(list(set(t.banco for t in all_transactions)))
        
        return render_template('transactions.html', 
                             transactions=filtered_transactions, 
                             banks=banks,
                             current_filters={
                                 'bank': bank_filter,
                                 'mapping': mapping_filter,
                                 'date_from': date_from,
                                 'date_to': date_to
                             })
    except Exception as e:
        logger.error(f"Error loading transactions: {str(e)}")
        flash(f'Erro ao carregar transações: {str(e)}', 'error')
        return render_template('transactions.html', transactions=[], banks=[], current_filters={})

@app.route('/transactions/edit/<transaction_id>', methods=['POST'])
def edit_transaction(transaction_id):
    """Edit a transaction"""
    try:
        transactions = FileHandler.load_transactions()
        transaction = next((t for t in transactions if t.id == transaction_id), None)
        
        if not transaction:
            flash('Transação não encontrada', 'error')
            return redirect(url_for('transactions'))
        
        # Update transaction
        transaction.rotulo_contabil = request.form.get('rotulo_contabil', '')
        transaction.conta_debito = request.form.get('conta_debito', '')
        transaction.conta_credito = request.form.get('conta_credito', '')
        transaction.historico_contabil = request.form.get('historico_contabil', '')
        transaction.revisado_manualmente = True
        
        # Check if user wants to create a rule
        create_rule = request.form.get('create_rule', False)
        if create_rule:
            rule_type = request.form.get('rule_type', 'contains')
            
            # Create custom rule
            custom_rule = CustomRule(
                termo_chave=transaction.descricao_normalizada,
                corresponde_exatamente=(rule_type == 'exact'),
                considerar_valor=(rule_type == 'exact_value'),
                valor_exato=transaction.valor if rule_type == 'exact_value' else None,
                tipo_movimentacao_regra=transaction.tipo_movimentacao.lower(),
                rotulo_contabil_aplicar=transaction.rotulo_contabil,
                conta_debito_aplicar=transaction.conta_debito,
                conta_credito_aplicar=transaction.conta_credito,
                historico_contabil_aplicar=transaction.historico_contabil
            )
            
            # Save rule
            rules = FileHandler.load_custom_rules()
            rules.append(custom_rule)
            FileHandler.save_custom_rules(rules)
            
            # Apply rule to similar transactions
            mapper = TransactionMapper()
            for t in transactions:
                if t.id != transaction_id and not t.revisado_manualmente:
                    if mapper.matches_custom_rule(t, custom_rule):
                        t.rotulo_contabil = custom_rule.rotulo_contabil_aplicar
                        t.conta_debito = custom_rule.conta_debito_aplicar
                        t.conta_credito = custom_rule.conta_credito_aplicar
                        t.historico_contabil = custom_rule.historico_contabil_aplicar
        
        # Save transactions
        FileHandler.save_transactions(transactions)
        
        flash('Transação atualizada com sucesso!', 'success')
        return redirect(url_for('transactions'))
        
    except Exception as e:
        logger.error(f"Error editing transaction: {str(e)}")
        flash(f'Erro ao editar transação: {str(e)}', 'error')
        return redirect(url_for('transactions'))

@app.route('/transactions/remap', methods=['POST'])
def remap_transactions():
    """Remap all transactions"""
    try:
        transactions = FileHandler.load_transactions()
        mapper = TransactionMapper()
        
        for transaction in transactions:
            if not transaction.revisado_manualmente:
                mapped_transaction = mapper.map_transaction(transaction)
                transaction.rotulo_contabil = mapped_transaction.rotulo_contabil
                transaction.conta_debito = mapped_transaction.conta_debito
                transaction.conta_credito = mapped_transaction.conta_credito
                transaction.historico_contabil = mapped_transaction.historico_contabil
        
        FileHandler.save_transactions(transactions)
        flash('Transações remapeadas com sucesso!', 'success')
        
    except Exception as e:
        logger.error(f"Error remapping transactions: {str(e)}")
        flash(f'Erro ao remapear transações: {str(e)}', 'error')
    
    return redirect(url_for('transactions'))

@app.route('/transactions/clear', methods=['POST'])
def clear_transactions():
    """Clear all transactions"""
    try:
        FileHandler.save_transactions([])
        flash('Todas as transações foram removidas!', 'success')
    except Exception as e:
        logger.error(f"Error clearing transactions: {str(e)}")
        flash(f'Erro ao limpar transações: {str(e)}', 'error')
    
    return redirect(url_for('transactions'))

@app.route('/templates')
def templates():
    """Manage bank templates"""
    try:
        templates = FileHandler.load_bank_templates()
        return render_template('templates.html', templates=templates)
    except Exception as e:
        logger.error(f"Error loading templates: {str(e)}")
        return render_template('templates.html', templates=[])

@app.route('/templates/create', methods=['POST'])
def create_template():
    """Create a new bank template"""
    try:
        template = BankTemplate(
            banco=request.form.get('banco'),
            formato=request.form.get('formato'),
            regex_data=request.form.get('regex_data'),
            regex_valor=request.form.get('regex_valor'),
            regex_descricao=request.form.get('regex_descricao'),
            modo_leitura=request.form.get('modo_leitura'),
            linhas_ignoradas_topo=int(request.form.get('linhas_ignoradas_topo', 0)),
            linhas_ignoradas_rodape=int(request.form.get('linhas_ignoradas_rodape', 0))
        )
        
        # Handle CSV columns if applicable
        if template.formato == 'csv':
            template.colunas_csv = {
                'data': int(request.form.get('col_data', 0)),
                'descricao': int(request.form.get('col_descricao', 1)),
                'valor': int(request.form.get('col_valor', 2)),
                'saldo': int(request.form.get('col_saldo', 3))
            }
        
        FileHandler.save_bank_template(template)
        flash('Template criado com sucesso!', 'success')
        
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        flash(f'Erro ao criar template: {str(e)}', 'error')
    
    return redirect(url_for('templates'))

@app.route('/mappings')
def mappings():
    """Manage accounting mappings"""
    try:
        mappings = FileHandler.load_accounting_mappings()
        return render_template('mappings.html', mappings=mappings)
    except Exception as e:
        logger.error(f"Error loading mappings: {str(e)}")
        return render_template('mappings.html', mappings=[])

@app.route('/mappings/create', methods=['POST'])
def create_mapping():
    """Create a new accounting mapping"""
    try:
        mapping = AccountingMapping(
            rotulo_contabil=request.form.get('rotulo_contabil'),
            descricao_longa=request.form.get('descricao_longa'),
            tipo_transacao=request.form.get('tipo_transacao'),
            palavras_chave=[k.strip() for k in request.form.get('palavras_chave', '').split(',') if k.strip()],
            regex_avancado=request.form.get('regex_avancado'),
            conta_debito=request.form.get('conta_debito'),
            conta_credito=request.form.get('conta_credito'),
            historico_contabil_padrao=request.form.get('historico_contabil_padrao'),
            excecoes=[e.strip() for e in request.form.get('excecoes', '').split(',') if e.strip()]
        )
        
        mappings = FileHandler.load_accounting_mappings()
        mappings.append(mapping)
        FileHandler.save_accounting_mappings(mappings)
        
        flash('Mapeamento criado com sucesso!', 'success')
        
    except Exception as e:
        logger.error(f"Error creating mapping: {str(e)}")
        flash(f'Erro ao criar mapeamento: {str(e)}', 'error')
    
    return redirect(url_for('mappings'))

@app.route('/mappings/edit/<mapping_id>', methods=['POST'])
def edit_mapping(mapping_id):
    """Edit an existing accounting mapping"""
    try:
        mappings = FileHandler.load_accounting_mappings()
        mapping = next((m for m in mappings if m.id == mapping_id), None)
        
        if not mapping:
            flash('Mapeamento não encontrado', 'error')
            return redirect(url_for('mappings'))
        
        # Update mapping
        mapping.rotulo_contabil = request.form.get('rotulo_contabil')
        mapping.descricao_longa = request.form.get('descricao_longa')
        mapping.tipo_transacao = request.form.get('tipo_transacao')
        mapping.palavras_chave = [k.strip() for k in request.form.get('palavras_chave', '').split(',') if k.strip()]
        mapping.regex_avancado = request.form.get('regex_avancado')
        mapping.conta_debito = request.form.get('conta_debito')
        mapping.conta_credito = request.form.get('conta_credito')
        mapping.historico_contabil_padrao = request.form.get('historico_contabil_padrao')
        mapping.excecoes = [e.strip() for e in request.form.get('excecoes', '').split(',') if e.strip()]
        
        FileHandler.save_accounting_mappings(mappings)
        flash('Mapeamento atualizado com sucesso!', 'success')
        
    except Exception as e:
        logger.error(f"Error editing mapping: {str(e)}")
        flash(f'Erro ao editar mapeamento: {str(e)}', 'error')
    
    return redirect(url_for('mappings'))

@app.route('/mappings/delete/<mapping_id>', methods=['POST'])
def delete_mapping(mapping_id):
    """Delete an accounting mapping"""
    try:
        mappings = FileHandler.load_accounting_mappings()
        mappings = [m for m in mappings if m.id != mapping_id]
        
        FileHandler.save_accounting_mappings(mappings)
        flash('Mapeamento excluído com sucesso!', 'success')
        
    except Exception as e:
        logger.error(f"Error deleting mapping: {str(e)}")
        flash(f'Erro ao excluir mapeamento: {str(e)}', 'error')
    
    return redirect(url_for('mappings'))

@app.route('/mappings/get/<mapping_id>')
def get_mapping(mapping_id):
    """Get mapping data for editing"""
    try:
        mappings = FileHandler.load_accounting_mappings()
        mapping = next((m for m in mappings if m.id == mapping_id), None)
        
        if not mapping:
            return jsonify({'error': 'Mapeamento não encontrado'}), 404
        
        return jsonify(mapping.to_dict())
        
    except Exception as e:
        logger.error(f"Error getting mapping: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/export')
def export_page():
    """Export page"""
    try:
        transactions = FileHandler.load_transactions()
        layouts = FileHandler.load_export_layouts()
        return render_template('export.html', transactions=transactions, layouts=layouts)
    except Exception as e:
        logger.error(f"Error loading export page: {str(e)}")
        return render_template('export.html', transactions=[], layouts=[])

@app.route('/export/download', methods=['POST'])
def export_download():
    """Download exported file"""
    try:
        export_format = request.form.get('format', 'csv')
        layout_name = request.form.get('layout', 'default')
        date_from = request.form.get('date_from', '')
        date_to = request.form.get('date_to', '')
        
        # Load transactions
        transactions = FileHandler.load_transactions()
        
        # Filter by date if provided
        if date_from:
            transactions = [t for t in transactions if t.data >= date_from]
        if date_to:
            transactions = [t for t in transactions if t.data <= date_to]
        
        # Export file
        exporter = ExportManager()
        file_path = exporter.export_transactions(transactions, export_format, layout_name)
        
        return send_file(file_path, as_attachment=True, 
                        download_name=f'transacoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{export_format}')
        
    except Exception as e:
        logger.error(f"Error exporting file: {str(e)}")
        flash(f'Erro ao exportar arquivo: {str(e)}', 'error')
        return redirect(url_for('export_page'))

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500
