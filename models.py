import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

class Transaction:
    def __init__(self, data: str, descricao_original: str, valor: float, 
                 tipo_movimentacao: str, banco: str, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.data = data
        self.descricao_original = descricao_original
        self.descricao_normalizada = self._normalize_description(descricao_original)
        self.valor = valor
        self.tipo_movimentacao = tipo_movimentacao
        self.banco = banco
        self.rotulo_contabil = kwargs.get('rotulo_contabil', '')
        self.conta_debito = kwargs.get('conta_debito', '')
        self.conta_credito = kwargs.get('conta_credito', '')
        self.historico_contabil = kwargs.get('historico_contabil', descricao_original)
        self.revisado_manualmente = kwargs.get('revisado_manualmente', False)
    
    def _normalize_description(self, description: str) -> str:
        """Normalize description for comparison"""
        import re
        import unicodedata
        
        # Clean description first
        cleaned = self._clean_description(description)
        
        # Remove accents
        normalized = unicodedata.normalize('NFD', cleaned)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        
        # Convert to lowercase and remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized.lower().strip())
        
        # Remove special characters except spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized
    
    def _clean_description(self, description: str) -> str:
        """Clean description by removing date prefix and value suffix"""
        import re
        
        cleaned = description.strip()
        
        # Remove date prefix (e.g., "20/01/2025 PIX TRANSF..." -> "PIX TRANSF...")
        date_pattern = r'^\d{2}/\d{2}/\d{4}\s+'
        cleaned = re.sub(date_pattern, '', cleaned)
        
        # Remove value suffix (e.g., "PIX TRANSF GUSTAVO18/01 -1.300,00" -> "PIX TRANSF GUSTAVO18/01")
        # Look for patterns like " -1.300,00", " 1.300,00", " R$ 1.300,00"
        value_pattern = r'\s+(?:R\$\s*)?-?\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?(?:\s+R\$)?$'
        cleaned = re.sub(value_pattern, '', cleaned)
        
        return cleaned.strip()
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'data': self.data,
            'descricao_original': self.descricao_original,
            'descricao_normalizada': self.descricao_normalizada,
            'valor': self.valor,
            'tipo_movimentacao': self.tipo_movimentacao,
            'banco': self.banco,
            'rotulo_contabil': self.rotulo_contabil,
            'conta_debito': self.conta_debito,
            'conta_credito': self.conta_credito,
            'historico_contabil': self.historico_contabil,
            'revisado_manualmente': self.revisado_manualmente
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

class BankTemplate:
    def __init__(self, banco: str, formato: str, **kwargs):
        self.banco = banco
        self.formato = formato
        self.regex_data = kwargs.get('regex_data', r'\d{2}/\d{2}/\d{4}')
        self.regex_valor = kwargs.get('regex_valor', r'-?\d{1,3}(?:\.?\d{3})*,\d{2}')
        self.regex_descricao = kwargs.get('regex_descricao', r'.+')
        self.modo_leitura = kwargs.get('modo_leitura', 'texto')
        self.colunas_csv = kwargs.get('colunas_csv', {})
        self.linhas_ignoradas_topo = kwargs.get('linhas_ignoradas_topo', 0)
        self.linhas_ignoradas_rodape = kwargs.get('linhas_ignoradas_rodape', 0)
    
    def to_dict(self) -> Dict:
        return {
            'banco': self.banco,
            'formato': self.formato,
            'regex_data': self.regex_data,
            'regex_valor': self.regex_valor,
            'regex_descricao': self.regex_descricao,
            'modo_leitura': self.modo_leitura,
            'colunas_csv': self.colunas_csv,
            'linhas_ignoradas_topo': self.linhas_ignoradas_topo,
            'linhas_ignoradas_rodape': self.linhas_ignoradas_rodape
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

class AccountingMapping:
    def __init__(self, rotulo_contabil: str, tipo_transacao: str, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.rotulo_contabil = rotulo_contabil
        self.descricao_longa = kwargs.get('descricao_longa', '')
        self.tipo_transacao = tipo_transacao
        self.palavras_chave = kwargs.get('palavras_chave', [])
        self.regex_avancado = kwargs.get('regex_avancado', '')
        self.conta_debito = kwargs.get('conta_debito', '')
        self.conta_credito = kwargs.get('conta_credito', '')
        self.historico_contabil_padrao = kwargs.get('historico_contabil_padrao', '')
        self.excecoes = kwargs.get('excecoes', [])
        self.sub_mapeamentos = kwargs.get('sub_mapeamentos', [])
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'rotulo_contabil': self.rotulo_contabil,
            'descricao_longa': self.descricao_longa,
            'tipo_transacao': self.tipo_transacao,
            'palavras_chave': self.palavras_chave,
            'regex_avancado': self.regex_avancado,
            'conta_debito': self.conta_debito,
            'conta_credito': self.conta_credito,
            'historico_contabil_padrao': self.historico_contabil_padrao,
            'excecoes': self.excecoes,
            'sub_mapeamentos': self.sub_mapeamentos
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

class CustomRule:
    def __init__(self, termo_chave: str, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.termo_chave = termo_chave
        self.corresponde_exatamente = kwargs.get('corresponde_exatamente', False)
        self.considerar_valor = kwargs.get('considerar_valor', False)
        self.valor_exato = kwargs.get('valor_exato', None)
        self.valor_min = kwargs.get('valor_min', None)
        self.valor_max = kwargs.get('valor_max', None)
        self.tipo_movimentacao_regra = kwargs.get('tipo_movimentacao_regra', 'ambos')
        self.rotulo_contabil_aplicar = kwargs.get('rotulo_contabil_aplicar', '')
        self.conta_debito_aplicar = kwargs.get('conta_debito_aplicar', '')
        self.conta_credito_aplicar = kwargs.get('conta_credito_aplicar', '')
        self.historico_contabil_aplicar = kwargs.get('historico_contabil_aplicar', '')
        self.data_criacao = kwargs.get('data_criacao', datetime.now().strftime('%Y-%m-%d'))
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'termo_chave': self.termo_chave,
            'corresponde_exatamente': self.corresponde_exatamente,
            'considerar_valor': self.considerar_valor,
            'valor_exato': self.valor_exato,
            'valor_min': self.valor_min,
            'valor_max': self.valor_max,
            'tipo_movimentacao_regra': self.tipo_movimentacao_regra,
            'rotulo_contabil_aplicar': self.rotulo_contabil_aplicar,
            'conta_debito_aplicar': self.conta_debito_aplicar,
            'conta_credito_aplicar': self.conta_credito_aplicar,
            'historico_contabil_aplicar': self.historico_contabil_aplicar,
            'data_criacao': self.data_criacao
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)
