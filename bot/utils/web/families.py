from config import FAMILY_TEMPLATE
from . import screenshot

async def make_family_tree(nodes: list) -> bytes:
    body = """
        <div class="tree">
            <ul>
    """

    def render_node(node_list, depth=0):
        content = ""
        for node in node_list:
            content += "<li>"
            
            # Добавляем класс root-couple для первой пары
            root_class = "root-couple" if depth == 0 else ""
            content += f'<div class="family-node {root_class}">'
            
            for member in node['members']:
                is_me = "me-card" if member.get("is_me") else ""
                name_chopped = member['name'][:18] + (".." if len(member['name']) > 18 else "")
                content += f"""
                <div class="member-card {is_me}">
                    <div class="name">{f"Вы ({name_chopped})" if member.get("is_me") else name_chopped}</div>
                """

                if member['adoption_date']:
                    content += f'<div class="id">{member['adoption_date']}</div>'
                content += "</div>"
            content += '</div>'
            
            # Рекурсия с увеличением глубины
            if node['children']:
                content += "<ul>"
                content += render_node(node['children'], depth + 1)
                content += "</ul>"
            
            content += "</li>"
        return content

    body += render_node(nodes, depth=0)
    body += """
            </ul>
        </div>
    """
    
    ss = await screenshot(body, FAMILY_TEMPLATE, ".tree")
    return ss
