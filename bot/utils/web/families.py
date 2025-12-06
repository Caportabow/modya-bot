from config import FAMILY_TEMPLATE
from . import screenshot

async def make_family_tree(nodes: list) -> bytes:
    body = """
        <div class="tree">
            <ul>
    """

    def render_node(node_list, rendered_marriages=None, depth=0):
        if rendered_marriages is None:
            rendered_marriages = set()
            
        content = ""
        for node in node_list:
            content += "<li>"
            
            marriage_id = node.get('marriage_id')
            
            # Проверяем дубликат
            if marriage_id and marriage_id in rendered_marriages:
                # Показываем ссылку вместо полного узла
                members_preview = " & ".join([
                    m['name'][:12] + (".." if len(m['name']) > 12 else "")
                    for m in node['members']
                ])

                content += f'''
                <div class="family-node reference-node">
                    <div class="member-card reference-card">
                        <div class="name">{members_preview}</div>
                        <div class="id">← показано выше</div>
                    </div>
                </div>
                '''
            else:
                # Отмечаем как отрисованный
                if marriage_id:
                    rendered_marriages.add(marriage_id)
                
                # Обычная отрисовка
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
                
                # Рекурсия с передачей set
                if node['children']:
                    content += "<ul>"
                    content += render_node(node['children'], rendered_marriages, depth + 1)
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
