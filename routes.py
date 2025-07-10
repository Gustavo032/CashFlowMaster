import os
import json
import logging
import uuid
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
            filtered_transactions = [t for t in filtered_transactions if t.rotulo_contabil and t.rotulo_contabil != 'IGNORAR']
        elif mapping_filter == 'unmapped':
            filtered_transactions = [t for t in filtered_transactions if not t.rotulo_contabil or t.rotulo_contabil == '']
        elif mapping_filter == 'ignored':
            filtered_transactions = [t for t in filtered_transactions if t.rotulo_contabil == 'IGNORAR']
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

@app.route('/transactions/refresh_descriptions', methods=['POST'])
def refresh_descriptions():
    """Refresh normalized descriptions for all transactions"""
    try:
        transactions = FileHandler.load_transactions()
        mapper = TransactionMapper()
        
        for transaction in transactions:
            # Recreate normalized description with fixed cleaning
            transaction.descricao_normalizada = transaction._normalize_description(transaction.descricao_original)
            
            # Only remap if not manually reviewed
            if not transaction.revisado_manualmente:
                mapped_transaction = mapper.map_transaction(transaction)
                transaction.rotulo_contabil = mapped_transaction.rotulo_contabil
                transaction.conta_debito = mapped_transaction.conta_debito
                transaction.conta_credito = mapped_transaction.conta_credito
                transaction.historico_contabil = mapped_transaction.historico_contabil
        
        FileHandler.save_transactions(transactions)
        flash('Descrições atualizadas e transações remapeadas com sucesso!', 'success')
        
    except Exception as e:
        logger.error(f"Error refreshing descriptions: {str(e)}")
        flash(f'Erro ao atualizar descrições: {str(e)}', 'error')
    
    return redirect(url_for('transactions'))

