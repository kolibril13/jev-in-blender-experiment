"""Jev Operator Search: describe what you want to do, get the Blender operator.

Type a request in the N-panel (3D Viewport > Sidebar > Jev), press Enter, and
TypeSafe's Jev ranks every registered operator against it. Click a result to
run it, or copy its bpy.ops call.
"""

import contextlib
import os
import queue
import threading

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import AddonPreferences, Operator, Panel, PropertyGroup

from . import catalog as cat
from . import config as jev_config
from . import search as jev_search
from . import jev_api
from .jev_api import JevError

# ---------------------------------------------------------------------------
# Background search plumbing
# ---------------------------------------------------------------------------

_results_queue = queue.Queue()
_search_thread = None


def _redraw_all():
    wm = bpy.context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _poll_results():
    """bpy.app.timers callback: move finished searches into the UI properties."""
    wm = bpy.context.window_manager
    props = wm.jev_search
    try:
        outcome = _results_queue.get_nowait()
    except queue.Empty:
        return 0.1 if props.searching else None

    props.searching = False
    props.results.clear()
    if outcome["error"]:
        props.status = outcome["error"]
    else:
        results, meta = outcome["results"], outcome["meta"]
        for r in results:
            item = props.results.add()
            item.idname = r["idname"]
            item.label = r["label"]
            item.description = r["description"]
            item.module = r["module"]
            item.score = r["score"]
        mods = ", ".join(f"{m} {p:.0%}" for m, p in meta["modules"]) or meta["strategy"]
        props.status = f"{meta['seconds']:.2f}s · {meta['input_tokens']:,} tokens · {mods}"
    _redraw_all()
    return None


def _run_search(api_key, text, context_summary, prefs):
    try:
        results, meta = jev_search.search(
            api_key, text, context_summary,
            top_modules=prefs["top_modules"], top_results=prefs["top_results"], model=prefs["model"],
            strategy=prefs["strategy"], module_mass=prefs["module_mass"],
        )
        _results_queue.put({"error": None, "results": results, "meta": meta})
    except JevError as e:
        _results_queue.put({"error": str(e), "results": None, "meta": None})
    except Exception as e:  # keep the UI alive whatever happens in the thread
        _results_queue.put({"error": f"{type(e).__name__}: {e}", "results": None, "meta": None})


def _blender_context_summary(context):
    obj = context.active_object
    return {
        "mode": context.mode,
        "active_object_type": obj.type if obj else None,
        "active_object_name": obj.name if obj else None,
        "selected_object_count": len(context.selected_objects),
        "editor": context.area.type if context.area else None,
    }


def _prefs(context):
    return context.preferences.addons[__package__].preferences


def _api_key(context):
    return (
        _prefs(context).api_key.strip()
        or jev_config.load_api_key()
        or os.environ.get("TYPESAFE_API_KEY", "")
    )


def start_search(context):
    global _search_thread
    props = context.window_manager.jev_search
    text = props.query.strip()
    if not text:
        return
    if props.searching:
        return
    api_key = _api_key(context)
    if not api_key:
        props.status = "Set your TypeSafe API key in the add-on preferences"
        return

    prefs = _prefs(context)
    cat.get_catalog()  # build on the main thread; the worker only reads it
    props.searching = True
    props.status = "Asking Jev…"
    _search_thread = threading.Thread(
        target=_run_search,
        args=(api_key, text, _blender_context_summary(context), {
            "top_modules": prefs.top_modules, "top_results": prefs.top_results,
            "model": prefs.model, "strategy": prefs.strategy, "module_mass": prefs.module_mass,
        }),
        daemon=True,
    )
    _search_thread.start()
    if not bpy.app.timers.is_registered(_poll_results):
        bpy.app.timers.register(_poll_results, first_interval=0.1)


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def _on_query_update(self, context):
    # Fires when the user confirms the text field (Enter).
    start_search(context)


