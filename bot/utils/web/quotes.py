import base64
import html
from itertools import groupby
from typing import Optional

from utils.web import screenshot
from config import QUOTE_TEMPLATE


# Constants
MAX_MESSAGE_LENGTH = 710
AVATAR_GRADIENTS = [
    'background-image: linear-gradient(45deg, #4facfe, #00f2fe);',
    'background-image: linear-gradient(45deg, #ff6f61, #ff8c7a);',
    'background-image: linear-gradient(45deg, #43e97b, #39ffb2);',
]

# HTML Templates (consider moving to external files for larger projects)
TEMPLATES = {
    'content': """
    <div class="chat-message">
      <div class="avatar" {letter_styling}>{avatar}</div>
      <div class="message-content">
        <div class="chat-bubble">
          <div class="username">{name}</div>
          {media}
          <div class="message">{text}</div>
        </div>
      </div>
    </div>
    """,
    
    'additional_content': """
    <div class="chat-message consecutive">
      <div class="avatar"></div>
      <div class="message-content">
        {bubbles}
      </div>
    </div>
    """,
    
    'additional_bubble': """
    <div class="chat-bubble">
        {media}
        <div class="message">{text}</div>
    </div>
    """,
    
    'media': """
    <img class="message-media" src="{source}"></img>
    """
}


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent XSS."""
    return html.escape(text)


def truncate_text(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def encode_media_as_data_url(media: dict) -> str:
    """Encode media as base64 data URL."""
    encoded = base64.b64encode(media['source']).decode('utf-8')
    return f"data:{media['type']};base64,{encoded}"


def create_avatar_html(avatar: Optional[bytes], name: str) -> tuple[str, str]:
    """
    Create avatar HTML and styling.
    
    Returns:
        tuple: (avatar_html, styling_attribute)
    """
    if avatar:
        encoded_avatar = base64.b64encode(avatar).decode('utf-8')
        avatar_html = f'<img src="data:image/jpeg;base64,{encoded_avatar}" alt="avatar" />'
        styling = ''
    else:
        avatar_html = escape_html(name[0].upper())
        gradient = AVATAR_GRADIENTS[hash(name) % len(AVATAR_GRADIENTS)]
        styling = f'style="{gradient}"'
    
    return avatar_html, styling


def create_media_html(media: Optional[dict]) -> str:
    """Create media HTML if media exists."""
    if not media:
        return ""
    
    encoded_media = encode_media_as_data_url(media)
    return TEMPLATES['media'].format(source=encoded_media)


def create_message_bubble(material: list, is_first: bool = True) -> str:
    """
    Create HTML for a single message bubble.
    
    Args:
        material: Message material dictionary
        is_first: Whether this is the first message in a group
    
    Returns:
        HTML string for the message bubble
    """
    text = escape_html(truncate_text(material['text']))
    media_html = create_media_html(material.get('media'))
    
    if is_first:
        avatar_html, styling = create_avatar_html(
            material.get('avatar'), 
            material['name']
        )
        name = escape_html(material['name'])
        
        return TEMPLATES['content'].format(
            avatar=avatar_html,
            letter_styling=styling,
            name=name,
            media=media_html,
            text=text
        )
    else:
        return TEMPLATES['additional_bubble'].format(
            media=media_html,
            text=text
        )


def validate_materials(materials: list) -> None:
    """
    Validate input materials.
    
    Raises:
        ValueError: If materials are invalid
    """
    if not materials:
        raise ValueError("Materials list cannot be empty")
    
    for idx, material in enumerate(materials):
        if not isinstance(material, dict):
            raise ValueError(f"Material at index {idx} must be a dictionary")
        if 'name' not in material:
            raise ValueError(f"Material at index {idx} missing required 'name' key")
        if 'text' not in material:
            raise ValueError(f"Material at index {idx} missing required 'text' key")


async def make_quote(materials: list) -> bytes:
    """
    Create a quote screenshot from message materials.
    
    Args:
        materials: List of message dictionaries containing name, text, 
                   and optionally avatar and media
    
    Returns:
        Screenshot bytes of the rendered quote
        
    Raises:
        ValueError: If materials are invalid or empty
    """
    validate_materials(materials)
    
    html_parts = []
    
    # Group consecutive messages by sender name
    for sender_name, group in groupby(materials, key=lambda m: m['name']):
        group_messages = list(group)
        
        # First message in group gets full styling
        first_message = group_messages[0]
        html_parts.append(create_message_bubble(first_message, is_first=True))
        
        # Additional consecutive messages from same sender
        if len(group_messages) > 1:
            additional_bubbles = [
                create_message_bubble(msg, is_first=False)
                for msg in group_messages[1:]
            ]
            
            additional_html = TEMPLATES['additional_content'].format(
                bubbles=''.join(additional_bubbles)
            )
            html_parts.append(additional_html)
    
    quote_content = ''.join(html_parts)
    
    # Take screenshot (assuming this function exists in your codebase)
    screenshot_bytes = await screenshot(quote_content, QUOTE_TEMPLATE, ".chat-container")
    
    return screenshot_bytes
