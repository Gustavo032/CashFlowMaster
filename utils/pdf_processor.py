import os
import re
import logging
import pandas as pd
from datetime import datetime
from typing import List, Optional
from models import Transaction, BankTemplate
from utils.file_handlers import FileHandler

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.supported_formats = ['pdf', 'csv', 'ofx']
    
    def process_file(self, filepath: str, bank_template: str = 'auto') -> List[Transaction]:
        """Process a file based on its format"""
        try:
            file_extension = os.path.splitext(filepath)[1].lower()
            
            if file_extension == '.pdf':
                return self._process_pdf(filepath, bank_template)
            elif file_extension == '.csv':
                return self._process_csv(filepath, bank_template)
            elif file_extension == '.ofx':
                return self._process_ofx(filepath)
            else:
                raise ValueError(f"Formato de arquivo não suportado: {file_extension}")
                
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {str(e)}")
            raise
    
    def _process_pdf(self, filepath: str, bank_template: str) -> List[Transaction]:
        """Process PDF file with multiple fallback methods"""
        transactions = []
        
        # Get bank template
        template = self._get_bank_template(bank_template, filepath)
        if not template:
            logger.warning(f"No template found for bank: {bank_template}")
            template = self._get_default_template()
        
        # Priority 1: Direct text extraction
        try:
            transactions = self._extract_text_from_pdf(filepath, template)
            if transactions:
                logger.info(f"Successfully extracted {len(transactions)} transactions using direct text extraction")
                return transactions
        except Exception as e:
            logger.warning(f"Direct text extraction failed: {str(e)}")
        
        # Priority 2: OCR
        try:
            transactions = self._extract_text_with_ocr(filepath, template)
            if transactions:
                logger.info(f"Successfully extracted {len(transactions)} transactions using OCR")
                return transactions
        except Exception as e:
            logger.warning(f"OCR extraction failed: {str(e)}")
        
        # Priority 3: Heuristic CSV conversion
        try:
            transactions = self._convert_pdf_to_csv_heuristic(filepath, template)
            if transactions:
                logger.info(f"Successfully extracted {len(transactions)} transactions using heuristic CSV conversion")
                return transactions
        except Exception as e:
            logger.warning(f"Heuristic CSV conversion failed: {str(e)}")
        
        # All methods failed
        logger.error(f"All extraction methods failed for file: {filepath}")
        raise Exception("Não foi possível extrair dados do arquivo PDF")
    
    def _extract_text_from_pdf(self, filepath: str, template: BankTemplate) -> List[Transaction]:
        """Extract text directly from PDF using pdfplumber"""
        try:
            import pdfplumber
            
            transactions = []
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        page_transactions = self._parse_text_with_template(text, template)
                        transactions.extend(page_transactions)
            
            return transactions
        
        except ImportError:
            logger.warning("pdfplumber not available, trying PyMuPDF")
            return self._extract_text_with_pymupdf(filepath, template)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def _extract_text_with_pymupdf(self, filepath: str, template: BankTemplate) -> List[Transaction]:
        """Extract text using PyMuPDF as fallback"""
        try:
            import fitz  # PyMuPDF
            
            transactions = []
            doc = fitz.open(filepath)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text:
                    page_transactions = self._parse_text_with_template(text, template)
                    transactions.extend(page_transactions)
            
            doc.close()
            return transactions
        
        except ImportError:
            logger.error("PyMuPDF not available")
            raise Exception("Bibliotecas de processamento PDF não disponíveis")
        except Exception as e:
            logger.error(f"Error extracting text with PyMuPDF: {str(e)}")
            raise
    
    def _extract_text_with_ocr(self, filepath: str, template: BankTemplate) -> List[Transaction]:
        """Extract text using OCR with pytesseract"""
        try:
            import pytesseract
            from PIL import Image
            import fitz  # PyMuPDF for PDF to image conversion
            
            transactions = []
            
            # Convert PDF to images
            doc = fitz.open(filepath)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img_data = pix.tobytes("ppm")
                
                # Convert to PIL Image
                img = Image.open(io.BytesIO(img_data))
                
                # Apply OCR
                text = pytesseract.image_to_string(img, lang='por')
                if text:
                    page_transactions = self._parse_text_with_template(text, template)
                    transactions.extend(page_transactions)
            
            doc.close()
            return transactions
        
        except ImportError:
            logger.error("pytesseract or PIL not available")
            raise Exception("Bibliotecas de OCR não disponíveis")
        except Exception as e:
            logger.error(f"Error extracting text with OCR: {str(e)}")
            raise
    
    def _convert_pdf_to_csv_heuristic(self, filepath: str, template: BankTemplate) -> List[Transaction]:
        """Convert PDF to CSV using heuristic table detection"""
        try:
            import pdfplumber
            
            transactions = []
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            table_transactions = self._parse_table_with_template(table, template)
                            transactions.extend(table_transactions)
            
            return transactions
        
        except ImportError:
            logger.error("pdfplumber not available for table extraction")
            raise Exception("Biblioteca de extração de tabelas não disponível")
        except Exception as e:
            logger.error(f"Error converting PDF to CSV heuristic: {str(e)}")
            raise
    
    def _parse_text_with_template(self, text: str, template: BankTemplate) -> List[Transaction]:
        """Parse text using template regex patterns"""
        transactions = []
        
        try:
            lines = text.split('\n')
            
            # Skip header and footer lines
            start_line = template.linhas_ignoradas_topo
            end_line = len(lines) - template.linhas_ignoradas_rodape
            lines = lines[start_line:end_line]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Extract data, valor, and description using regex
                date_match = re.search(template.regex_data, line)
                value_match = re.search(template.regex_valor, line)
                
                if date_match and value_match:
                    # Extract description by removing date and value from line
                    description = line
                    description = re.sub(template.regex_data, '', description)
                    description = re.sub(template.regex_valor, '', description)
                    description = re.sub(template.regex_descricao, '', description)
                    description = description.strip()
                    
                    if not description:
                        # If no description after cleaning, use the regex to capture it
                        desc_match = re.search(template.regex_descricao, line)
                        if desc_match:
                            description = desc_match.group(0).strip()
                    
                    # Parse date
                    date_str = date_match.group(0)
                    try:
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"Could not parse date: {date_str}")
                        continue
                    
                    # Parse value
                    value_str = value_match.group(0)
                    try:
                        # Convert Brazilian format to float
                        value_str = value_str.replace('.', '').replace(',', '.')
                        value = float(value_str)
                    except ValueError:
                        logger.warning(f"Could not parse value: {value_str}")
                        continue
                    
                    # Determine transaction type
                    tipo_movimentacao = "Débito" if value < 0 else "Crédito"
                    
                    # Create transaction
                    transaction = Transaction(
                        data=formatted_date,
                        descricao_original=description,
                        valor=value,
                        tipo_movimentacao=tipo_movimentacao,
                        banco=template.banco
                    )
                    transactions.append(transaction)
        
        except Exception as e:
            logger.error(f"Error parsing text with template: {str(e)}")
            raise
        
        return transactions
    
    def _parse_table_with_template(self, table: List[List[str]], template: BankTemplate) -> List[Transaction]:
        """Parse table data using template column mapping"""
        transactions = []
        
        try:
            if not template.colunas_csv:
                logger.warning("No CSV column mapping in template")
                return transactions
            
            # Skip header rows
            start_row = template.linhas_ignoradas_topo
            end_row = len(table) - template.linhas_ignoradas_rodape
            table = table[start_row:end_row]
            
            for row in table:
                if not row or len(row) < max(template.colunas_csv.values()) + 1:
                    continue
                
                try:
                    # Extract data based on column mapping
                    date_str = row[template.colunas_csv.get('data', 0)]
                    description = row[template.colunas_csv.get('descricao', 1)]
                    value_str = row[template.colunas_csv.get('valor', 2)]
                    
                    # Parse date
                    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    
                    # Parse value
                    value_str = value_str.replace('.', '').replace(',', '.')
                    value = float(value_str)
                    
                    # Determine transaction type
                    tipo_movimentacao = "Débito" if value < 0 else "Crédito"
                    
                    # Create transaction
                    transaction = Transaction(
                        data=formatted_date,
                        descricao_original=description.strip(),
                        valor=value,
                        tipo_movimentacao=tipo_movimentacao,
                        banco=template.banco
                    )
                    transactions.append(transaction)
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing table row: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing table with template: {str(e)}")
            raise
        
        return transactions
    
    def _process_csv(self, filepath: str, bank_template: str) -> List[Transaction]:
        """Process CSV file"""
        try:
            template = self._get_bank_template(bank_template, filepath)
            if not template:
                template = self._get_default_csv_template()
            
            # Read CSV file
            df = pd.read_csv(filepath)
            
            # Skip header and footer rows
            start_row = template.linhas_ignoradas_topo
            end_row = len(df) - template.linhas_ignoradas_rodape
            df = df.iloc[start_row:end_row]
            
            transactions = []
            
            for _, row in df.iterrows():
                try:
                    # Get column values
                    date_str = str(row.iloc[template.colunas_csv.get('data', 0)])
                    description = str(row.iloc[template.colunas_csv.get('descricao', 1)])
                    value_str = str(row.iloc[template.colunas_csv.get('valor', 2)])
                    
                    # Parse date
                    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    
                    # Parse value
                    value_str = value_str.replace('.', '').replace(',', '.')
                    value = float(value_str)
                    
                    # Determine transaction type
                    tipo_movimentacao = "Débito" if value < 0 else "Crédito"
                    
                    # Create transaction
                    transaction = Transaction(
                        data=formatted_date,
                        descricao_original=description.strip(),
                        valor=value,
                        tipo_movimentacao=tipo_movimentacao,
                        banco=template.banco
                    )
                    transactions.append(transaction)
                
                except Exception as e:
                    logger.warning(f"Error parsing CSV row: {str(e)}")
                    continue
            
            return transactions
        
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            raise
    
    def _process_ofx(self, filepath: str) -> List[Transaction]:
        """Process OFX file"""
        try:
            from ofxparse import OfxParser
            
            with open(filepath, 'rb') as f:
                ofx = OfxParser.parse(f)
            
            transactions = []
            
            # Get account information
            account = ofx.account
            bank_name = getattr(account.institution, 'organization', 'Unknown Bank')
            
            # Process transactions
            for transaction in account.statement.transactions:
                # Parse date
                date_obj = transaction.date
                formatted_date = date_obj.strftime('%Y-%m-%d')
                
                # Get description
                description = transaction.memo or transaction.payee or 'No description'
                
                # Get value
                value = float(transaction.amount)
                
                # Determine transaction type
                tipo_movimentacao = "Débito" if value < 0 else "Crédito"
                
                # Create transaction
                trans = Transaction(
                    data=formatted_date,
                    descricao_original=description.strip(),
                    valor=value,
                    tipo_movimentacao=tipo_movimentacao,
                    banco=bank_name
                )
                transactions.append(trans)
            
            return transactions
        
        except ImportError:
            logger.error("ofxparse library not available")
            raise Exception("Biblioteca de processamento OFX não disponível")
        except Exception as e:
            logger.error(f"Error processing OFX file: {str(e)}")
            raise
    
    def _get_bank_template(self, bank_template: str, filepath: str) -> Optional[BankTemplate]:
        """Get bank template by name or auto-detect"""
        try:
            if bank_template == 'auto':
                # Try to auto-detect bank from file content
                bank_template = self._auto_detect_bank(filepath)
            
            if bank_template:
                templates = FileHandler.load_bank_templates()
                for template in templates:
                    if template.banco.lower() == bank_template.lower():
                        return template
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting bank template: {str(e)}")
            return None
    
    def _auto_detect_bank(self, filepath: str) -> Optional[str]:
        """Auto-detect bank from file content"""
        try:
            # Simple auto-detection based on file content
            # This is a simplified version - in practice, you'd want more sophisticated detection
            
            file_extension = os.path.splitext(filepath)[1].lower()
            
            if file_extension == '.pdf':
                try:
                    import pdfplumber
                    with pdfplumber.open(filepath) as pdf:
                        first_page = pdf.pages[0]
                        text = first_page.extract_text()
                        
                        if 'bradesco' in text.lower():
                            return 'bradesco'
                        elif 'itau' in text.lower() or 'itaú' in text.lower():
                            return 'itau'
                        elif 'banco do brasil' in text.lower():
                            return 'bb'
                        
                except Exception:
                    pass
            
            return None
        
        except Exception as e:
            logger.error(f"Error auto-detecting bank: {str(e)}")
            return None
    
    def _get_default_template(self) -> BankTemplate:
        """Get default template for fallback"""
        return BankTemplate(
            banco="Genérico",
            formato="pdf",
            regex_data=r'\d{2}/\d{2}/\d{4}',
            regex_valor=r'-?\d{1,3}(?:\.?\d{3})*,\d{2}',
            regex_descricao=r'.+',
            modo_leitura="texto"
        )
    
    def _get_default_csv_template(self) -> BankTemplate:
        """Get default CSV template"""
        return BankTemplate(
            banco="Genérico",
            formato="csv",
            colunas_csv={
                'data': 0,
                'descricao': 1,
                'valor': 2,
                'saldo': 3
            }
        )
