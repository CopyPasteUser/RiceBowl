"""Explicit, reviewed next-login selection for offline Creator workflows.

No live Wayland/XFCE mutation, no autostart of services or implicit commit.
All selection changes use the existing lock and one-level restore state.
"""

from __future__ import annotations

from . import recipes, review


STAGE_VERSION = 1


class StageError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_stage_request") -> None:
        super().__init__(message)
        self.code = code


def _hash(token: str) -> str:
    return review._semantic_hash(review._manifest(recipes.load(token)))


def status() -> dict[str, object]:
    """Read the next-session choice and compare against the current recipe."""
    try:
        active, previous = recipes.current_selection()
        fingerprint = _hash(active)
        # The session resolver performs the same fingerprint check at login.
        # Report a changed staged recipe as invalid instead of showing a
        # misleading 'ready' status.
        recipes.selected_recipe()
        can_restore = previous is not None
        if can_restore:
            try:
                recipes.load(previous)
            except recipes.RecipeError:
                can_restore = False
    except recipes.RecipeError as exc:
        raise StageError("Next-session selection is unavailable or invalid",
                         code="invalid_selection_state") from exc
    return {"stage_version": STAGE_VERSION, "ok": True, "applied": False,
            "next_session": active, "semantic_sha256": fingerprint,
            "previous": previous, "can_restore": can_restore}


def stage(token: str, expected_semantic_sha256: str,
          *, expected_active: str | None = None) -> dict[str, object]:
    """Stage an existing ID only if it still matches the reviewed semantics."""
    try:
        target, previous = recipes.change_selection(
            token, expected_active=expected_active,
            expected_semantic_sha256=expected_semantic_sha256)
    except recipes.SelectionConflict as exc:
        raise StageError("Next-session selection changed; inspect it and retry",
                         code="selection_conflict") from exc
    except recipes.RecipeFingerprintMismatch as exc:
        raise StageError("Recipe no longer matches the reviewed semantic fingerprint",
                         code="recipe_changed") from exc
    except (recipes.RecipeError, OSError) as exc:
        raise StageError("Recipe could not be staged safely", code="invalid_stage_request") from exc
    return {"stage_version": STAGE_VERSION, "ok": True, "staged": True,
            "applied": False, "changed": target != previous,
            "next_session": target, "previous": previous,
            "semantic_sha256": expected_semantic_sha256}


def rollback(*, expected_active: str | None = None) -> dict[str, object]:
    """Explicit one-step rollback of the future login selection, never live."""
    try:
        target, previous = recipes.change_selection(restore=True,
                                                     expected_active=expected_active)
    except recipes.SelectionConflict as exc:
        raise StageError("Next-session selection changed; inspect it and retry",
                         code="selection_conflict") from exc
    except (recipes.RecipeError, OSError) as exc:
        raise StageError("Previous recipe is missing or cannot be restored",
                         code="rollback_unavailable") from exc
    return {"stage_version": STAGE_VERSION, "ok": True, "staged": True,
            "applied": False, "changed": target != previous,
            "next_session": target, "previous": previous}


def invalid_stage(exc: StageError) -> dict[str, object]:
    return {"stage_version": STAGE_VERSION, "ok": False, "staged": False,
            "applied": False, "error": {"code": exc.code, "message": str(exc)}}
