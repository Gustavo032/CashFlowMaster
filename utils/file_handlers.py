import os
import json
import logging
from typing import List, Dict, Any
from models import Transaction, BankTemplate, AccountingMapping, CustomRule

logger = logging.getLogger(__name__)

class FileHandler:
    @staticmethod
    def load_transactions() -> List[Transaction]:
        """Load transactions from JSON file"""
        try:
            filepath = 'data/transacoes.json'
            if not os.path.exists(filepath):
                return []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            transactions = []
            for item in data:
                transaction = Transaction.from_dict(item)
                transactions.append(transaction)
            
            return transactions
        
        except Exception as e:
            logger.error(f"Error loading transactions: {str(e)}")
            return []
    
    @staticmethod
    def save_transactions(transactions: List[Transaction]) -> None:
        """Save transactions to JSON file"""
        try:
            filepath = 'data/transacoes.json'
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            data = [transaction.to_dict() for transaction in transactions]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving transactions: {str(e)}")
            raise
    
    @staticmethod
    def load_bank_templates() -> List[BankTemplate]:
        """Load bank templates from template files"""
        try:
            templates = []
            template_dir = 'data/templates'
            
            if not os.path.exists(template_dir):
                return templates
            
            for filename in os.listdir(template_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(template_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        template = BankTemplate.from_dict(data)
                        templates.append(template)
                    
                    except Exception as e:
                        logger.error(f"Error loading template {filename}: {str(e)}")
                        continue
            
            return templates
        
        except Exception as e:
            logger.error(f"Error loading bank templates: {str(e)}")
            return []
    
    @staticmethod
    def save_bank_template(template: BankTemplate) -> None:
        """Save bank template to file"""
        try:
            template_dir = 'data/templates'
            os.makedirs(template_dir, exist_ok=True)
            
            filename = f"{template.banco.lower().replace(' ', '_')}.json"
            filepath = os.path.join(template_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving bank template: {str(e)}")
            raise
    
    @staticmethod
    def load_accounting_mappings() -> List[AccountingMapping]:
        """Load accounting mappings from JSON file"""
        try:
            filepath = 'data/mapeamentos_contabeis.json'
            if not os.path.exists(filepath):
                return []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            mappings = []
            for item in data:
                mapping = AccountingMapping.from_dict(item)
                mappings.append(mapping)
            
            return mappings
        
        except Exception as e:
            logger.error(f"Error loading accounting mappings: {str(e)}")
            return []
    
    @staticmethod
    def save_accounting_mappings(mappings: List[AccountingMapping]) -> None:
        """Save accounting mappings to JSON file"""
        try:
            filepath = 'data/mapeamentos_contabeis.json'
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            data = [mapping.to_dict() for mapping in mappings]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving accounting mappings: {str(e)}")
            raise
    
    @staticmethod
    def load_custom_rules() -> List[CustomRule]:
        """Load custom rules from JSON file"""
        try:
            filepath = 'data/regras_personalizadas.json'
            if not os.path.exists(filepath):
                return []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            rules = []
            for item in data:
                rule = CustomRule.from_dict(item)
                rules.append(rule)
            
            return rules
        
        except Exception as e:
            logger.error(f"Error loading custom rules: {str(e)}")
            return []
    
    @staticmethod
    def save_custom_rules(rules: List[CustomRule]) -> None:
        """Save custom rules to JSON file"""
        try:
            filepath = 'data/regras_personalizadas.json'
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            data = [rule.to_dict() for rule in rules]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving custom rules: {str(e)}")
            raise
    
    @staticmethod
    def load_mapping_presets() -> List[Dict[str, Any]]:
        """Load mapping presets from JSON file"""
        try:
            filepath = 'data/presets_mapeamentos.json'
            if not os.path.exists(filepath):
                return []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
        
        except Exception as e:
            logger.error(f"Error loading mapping presets: {str(e)}")
            return []
    
    @staticmethod
    def save_mapping_presets(presets: List[Dict[str, Any]]) -> None:
        """Save mapping presets to JSON file"""
        try:
            filepath = 'data/presets_mapeamentos.json'
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(presets, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving mapping presets: {str(e)}")
            raise
    
    @staticmethod
    def load_export_layouts() -> List[Dict[str, Any]]:
        """Load export layouts from JSON file"""
        try:
            filepath = 'data/layouts_exportacao.json'
            if not os.path.exists(filepath):
                return []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
        
        except Exception as e:
            logger.error(f"Error loading export layouts: {str(e)}")
            return []
    
    @staticmethod
    def save_export_layouts(layouts: List[Dict[str, Any]]) -> None:
        """Save export layouts to JSON file"""
        try:
            filepath = 'data/layouts_exportacao.json'
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(layouts, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving export layouts: {str(e)}")
            raise
