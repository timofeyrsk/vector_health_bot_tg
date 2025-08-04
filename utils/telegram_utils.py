import re
from typing import Tuple, List, Dict, Union

def parse_markdown_to_entities(text: str) -> Tuple[str, List[Dict]]:
    """
    Parse simple Markdown text to Telegram Message Entities.
    
    Supported formats:
    - *bold* -> bold entity
    - _italic_ -> italic entity  
    - ~strikethrough~ -> strikethrough entity
    
    Args:
        text: Text with Markdown formatting
        
    Returns:
        Tuple of (plain_text, entities_list)
    """
    if not text:
        return "", []
    
    entities = []
    
    # Define all formatting patterns
    patterns = [
        (r'\*(.*?)\*', 'bold'),
        (r'_(.*?)_', 'italic'),
        (r'~(.*?)~', 'strikethrough')
    ]
    
    # Find all matches with their positions
    all_matches = []
    for pattern, entity_type in patterns:
        for match in re.finditer(pattern, text):
            all_matches.append({
                'start': match.start(),
                'end': match.end(),
                'content': match.group(1),
                'type': entity_type
            })
    
    # Sort matches by start position
    all_matches.sort(key=lambda x: x['start'])
    
    # Build plain text and calculate offsets using UTF-16 positions
    plain_text = ""
    current_pos = 0
    
    for match in all_matches:
        # Add text before this match
        plain_text += text[current_pos:match['start']]
        
        # Calculate offset in plain text using UTF-16 length
        # Convert to UTF-16 and count code units (divide by 2 for UTF-16LE)
        offset = len(plain_text.encode('utf-16-le')) // 2
        
        # Calculate length of content in UTF-16
        content_length = len(match['content'].encode('utf-16-le')) // 2
        
        # Create entity
        entity = {
            'type': match['type'],
            'offset': offset,
            'length': content_length
        }
        entities.append(entity)
        
        # Add the content to plain text
        plain_text += match['content']
        
        # Move position past this match
        current_pos = match['end']
    
    # Add remaining text
    plain_text += text[current_pos:]
    
    # Sort entities by offset for consistency
    entities.sort(key=lambda x: x['offset'])
    
    return plain_text, entities

def clean_keyboard_text(text: str) -> str:
    """
    Clean text for keyboard buttons by removing all markdown formatting.
    
    Args:
        text: Text that may contain markdown formatting
        
    Returns:
        Clean text without any markdown symbols
    """
    if not text:
        return ""
    
    # Remove all markdown formatting symbols
    cleaned = re.sub(r'[\*_~`\[\]\(\)]', '', text)
    return cleaned

def clean_keyboard_markup(keyboard: List[List[Dict]]) -> List[List[Dict]]:
    """
    Clean all text fields in keyboard markup to prevent formatting errors.
    
    Args:
        keyboard: Keyboard markup structure
        
    Returns:
        Cleaned keyboard markup
    """
    if not keyboard:
        return keyboard
    
    cleaned_keyboard = []
    
    for row in keyboard:
        cleaned_row = []
        for button in row:
            if isinstance(button, dict):
                cleaned_button = button.copy()
                # Clean text field
                if 'text' in cleaned_button:
                    cleaned_button['text'] = clean_keyboard_text(cleaned_button['text'])
                cleaned_row.append(cleaned_button)
            elif isinstance(button, str):
                # Если вдруг встретили строку — просто добавляем как есть
                cleaned_row.append(button)
            else:
                # На всякий случай, если тип неизвестен
                cleaned_row.append(button)
        cleaned_keyboard.append(cleaned_row)
    
    return cleaned_keyboard 