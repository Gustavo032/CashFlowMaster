# CashFlowMaster - Sistema de Automação Contábil

## Overview

CashFlowMaster é uma aplicação web local desenvolvida em Flask (Python) projetada para automatizar o processo de importação de extratos bancários e mapeamento de transações para contas contábeis. O sistema oferece funcionalidades completas de importação de múltiplos formatos de arquivo, mapeamento inteligente baseado em regras, e exportação personalizada para diversos sistemas contábeis.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Flask com templates Jinja2
- **CSS Framework**: Bootstrap 5 com tema dark personalizado
- **JavaScript**: Vanilla JS com funcionalidades modernas (tooltips, validação, auto-save)
- **Icons**: Feather Icons para interface consistente
- **Responsive Design**: Layout adaptável para diferentes dispositivos

### Backend Architecture
- **Framework**: Flask (Python)
- **Structure**: Modular com separação clara de responsabilidades
- **Routes**: Centralizadas em `routes.py`
- **Models**: Classes Python para entidades de negócio
- **Utils**: Módulos especializados para processamento de dados

### Data Storage Solutions
- **Primary Storage**: JSON files no sistema de arquivos
- **File Structure**: Organizada em diretórios específicos (`data/`, `uploads/`, `logs/`)
- **No Database**: Sistema file-based para simplicidade e portabilidade
- **Backup Strategy**: Arquivos JSON versionáveis e facilmente copiáveis

## Key Components

### 1. File Processing System
- **PDF Processing**: Múltiplas estratégias de extração (texto direto, OCR, heurísticas)
- **CSV/OFX Support**: Importação direta com mapeamento de colunas
- **Template System**: Templates JSON específicos por banco
- **Fallback Mechanisms**: Estratégias alternativas quando métodos principais falham

### 2. Transaction Mapping Engine
- **Rule-based Mapping**: Sistema de regras personalizáveis
- **Priority System**: Hierarquia de aplicação de regras
- **Keyword Matching**: Busca por palavras-chave na descrição
- **Regex Support**: Padrões avançados para casos complexos

### 3. Template Management
- **Bank Templates**: Configurações específicas por instituição financeira
- **JSON Configuration**: Templates armazenados como arquivos JSON
- **Auto-detection**: Tentativa de detectar o banco automaticamente
- **Custom Rules**: Regras personalizadas pelos usuários

### 4. Export System
- **Multiple Formats**: CSV, TXT, JSON
- **Layout Templates**: Configurações de exportação personalizáveis
- **System Integration**: Formatos para sistemas contábeis específicos
- **Date Filtering**: Exportação por períodos específicos

## Data Flow

### 1. Import Process
```
File Upload → Format Detection → Template Selection → Data Extraction → Transaction Creation → Storage
```

### 2. Mapping Process
```
Raw Transaction → Custom Rules Check → Standard Mapping → Account Assignment → Manual Review (if needed)
```

### 3. Export Process
```
Transaction Filter → Layout Selection → Format Conversion → File Generation → Download
```

## External Dependencies

### Python Packages
- **Flask**: Web framework principal
- **Werkzeug**: Utilities e middleware
- **PDF Processing**: pdfplumber, PyMuPDF (fitz) para PDFs
- **OCR**: pytesseract para reconhecimento de texto
- **Data Processing**: pandas para manipulação de dados
- **File Handling**: Standard library para operações de arquivo

### Frontend Dependencies
- **Bootstrap 5**: Framework CSS via CDN
- **Feather Icons**: Biblioteca de ícones via CDN
- **No Build Process**: Arquivos estáticos servidos diretamente

### System Dependencies
- **Tesseract OCR**: Para processamento de PDFs com OCR
- **Python 3.x**: Runtime environment
- **File System**: Acesso completo para leitura/escrita

## Deployment Strategy

### Development
- **Local Development**: Flask development server
- **Port**: 5000 (configurável)
- **Debug Mode**: Habilitado para desenvolvimento
- **Hot Reload**: Automático com Flask

### Production Considerations
- **WSGI Server**: Configurado com ProxyFix para reverse proxy
- **Security**: Session secret configurável via environment
- **Logging**: Sistema de logs estruturado
- **File Permissions**: Diretórios criados automaticamente

### Architecture Decisions

#### File-based Storage
- **Problem**: Necessidade de simplicidade e portabilidade
- **Solution**: Arquivos JSON para persistência
- **Rationale**: Elimina dependência de banco de dados, facilita backup/migração
- **Trade-offs**: Menor performance em grandes volumes, mas maior simplicidade

#### Modular Processing
- **Problem**: Diferentes formatos de arquivo e bancos
- **Solution**: Sistema de templates e processadores especializados
- **Rationale**: Flexibilidade para adicionar novos bancos/formatos
- **Trade-offs**: Mais complexidade inicial, mas alta extensibilidade

#### Rule-based Mapping
- **Problem**: Automatização do mapeamento contábil
- **Solution**: Sistema hierárquico de regras com scoring
- **Rationale**: Balança automação com controle manual
- **Trade-offs**: Requer configuração inicial, mas oferece alta precisão

#### Template System
- **Problem**: Variabilidade nos formatos de extratos bancários
- **Solution**: Templates JSON configuráveis por banco
- **Rationale**: Flexibilidade sem necessidade de código
- **Trade-offs**: Configuração manual necessária, mas alta adaptabilidade