
def pretty_projects(projects):
    formatted_projects = []
    for project in projects:
        project_id = project.get('id', 'N/A')
        project_name = project.get('name', 'Без имени')
        project_status = project.get('_links', {}).get('status', {}).get('title', 'Статус неизвестен')
        # Получаем описание. Используем .get() для безопасного доступа к вложенным ключам
        project_description_raw = project.get('description', {}).get('raw', 'Без описания')
        formatted_projects.append(
            f"- ID: {project_id}, Название: **{project_name}**\n"
            f"  Описание: {project_description_raw}"
            f"  Статус: {project_status}"
        )
    return formatted_projects

