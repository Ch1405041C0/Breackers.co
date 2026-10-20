import os


def test_hotfix_can_save(page):
    target = os.environ["BREAKERS_TARGET_URL"]
    page.goto(target)
    page.get_by_role("button", name="Guardar").click()
    page.get_by_text("Guardado correctamente").wait_for()
