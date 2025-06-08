# TODO: добавить вывод статуса, типо по плану или нет
def pretty_projects(projects):
    formatted_projects = []
    for project in projects:
        project_id = project.get('id', 'N/A')
        project_name = project.get('name', 'Без имени')
        # Получаем описание. Используем .get() для безопасного доступа к вложенным ключам
        project_description_raw = project.get('description', {}).get('raw', 'Без описания')
        formatted_projects.append(
            f"- ID: {project_id}, Название: **{project_name}**\n"
            f"  Описание: {project_description_raw}"
        )
    return formatted_projects

