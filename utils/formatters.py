import re
import logging

logger = logging.getLogger(__name__)

def format_markdown_response(text: str) -> str:
    """Format response for MarkdownV2 with better escape."""
    try:
        # Pre-process text to handle common patterns
        text = text.replace('*', '\\*')
        text = text.replace('_', '\\_')
        text = text.replace('[', '\\[')
        text = text.replace(']', '\\]')
        text = text.replace('(', '\\(')
        text = text.replace(')', '\\)')
        text = text.replace('~', '\\~')
        text = text.replace('`', '\\`')
        text = text.replace('>', '\\>')
        text = text.replace('#', '\\#')
        text = text.replace('+', '\\+')
        text = text.replace('-', '\\-')
        text = text.replace('=', '\\=')
        text = text.replace('|', '\\|')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        text = text.replace('.', '\\.')
        text = text.replace('!', '\\!')

        # Split text into paragraphs
        paragraphs = text.split('\n')
        formatted_paragraphs = []
        
        for p in paragraphs:
            # Format Alya-chan mentions
            p = p.replace("Alya\\-chan", "*Alya\\-chan*")
            
            # Format Japanese expressions with italic
            japanese_words = ["ara ara", "ne~", "desu", "kun", "chan", "mou", "ehehe"]
            for word in japanese_words:
                if word in p.lower():
                    p = p.replace(word, f"_{word}_")
            
            # Format numbers
            p = re.sub(r'(\d+)', r'`\1`', p)
            
            formatted_paragraphs.append(p)
        
        return '\n'.join(formatted_paragraphs)
    except Exception as e:
        logger.error(f"Error formatting markdown: {e}")
        # Return safe text if formatting fails
        return text.replace('[', '\\[').replace(']', '\\]')