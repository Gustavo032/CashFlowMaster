import os
import csv
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from models import Transaction
from utils.file_handlers import FileHandler

logger = logging.getLogger(__name__)

class ExportManager:
    def __init__(self):
        self.export_dir = 'exports'
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_transactions(self, transactions: List[Transaction], format_type: str, layout_name: str = 'default') -> str:
        """Export transactions to specified format"""
        try:
            if format_type == 'csv':
                return self._export_csv(transactions, layout_name)
            elif format_type == 'txt':
                return self._export_txt(transactions, layout_name)
            elif format_type == 'json':
                return self._export_json(transactions, layout_name)
            else:
                raise ValueError(f"Formato de exportação não suportado: {format_type}")
        
        except Exception as e:
            logger.error(f"Error exporting transactions: {str(e)}")
            raise
    
    def _export_csv(self, transactions: List[Transaction], layout_name: str) -> str:
        """Export transactions to CSV format"""
        try:
            layout = self._get_export_layout(layout_name)
            if not layout:
                layout = self._get_default_csv_layout()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transacoes_{timestamp}.csv"
            filepath = os.path.join(self.export_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                # Determine delimiter
                delimiter = layout.get('delimitador', ',')
                writer = csv.writer(csvfile, delimiter=delimiter)
                
                # Write header
                headers = [col['nome_coluna'] for col in layout['colunas']]
                writer.writerow(headers)
                
                # Write data
                for transaction in transactions:
                    row = []
                    for col in layout['colunas']:
                        value = self._get_field_value(transaction, col)
                        row.append(value)
                    writer.writerow(row)
            
            return filepath
        
        except Exception as e:
            logger.error(f"Error exporting CSV: {str(e)}")
            raise
    
    def _export_txt(self, transactions: List[Transaction], layout_name: str) -> str:
        """Export transactions to TXT format"""
        try:
            layout = self._get_export_layout(layout_name)
            if not layout:
                layout = self._get_default_txt_layout()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transacoes_{timestamp}.txt"
            filepath = os.path.join(self.export_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as txtfile:
                delimiter = layout.get('delimitador', '|')
                
                for transaction in transactions:
                    row_data = []
                    for col in layout['colunas']:
                        value = self._get_field_value(transaction, col)
                        # Apply fixed width formatting if specified
                        if col.get('tamanho_fixo'):
                            value = self._format_fixed_width(value, col)
                        row_data.append(str(value))
                    
                    line = delimiter.join(row_data)
                    txtfile.write(line + '\n')
            
            return filepath
        
        except Exception as e:
            logger.error(f"Error exporting TXT: {str(e)}")
            raise
    
    def _export_json(self, transactions: List[Transaction], layout_name: str) -> str:
        """Export transactions to JSON format"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transacoes_{timestamp}.json"
            filepath = os.path.join(self.export_dir, filename)
            
            # Convert transactions to dict format
            data = [transaction.to_dict() for transaction in transactions]
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=2)
            
            return filepath
        
        except Exception as e:
            logger.error(f"Error exporting JSON: {str(e)}")
            raise
    
    def _get_export_layout(self, layout_name: str) -> Dict[str, Any]:
        """Get export layout by name"""
        try:
            layouts = FileHandler.load_export_layouts()
            for layout in layouts:
                if layout.get('nome') == layout_name:
                    return layout
            return None
        
        except Exception as e:
            logger.error(f"Error getting export layout: {str(e)}")
            return None
    
    def _get_default_csv_layout(self) -> Dict[str, Any]:
        """Get default CSV layout"""
        return {
            'nome': 'CSV Padrão',
            'formato': 'csv',
            'delimitador': ',',
            'colunas': [
                {'campo': 'data', 'nome_coluna': 'Data', 'tipo': 'data'},
                {'campo': 'descricao_original', 'nome_coluna': 'Descrição', 'tipo': 'texto'},
                {'campo': 'valor', 'nome_coluna': 'Valor', 'tipo': 'numero'},
                {'campo': 'tipo_movimentacao', 'nome_coluna': 'Tipo', 'tipo': 'texto'},
                {'campo': 'banco', 'nome_coluna': 'Banco', 'tipo': 'texto'},
                {'campo': 'rotulo_contabil', 'nome_coluna': 'Categoria', 'tipo': 'texto'},
                {'campo': 'conta_debito', 'nome_coluna': 'Conta Débito', 'tipo': 'texto'},
                {'campo': 'conta_credito', 'nome_coluna': 'Conta Crédito', 'tipo': 'texto'},
                {'campo': 'historico_contabil', 'nome_coluna': 'Histórico', 'tipo': 'texto'}
            ]
        }
    
    def _get_default_txt_layout(self) -> Dict[str, Any]:
        """Get default TXT layout"""
        return {
            'nome': 'TXT Padrão',
            'formato': 'txt',
            'delimitador': '|',
            'colunas': [
                {'campo': 'data', 'nome_coluna': 'DTLANC', 'tipo': 'data', 'formato': '%Y%m%d'},
                {'campo': 'conta_debito', 'nome_coluna': 'CTADEB', 'tipo': 'texto', 'tamanho_fixo': 15},
                {'campo': 'conta_credito', 'nome_coluna': 'CTACRED', 'tipo': 'texto', 'tamanho_fixo': 15},
                {'campo': 'valor', 'nome_coluna': 'VRLANC', 'tipo': 'numero', 'formato': '%.2f'},
                {'campo': 'historico_contabil', 'nome_coluna': 'HISTLANC', 'tipo': 'texto', 'tamanho_fixo': 50}
            ]
        }
    
    def _get_field_value(self, transaction: Transaction, column_config: Dict[str, Any]) -> str:
        """Get field value based on column configuration"""
        try:
            field_name = column_config['campo']
            field_type = column_config.get('tipo', 'texto')
            
            # Get raw value
            raw_value = getattr(transaction, field_name, '')
            
            # Format based on type
            if field_type == 'data':
                if isinstance(raw_value, str) and raw_value:
                    try:
                        date_obj = datetime.strptime(raw_value, '%Y-%m-%d')
                        format_str = column_config.get('formato', '%d/%m/%Y')
                        return date_obj.strftime(format_str)
                    except ValueError:
                        return raw_value
                return raw_value
            
            elif field_type == 'numero':
                if isinstance(raw_value, (int, float)):
                    format_str = column_config.get('formato', '%.2f')
                    formatted = format_str % raw_value
                    
                    # Handle decimal separator
                    separator = column_config.get('separador_decimal', '.')
                    if separator != '.':
                        formatted = formatted.replace('.', separator)
                    
                    return formatted
                return str(raw_value)
            
            else:  # texto
                return str(raw_value)
        
        except Exception as e:
            logger.error(f"Error getting field value: {str(e)}")
            return ''
    
    def _format_fixed_width(self, value: str, column_config: Dict[str, Any]) -> str:
        """Format value with fixed width"""
        try:
            width = column_config.get('tamanho_fixo', 0)
            padding = column_config.get('preenchimento', 'spaces')
            
            if width <= 0:
                return value
            
            # Truncate if too long
            if len(value) > width:
                value = value[:width]
            
            # Pad if too short
            if len(value) < width:
                if padding == 'zeros':
                    value = value.zfill(width)
                else:  # spaces
                    value = value.ljust(width)
            
            return value
        
        except Exception as e:
            logger.error(f"Error formatting fixed width: {str(e)}")
            return value