class JevResultItem(PropertyGroup):
    idname: StringProperty()
    label: StringProperty()
    description: StringProperty()
    module: StringProperty()
    score: FloatProperty()


class JevSearchProps(PropertyGroup):
    query: StringProperty(
        name="",
        description="Describe what you want to do, then press Enter",
        update=_on_query_update,
    )
    searching: BoolProperty(default=False)
    status: StringProperty(default="")
    results: CollectionProperty(type=JevResultItem)


# Set while the stored key is being written back into the preferences, so the
# assignment doesn't bounce straight back out to disk.
_restoring_api_key = False


def _on_api_key_update(self, context):
    if not _restoring_api_key:
        jev_config.save_api_key(self.api_key.strip())


def _restore_api_key():
    """Put the key saved by a previous session back into the preferences."""
    global _restoring_api_key
    addon = bpy.context.preferences.addons.get(__package__)
    if addon is None:
        return 0.5  # preferences not ready yet — try again shortly
    if not addon.preferences.api_key:
        stored = jev_config.load_api_key()
        if stored:
            _restoring_api_key = True
            try:
                addon.preferences.api_key = stored
            finally:
                _restoring_api_key = False
    return None


class JevPreferences(AddonPreferences):
    bl_idname = __package__

    api_key: StringProperty(
        name="TypeSafe API key",
        description="From https://console.typesafe.ai/ — saved for future sessions; falls back to the TYPESAFE_API_KEY environment variable",
        subtype="PASSWORD",
        update=_on_api_key_update,
    )
    model: StringProperty(name="Model", default="jev-latest")
    top_modules: IntProperty(
        name="Modules to expand",
        description="How many top-ranked operator categories are searched in detail",
        default=3, min=1, max=8,
    )
    top_results: IntProperty(name="Results shown", default=8, min=1, max=25)
    strategy: EnumProperty(
        name="Strategy",
        items=(
            ("hierarchical", "Hierarchical (2 requests)", "Rank modules first, then the operators of the likeliest modules"),
            ("flat", "Flat (1 request)", "Rank every operator in one request; fewer round trips, ~4x the tokens"),
        ),
        default="hierarchical",
    )
    module_mass: FloatProperty(
        name="Module probability mass",
        description="Hierarchical: stop expanding modules once their combined probability reaches this",
        default=0.9, min=0.5, max=1.0,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.prop(self, "model")
        layout.prop(self, "strategy")
        row = layout.row()
        row.enabled = self.strategy == "hierarchical"
        row.prop(self, "top_modules")
        row.prop(self, "module_mass")
        layout.prop(self, "top_results")
        if not self.api_key and os.environ.get("TYPESAFE_API_KEY"):
            layout.label(text="Using TYPESAFE_API_KEY from the environment", icon="INFO")


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class JEV_OT_search(Operator):
    bl_idname = "jev.search"
    bl_label = "Search operators with Jev"
    bl_description = "Rank Blender operators against the request text"

    def execute(self, context):
        start_search(context)
        return {"FINISHED"}


def _resolve(idname):
    mod_name, op_name = idname.split(".", 1)
    return getattr(getattr(bpy.ops, mod_name), op_name)


def _window_region(area):
    for region in area.regions:
        if region.type == "WINDOW":
            return region
    return None


class JEV_OT_run_operator(Operator):
    bl_idname = "jev.run_operator"
    bl_label = "Run operator"
    bl_description = "Invoke this operator (as if chosen from a menu)"

    idname: StringProperty()

    def execute(self, context):
        op = _resolve(self.idname)
        # Buttons live in the sidebar (UI region); most operators expect the main
        # WINDOW region, so run them there.
        region = _window_region(context.area) if context.area else None
        try:
            with (context.temp_override(region=region) if region else contextlib.nullcontext()):
                if not op.poll():
                    self.report({"WARNING"}, f"{self.idname} can't run in the current context")
                    return {"CANCELLED"}
                result = op("INVOKE_DEFAULT")
        except Exception as e:
            self.report({"ERROR"}, f"{self.idname}: {e}")
            return {"CANCELLED"}
        if "CANCELLED" in result:
            self.report({"INFO"}, f"{self.idname} cancelled")
        return {"FINISHED"}


class JEV_OT_copy_operator(Operator):
    bl_idname = "jev.copy_operator"
    bl_label = "Copy Python call"
    bl_description = "Copy the bpy.ops call for this operator to the clipboard"

    idname: StringProperty()

    def execute(self, context):
        context.window_manager.clipboard = f"bpy.ops.{self.idname}()"
        self.report({"INFO"}, f"Copied bpy.ops.{self.idname}()")
        return {"FINISHED"}


class JEV_OT_rebuild_catalog(Operator):
    bl_idname = "jev.rebuild_catalog"
    bl_label = "Rebuild operator catalog"
    bl_description = "Re-scan bpy.ops (after enabling or disabling add-ons)"

    def execute(self, context):
        catalog = cat.get_catalog(force=True)
        n = sum(len(v) for v in catalog.values())
        self.report({"INFO"}, f"{n} operators in {len(catalog)} modules")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class JEV_PT_search(Panel):
    bl_label = "Jev Operator Search"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jev"

    _warmed = False

    def draw(self, context):
        layout = self.layout
        props = context.window_manager.jev_search

        if not JEV_PT_search._warmed:
            JEV_PT_search._warmed = True
            threading.Thread(target=jev_api.warm_up, daemon=True).start()

        row = layout.row(align=True)
        row.prop(props, "query", text="", icon="VIEWZOOM", placeholder="I want to…")
        sub = row.row(align=True)
        sub.enabled = not props.searching
        sub.operator("jev.search", text="", icon="PLAY")

        if props.status:
            icon = "SORTTIME" if props.searching else ("ERROR" if "error" in props.status.lower() or "key" in props.status.lower() else "INFO")
            layout.label(text=props.status, icon=icon)

        if not props.results:
            return

        col = layout.column(align=True)
        for item in props.results:
            box = col.box()
            head = box.row(align=True)
            runnable = _can_run(item.idname, context)
            run = head.row(align=True)
            run.enabled = runnable
            op = run.operator("jev.run_operator", text=item.label, icon="PLAY")
            op.idname = item.idname
            head.label(text=f"{item.score:.0%}")
            cp = head.operator("jev.copy_operator", text="", icon="COPYDOWN")
            cp.idname = item.idname

            sub = box.column(align=True)
            sub.scale_y = 0.8
            sub.label(text=f"bpy.ops.{item.idname}", icon="NONE" if runnable else "LOCKED")
            if item.description:
                sub.label(text=_truncate(item.description, 60))


def _can_run(idname, context):
    try:
        op = _resolve(idname)
        region = _window_region(context.area) if context.area else None
        if region:
            with context.temp_override(region=region):
                return op.poll()
        return op.poll()
    except Exception:
        return False


def _truncate(text, n):
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    JevResultItem,
    JevSearchProps,
    JevPreferences,
    JEV_OT_search,
    JEV_OT_run_operator,
    JEV_OT_copy_operator,
    JEV_OT_rebuild_catalog,
    JEV_PT_search,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.jev_search = bpy.props.PointerProperty(type=JevSearchProps)
    # Deferred: during startup the add-on's preferences don't exist yet when
    # register() runs.
    bpy.app.timers.register(_restore_api_key, first_interval=0.0)


def unregister():
    if bpy.app.timers.is_registered(_restore_api_key):
        bpy.app.timers.unregister(_restore_api_key)
    if bpy.app.timers.is_registered(_poll_results):
        bpy.app.timers.unregister(_poll_results)
    del bpy.types.WindowManager.jev_search
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
