from datetime import datetime, timezone
from config import FAMILY_TEMPLATE
from services.web import screenshot
from services.time_utils import TimedeltaFormatter

# Constants
MAX_NAME_LENGTH_REFERENCE = 12
MAX_NAME_LENGTH_FULL = 18

async def make_family_tree(nodes: list) -> bytes:
    """
    Generate a family tree screenshot from node data.
    
    Args:
        nodes: List of family nodes with structure:
            {
                'marriage_id': Optional[int],
                'members': List[{'name': str, 'is_me': bool, is_partner: bool, 'adoption_date': Optional[datetime]}],
                'children': List[node]
            }
    """
    rendered_marriages = set()
    
    def truncate_name(name: str, max_length: int) -> str:
        if len(name) <= max_length:
            return name
        return name[:max_length] + ".."
    
    def render_member_card(member: dict, is_reference: bool = False) -> str:
        max_length = MAX_NAME_LENGTH_REFERENCE if is_reference else MAX_NAME_LENGTH_FULL
        name = truncate_name(member['name'], max_length)
        
        if member.get('is_me'):
            name = f"Вы ({name})"
            card_class = "me-card"
        else:
            card_class = "reference-card" if is_reference else ""
        
        if not member.get('is_partner') and member.get('adoption_date'):
            time_diff = datetime.now(timezone.utc) - member["adoption_date"]
            adoption_display = f"сын/дочь уже {TimedeltaFormatter.format(time_diff, suffix='none')}"
        else:
            adoption_display = "супруг/cупруга"
        
        return f'''
        <div class="member-card {card_class}">
            <div class="name">{name}</div>
            <div class="id">{adoption_display}</div>
        </div>
        '''
    
    def render_node(node_list: list, is_root: bool = False) -> str:
        parts = []
        
        for node in node_list:
            parts.append("<li>")
            
            marriage_id = node.get('marriage_id')
            
            if marriage_id and marriage_id in rendered_marriages:
                # Reference to already-rendered marriage
                blood_m = next((m for m in node.get('members', []) if not m.get('is_partner')), node.get('members', [{}])[0])
                name = truncate_name(blood_m.get('name', ''), MAX_NAME_LENGTH_REFERENCE*2)
                
                if blood_m.get('adoption_date'):
                    time_diff = datetime.now(timezone.utc) - blood_m["adoption_date"]
                    time_str = TimedeltaFormatter.format(time_diff, suffix="none")
                    status_text = f"← сын/дочь уже {time_str}" 
                else:
                    status_text = "← показано выше"
                
                parts.append(f'''
                <div class="family-node reference-node">
                    <div class="member-card reference-card">
                        <div class="name">{name}</div>
                        <div class="id">{status_text}</div>
                    </div>
                </div>
                ''')
            else:
                # Full node rendering
                if marriage_id:
                    rendered_marriages.add(marriage_id)
                
                root_class = "root-couple" if is_root else ""
                parts.append(f'<div class="family-node {root_class}">')
                
                for member in node.get('members', []):
                    parts.append(render_member_card(member))
                
                parts.append('</div>')
                
                # Recurse for children
                if node.get('children'):
                    parts.append("<ul>")
                    parts.append(render_node(node['children'], is_root=False))
                    parts.append("</ul>")
            
            parts.append("</li>")
        
        return "".join(parts)
    
    body = f'''
    <div class="tree">
        <ul>
            {render_node(nodes, is_root=True)}
        </ul>
    </div>
    '''
    
    return await screenshot(body, FAMILY_TEMPLATE, ".tree")
