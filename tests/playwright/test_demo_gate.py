import os

import pytest


def test_hotfix_can_save(page):
    target = os.getenv("BREAKERS_TARGET_URL")
    if not target:
        pytest.skip("BREAKERS_TARGET_URL is required for the deployed demo gate")

    page.goto(target)
    page.get_by_role("button", name="Guardar").click()
    page.get_by_text("Guardado correctamente").wait_for()
