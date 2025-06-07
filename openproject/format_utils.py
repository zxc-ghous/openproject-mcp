def pretty_print_projects(projects):
    print(f"\nВсего получено {len(projects)} проектов OpenProject:")
    for project in projects:
        project_id = project.get("id")
        project_name = project.get("name")
        print(f"- ID: {project_id}, Название: {project_name}")