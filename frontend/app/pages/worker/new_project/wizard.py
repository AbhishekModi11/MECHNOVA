from nicegui import ui
from app.session import require_auth
from app.components.layout import app_shell
from app.pages.worker.new_project.step_design import render_step_design


def register_new_project_wizard():
    @ui.page("/worker/new-project")
    def new_project_wizard_page():
        if not require_auth(allowed_roles=["worker"]):
            return
        app_shell("Step 1: New Project")
        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            render_step_design(state={}, project_id=None)

    @ui.page("/worker/projects/{project_id}/upload")
    def project_upload_restore_page(project_id: str):
        if not require_auth(allowed_roles=["worker"]):
            return
        app_shell("Step 1: Part Design & Upload")
        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            render_step_design(state={}, project_id=project_id)