@app.route('/transactions/remap_selected', methods=['POST'])
def remap_selected_transactions():
    """Remap selected transactions"""
    try:
        # Check if request is JSON (AJAX)
        if request.is_json:
            transaction_ids = request.json.get('transaction_ids', [])
        else:
            transaction_ids = request.form.getlist('transaction_ids')
        
        if not transaction_ids:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Nenhuma transação selecionada'}), 400
            flash('Nenhuma transação selecionada.', 'warning')
            return redirect(url_for('transactions'))

        transactions = FileHandler.load_transactions()
        mapper = TransactionMapper()
        updated_count = 0

        for transaction in transactions:
            if transaction.id in transaction_ids and not transaction.revisado_manualmente:
                mapped_transaction = mapper.map_transaction(transaction)
                transaction.rotulo_contabil = mapped_transaction.rotulo_contabil
                transaction.conta_debito = mapped_transaction.conta_debito
                transaction.conta_credito = mapped_transaction.conta_credito
                transaction.historico_contabil = mapped_transaction.historico_contabil
                updated_count += 1

        FileHandler.save_transactions(transactions)
        
        if request.is_json:
            return jsonify({'success': True, 'message': f'{updated_count} transações remapeadas com sucesso!'})
        
        flash(f'{updated_count} transações remapeadas com sucesso!', 'success')

    except Exception as e:
        logger.error(f"Error remapping selected transactions: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Erro ao remapear transações selecionadas: {str(e)}', 'error')

    return redirect(url_for('transactions'))

@app.route('/transactions/delete_selected', methods=['POST'])
def delete_selected_transactions():
    """Delete selected transactions"""
    try:
        # Check if request is JSON (AJAX)
        if request.is_json:
            transaction_ids = request.json.get('transaction_ids', [])
        else:
            transaction_ids = request.form.getlist('transaction_ids')
        
        if not transaction_ids:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Nenhuma transação selecionada'}), 400
            flash('Nenhuma transação selecionada.', 'warning')
            return redirect(url_for('transactions'))

        transactions = FileHandler.load_transactions()
        original_count = len(transactions)

        # Filter out selected transactions
        transactions = [t for t in transactions if t.id not in transaction_ids]
        deleted_count = original_count - len(transactions)

        FileHandler.save_transactions(transactions)
        
        if request.is_json:
            return jsonify({'success': True, 'message': f'{deleted_count} transações excluídas com sucesso!'})
        
        flash(f'{deleted_count} transações excluídas com sucesso!', 'success')

    except Exception as e:
        logger.error(f"Error deleting selected transactions: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Erro ao excluir transações selecionadas: {str(e)}', 'error')

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

@app.route('/templates/edit/<template_id>', methods=['POST'])
def edit_template(template_id):
    """Edit an existing bank template"""
    try:
        # Load existing template
        templates = FileHandler.load_bank_templates()
        template = next((t for t in templates if t.banco.lower().replace(' ', '_') == template_id), None)

        if not template:
            flash('Template não encontrado', 'error')
            return redirect(url_for('templates'))

        # Delete old template file
        FileHandler.delete_bank_template(template_id)

        # Update template with new values
        template.banco = request.form.get('banco')
        template.formato = request.form.get('formato')
        template.regex_data = request.form.get('regex_data')
        template.regex_valor = request.form.get('regex_valor')
        template.regex_descricao = request.form.get('regex_descricao')
        template.modo_leitura = request.form.get('modo_leitura')
        template.linhas_ignoradas_topo = int(request.form.get('linhas_ignoradas_topo', 0))
        template.linhas_ignoradas_rodape = int(request.form.get('linhas_ignoradas_rodape', 0))

        # Handle CSV columns if applicable
        if template.formato == 'csv':
            template.colunas_csv = {
                'data': int(request.form.get('col_data', 0)),
                'descricao': int(request.form.get('col_descricao', 1)),
                'valor': int(request.form.get('col_valor', 2)),
                'saldo': int(request.form.get('col_saldo', 3))
            }

        # Save updated template
        FileHandler.save_bank_template(template)
        flash('Template atualizado com sucesso!', 'success')

    except Exception as e:
        logger.error(f"Error editing template: {str(e)}")
        flash(f'Erro ao editar template: {str(e)}', 'error')

    return redirect(url_for('templates'))

@app.route('/templates/delete/<template_id>', methods=['POST'])
def delete_template(template_id):
    """Delete a bank template"""
    try:
        FileHandler.delete_bank_template(template_id)
        flash('Template excluído com sucesso!', 'success')

    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        flash(f'Erro ao excluir template: {str(e)}', 'error')

    return redirect(url_for('templates'))

@app.route('/templates/get/<template_id>')
def get_template(template_id):
    """Get template data for editing"""
    try:
        templates = FileHandler.load_bank_templates()
        template = next((t for t in templates if t.banco.lower().replace(' ', '_') == template_id), None)

        if not template:
            return jsonify({'error': 'Template não encontrado'}), 404

        return jsonify(template.to_dict())

    except Exception as e:
        logger.error(f"Error getting template: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@app.route('/mappings/presets/save', methods=['POST'])
def save_mapping_preset():
    """Save current mappings as a preset"""
    try:
        preset_name = request.json.get('name')
        if not preset_name:
            return jsonify({'error': 'Nome do preset é obrigatório'}), 400

        # Load current mappings
        current_mappings = FileHandler.load_accounting_mappings()

        # Load existing presets
        presets = FileHandler.load_mapping_presets()

        # Create new preset
        new_preset = {
            'id': str(uuid.uuid4()),
            'name': preset_name,
            'description': request.json.get('description', ''),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mappings': [mapping.to_dict() for mapping in current_mappings]
        }

        # Add to presets list
        presets.append(new_preset)

        # Save presets
        FileHandler.save_mapping_presets(presets)

        return jsonify({'success': True, 'message': f'Preset "{preset_name}" salvo com sucesso!'})

    except Exception as e:
        logger.error(f"Error saving preset: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/mappings/presets/load/<preset_id>', methods=['POST'])
def load_mapping_preset(preset_id):
    """Load a preset and replace current mappings"""
    try:
        # Load presets
        presets = FileHandler.load_mapping_presets()
        preset = next((p for p in presets if p['id'] == preset_id), None)

        if not preset:
            return jsonify({'error': 'Preset não encontrado'}), 404

        # Convert preset mappings back to AccountingMapping objects
        new_mappings = []
        for mapping_data in preset['mappings']:
            mapping = AccountingMapping.from_dict(mapping_data)
            new_mappings.append(mapping)

        # Save as current mappings
        FileHandler.save_accounting_mappings(new_mappings)

        return jsonify({'success': True, 'message': f'Preset "{preset["name"]}" carregado com sucesso!'})

    except Exception as e:
        logger.error(f"Error loading preset: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/mappings/presets/list')
def list_mapping_presets():
    """List available presets"""
    try:
        presets = FileHandler.load_mapping_presets()

        # Return only essential info for listing
        preset_list = []
        for preset in presets:
            # Handle both old and new preset formats
            preset_id = preset.get('id', preset.get('nome_preset', ''))
            preset_name = preset.get('name', preset.get('nome_preset', 'Preset sem nome'))
            preset_description = preset.get('description', '')
            preset_created_at = preset.get('created_at', '')
            preset_mappings = preset.get('mappings', [])

            preset_list.append({
                'id': preset_id,
                'name': preset_name,
                'description': preset_description,
                'created_at': preset_created_at,
                'mappings_count': len(preset_mappings)
            })

        return jsonify(preset_list)

    except Exception as e:
        logger.error(f"Error listing presets: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/mappings/presets/delete/<preset_id>', methods=['POST'])
def delete_mapping_preset(preset_id):
    """Delete a preset"""
    try:
        presets = FileHandler.load_mapping_presets()

        # Find and remove preset
        preset_to_delete = next((p for p in presets if p['id'] == preset_id), None)
        if not preset_to_delete:
            return jsonify({'error': 'Preset não encontrado'}), 404

        presets = [p for p in presets if p['id'] != preset_id]

        # Save updated presets
        FileHandler.save_mapping_presets(presets)

        return jsonify({'success': True, 'message': f'Preset "{preset_to_delete["name"]}" excluído com sucesso!'})

    except Exception as e:
        logger.error(f"Error deleting preset: {str(e)}")
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