import re
import logging
from typing import List, Optional, Tuple
from models import Transaction, AccountingMapping, CustomRule
from utils.file_handlers import FileHandler

logger = logging.getLogger(__name__)

class TransactionMapper:
    def __init__(self):
        self.scoring_weights = {
            'custom_rule': 10,
            'regex_advanced': 3,
            'sub_mapping_keywords': 2,
            'main_mapping_keywords': 1
        }
    
    def map_transaction(self, transaction: Transaction) -> Transaction:
        """Map a transaction to accounting accounts"""
        try:
            # Priority 1: Custom Rules
            custom_mapping = self._check_custom_rules(transaction)
            if custom_mapping:
                return self._apply_custom_mapping(transaction, custom_mapping)
            
            # Priority 2-4: Standard Mappings
            standard_mapping = self._check_standard_mappings(transaction)
            if standard_mapping:
                return self._apply_standard_mapping(transaction, standard_mapping)
            
            # No mapping found
            logger.info(f"No mapping found for transaction: {transaction.descricao_original}")
            return transaction
        
        except Exception as e:
            logger.error(f"Error mapping transaction: {str(e)}")
            return transaction
    
    def _check_custom_rules(self, transaction: Transaction) -> Optional[CustomRule]:
        """Check if transaction matches any custom rules"""
        try:
            custom_rules = FileHandler.load_custom_rules()
            
            for rule in custom_rules:
                if self.matches_custom_rule(transaction, rule):
                    return rule
            
            return None
        
        except Exception as e:
            logger.error(f"Error checking custom rules: {str(e)}")
            return None
    
    def matches_custom_rule(self, transaction: Transaction, rule: CustomRule) -> bool:
        """Check if transaction matches a custom rule"""
        try:
            # Check transaction type
            if rule.tipo_movimentacao_regra != 'ambos':
                if rule.tipo_movimentacao_regra == 'entrada' and transaction.tipo_movimentacao != 'Crédito':
                    return False
                if rule.tipo_movimentacao_regra == 'saida' and transaction.tipo_movimentacao != 'Débito':
                    return False
            
            # Check description match
            if rule.corresponde_exatamente:
                if transaction.descricao_normalizada != rule.termo_chave.lower():
                    return False
            else:
                if rule.termo_chave.lower() not in transaction.descricao_normalizada:
                    return False
            
            # Check value match if required
            if rule.considerar_valor:
                if rule.valor_exato is not None:
                    if abs(transaction.valor - rule.valor_exato) > 0.01:
                        return False
                elif rule.valor_min is not None and rule.valor_max is not None:
                    if not (rule.valor_min <= transaction.valor <= rule.valor_max):
                        return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking custom rule match: {str(e)}")
            return False
    
    def _check_standard_mappings(self, transaction: Transaction) -> Optional[Tuple[AccountingMapping, dict, int]]:
        """Check standard mappings and return best match with score"""
        try:
            mappings = FileHandler.load_accounting_mappings()
            best_match = None
            best_score = 0
            
            for mapping in mappings:
                # Check if transaction type is compatible
                if mapping.tipo_transacao == 'entrada' and transaction.tipo_movimentacao != 'Crédito':
                    continue
                if mapping.tipo_transacao == 'saida' and transaction.tipo_movimentacao != 'Débito':
                    continue
                
                # Check exceptions
                if self._has_exceptions(transaction, mapping):
                    continue
                
                # Check regex advanced
                regex_match = self._check_regex_advanced(transaction, mapping)
                if regex_match:
                    score = self.scoring_weights['regex_advanced']
                    if score > best_score:
                        best_match = (mapping, {'type': 'regex', 'data': regex_match}, score)
                        best_score = score
                    continue
                
                # Check sub-mappings
                sub_mapping_match = self._check_sub_mappings(transaction, mapping)
                if sub_mapping_match:
                    score = self.scoring_weights['sub_mapping_keywords']
                    if score > best_score:
                        best_match = (mapping, {'type': 'sub_mapping', 'data': sub_mapping_match}, score)
                        best_score = score
                    continue
                
                # Check main mapping keywords
                main_mapping_match = self._check_main_keywords(transaction, mapping)
                if main_mapping_match:
                    score = self.scoring_weights['main_mapping_keywords']
                    if score > best_score:
                        best_match = (mapping, {'type': 'main_mapping', 'data': main_mapping_match}, score)
                        best_score = score
            
            return best_match
        
        except Exception as e:
            logger.error(f"Error checking standard mappings: {str(e)}")
            return None
    
    def _has_exceptions(self, transaction: Transaction, mapping: AccountingMapping) -> bool:
        """Check if transaction has exceptions that exclude this mapping"""
        try:
            for exception in mapping.excecoes:
                if exception.lower() in transaction.descricao_normalizada:
                    return True
            return False
        
        except Exception as e:
            logger.error(f"Error checking exceptions: {str(e)}")
            return False
    
    def _check_regex_advanced(self, transaction: Transaction, mapping: AccountingMapping) -> Optional[str]:
        """Check regex advanced pattern"""
        try:
            if not mapping.regex_avancado:
                return None
            
            pattern = re.compile(mapping.regex_avancado, re.IGNORECASE)
            match = pattern.search(transaction.descricao_normalizada)
            
            return match.group(0) if match else None
        
        except Exception as e:
            logger.error(f"Error checking regex advanced: {str(e)}")
            return None
    
    def _check_sub_mappings(self, transaction: Transaction, mapping: AccountingMapping) -> Optional[dict]:
        """Check sub-mappings keywords"""
        try:
            for sub_mapping in mapping.sub_mapeamentos:
                for keyword in sub_mapping.get('palavras_chave', []):
                    if keyword.lower() in transaction.descricao_normalizada:
                        return sub_mapping
            return None
        
        except Exception as e:
            logger.error(f"Error checking sub-mappings: {str(e)}")
            return None
    
    def _check_main_keywords(self, transaction: Transaction, mapping: AccountingMapping) -> Optional[bool]:
        """Check main mapping keywords"""
        try:
            for keyword in mapping.palavras_chave:
                if keyword.lower() in transaction.descricao_normalizada:
                    return True
            return None
        
        except Exception as e:
            logger.error(f"Error checking main keywords: {str(e)}")
            return None
    
    def _apply_custom_mapping(self, transaction: Transaction, rule: CustomRule) -> Transaction:
        """Apply custom rule mapping to transaction"""
        try:
            transaction.rotulo_contabil = rule.rotulo_contabil_aplicar
            transaction.conta_debito = rule.conta_debito_aplicar
            transaction.conta_credito = rule.conta_credito_aplicar
            transaction.historico_contabil = rule.historico_contabil_aplicar
            
            return transaction
        
        except Exception as e:
            logger.error(f"Error applying custom mapping: {str(e)}")
            return transaction
    
    def _apply_standard_mapping(self, transaction: Transaction, mapping_data: Tuple[AccountingMapping, dict, int]) -> Transaction:
        """Apply standard mapping to transaction"""
        try:
            mapping, match_data, score = mapping_data
            
            if match_data['type'] == 'sub_mapping':
                # Use sub-mapping data
                sub_mapping = match_data['data']
                transaction.rotulo_contabil = sub_mapping.get('rotulo_contabil', mapping.rotulo_contabil)
                transaction.conta_debito = sub_mapping.get('conta_debito', mapping.conta_debito)
                transaction.conta_credito = sub_mapping.get('conta_credito', mapping.conta_credito)
                transaction.historico_contabil = sub_mapping.get('historico_contabil_padrao', mapping.historico_contabil_padrao)
            else:
                # Use main mapping data
                transaction.rotulo_contabil = mapping.rotulo_contabil
                transaction.conta_debito = mapping.conta_debito
                transaction.conta_credito = mapping.conta_credito
                transaction.historico_contabil = mapping.historico_contabil_padrao
            
            return transaction
        
        except Exception as e:
            logger.error(f"Error applying standard mapping: {str(e)}")
            return transaction
