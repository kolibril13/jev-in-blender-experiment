"""Builds the operator catalog Jev ranks over, straight from bpy.ops.

The catalog is a dict: module name -> list of (idname_py, label, description).
Module descriptions below are hand-written for the built-in modules; anything
else (third-party add-ons) gets an auto-generated one from its operator labels.
"""

import bpy

MODULE_DESCRIPTIONS = {
    "object": "Object mode: add/delete/duplicate/join objects, parenting, apply or clear transforms, origin, modifiers, shading (smooth/flat), convert object type, link or transfer data, hide/show, quick effects, constraints, vertex groups, shape keys",
    "mesh": "Edit mode mesh tools: add primitives (cube, sphere, cylinder, plane...), extrude, bevel, inset, loop cut, subdivide, merge, split, separate, fill, bridge, knife, bisect, dissolve, delete geometry, select by trait/loops/rings/similar, normals, mark seam/sharp, symmetrize, remove doubles",
    "transform": "Move (translate), rotate, scale (resize), shear, shrink/fatten, to sphere, bend, push/pull, edge slide, vertex slide, mirror, snap, randomize, tilt, warp",
    "view3d": "3D viewport: navigation (zoom, pan, orbit, frame selected/all, view axis, camera view, local view), 3D cursor placement, box/circle/lasso select, snap selection/cursor, toggle shading, render border, quad view",
    "uv": "UV editing: unwrap, smart project, cube/cylinder/sphere project, pack islands, mark seams, pin, align, stitch, minimize stretch, average island scale, select islands, reset",
    "sculpt": "Sculpt mode: brush strokes, dynamic topology, masks (box/lasso/expand), face sets, remesh, mesh filter, cloth filter, color filter, sample detail size, symmetrize, trim",
    "paint": "Texture paint, vertex paint and weight paint: brush strokes, fill, sample color, project image, weight tools (smooth, normalize, mirror, levels, quantize), vertex color set, hide/show masks",
    "curve": "Curve edit mode (bezier / nurbs / path): add primitives, handles type, subdivide, cyclic toggle, spline type, extrude, smooth, decimate, tilt, radius, separate, split",
    "curves": "Hair curves object: add empty/random hair, convert to/from particle system, snap to surface, set selection domain, sculpt curves selection",
    "armature": "Armature edit mode: add/extrude/subdivide bones, parent/unparent, roll, symmetrize, auto-name, flip names, split, dissolve, bone layers/collections",
    "pose": "Pose mode: clear transforms, rest pose, copy/paste/flip pose, IK add/clear, propagate, push/relax pose, breakdowner, bone groups, select hierarchy",
    "anim": "Animation keyframes: insert/delete/clear keyframes, keying sets, add/remove drivers, previews, change frame, channel operations, copy/paste drivers",
    "graph": "Graph editor (F-curves): select/edit keyframes, interpolation, handle types, easing, extrapolation, F-curve modifiers, bake, smooth, decimate, clean, view all/selected",
    "action": "Dope sheet / action editor: keyframes select/edit/duplicate, interpolation, snap, mirror, markers, push down action, stash, layer",
    "nla": "Nonlinear animation (NLA) editor: add/delete strips, tracks, action strips, transitions, meta strips, bake, tweak mode, mute",
    "node": "Node editors (shader, geometry nodes, compositor): add/delete/duplicate/link/mute nodes, group/ungroup, frames, join, hide sockets, node previews, viewer, backdrop, find node",
    "sequencer": "Video sequence editor: add strips (movie, image, sound, color, text, effect), split/cut, speed, transitions, meta strips, mute, lock, snap, gap remove, render strip",
    "clip": "Movie clip editor / motion tracking: markers, track, solve camera, stabilization, detect features, set orientation, reconstruction",
    "image": "Image editor: new/open/save/save as/reload/pack image, render result view, resize, invert, flip, external editor, sample color, tiles",
    "render": "Rendering: render image or animation, view render, play rendered animation, render presets, viewport (OpenGL) render, shutter curve preset",
    "scene": "Scene management: new/delete scene, view layers, render layers, light cache bake, freestyle line sets, keying set paths, delete gpencil",
    "screen": "Screen / window layout: split/join/swap areas, fullscreen area, frame jumping, animation playback (play/pause/step), screenshot, header/footer toggles, region toggles",
    "wm": "Window manager and files: new/open/save/recover .blend, import/export (OBJ, STL, PLY, USD, Alembic, FBX...), append/link, preferences, undo/redo, menu search, quit, open URL, keyconfig, drivers, extensions, batch rename",
    "file": "File browser: navigate directories, bookmarks, filters, select files, new folder, refresh, hide dot files, execute",
    "outliner": "Outliner: expand/collapse, select hierarchy, collections (new/delete/exclude/hide), orphan data purge, ID operations, unlink, delete hierarchy, show/hide",
    "material": "Material slots: new material, copy/paste material",
    "texture": "Textures: new texture, texture slots",
    "world": "World: new world",
    "constraint": "Object and bone constraints: add, delete, apply, move up/down, set inverse (child of), follow path animate, limit distance reset, stretch to reset",
    "collection": "Collections: create new collection, link/unlink objects to collection, remove from collection, exclude",
    "rigidbody": "Rigid body physics: add/remove rigid body, constraints, bake to keyframes, calculate mass, change shape, connect",
    "cloth": "Cloth physics presets",
    "fluid": "Fluid simulation: bake/free data, mesh, noise, particles, guides, preset",
    "particle": "Particle systems: new/copy, hair editing (comb, cut, puff, weight), connect/disconnect hair, rekey, remove doubles, duplicate system, edited copy",
    "dpaint": "Dynamic paint: add/remove canvas or brush, bake, output surface",
    "mask": "Mask editor (compositing/tracking masks): add splines, points, feather, handle types, parent, shape keys, hide/reveal",
    "text": "Text editor: new/open/save/reload text block, run script, find/replace, cursor and selection movement, indent, comment, autocomplete, line break",
    "console": "Python console: execute, autocomplete, history, copy/paste, clear, indent, banner",
    "info": "Info editor: select/delete/copy reports",
    "preferences": "Preferences: add-ons install/enable/disable, keymaps import/export, themes, studio lights, app templates, asset libraries, extension repositories, auto-run scripts",
    "extensions": "Extensions: install/update/remove extensions, sync repositories, enable/disable, drop file, repo settings",
    "asset": "Asset browser: mark/clear asset, catalogs, tags, library refresh, open containing blend file, assign action",
    "font": "Text object (3D font) edit mode: type text, select, change case, bold/italic/underline style, text box add/remove, cursor movement, open font",
    "lattice": "Lattice edit mode: select, flip, make regular",
    "mball": "Metaball edit mode: select, hide/reveal, delete, duplicate",
    "marker": "Timeline markers: add, delete, move, rename, duplicate, bind camera to marker, select",
    "brush": "Brush data: add, reset, scale size, curve preset, stencil control, sculpt curves brush",
    "palette": "Color palettes: new palette, add/remove color, sort, join",
    "paintcurve": "Paint curves: add, draw, select, slide, delete points, cursor",
    "geometry": "Geometry attributes and color attributes: add/remove/convert attribute, render color, execute node group, randomize",
    "grease_pencil": "Grease Pencil (2D drawing/animation): draw, edit strokes, layers, frames, interpolate, sculpt strokes, primitives, weight paint, trace image, materials, bake",
    "gpencil": "Legacy Grease Pencil (annotations): annotation draw, add/remove annotation layers",
    "spreadsheet": "Spreadsheet editor: fit column, toggle pin, add/remove row filter",
    "sound": "Sound: open sound file, pack/unpack, mixdown, update animation flags, bake sound to F-curve",
    "camera": "Camera presets",
    "cycles": "Cycles: denoise animation, merge images, use shading nodes",
    "ed": "Undo / redo / undo history, flush edits, library reload/relocate",
    "buttons": "Properties editor: toggle pin, context menu, start filter, file/directory browse, clear filter",
    "ui": "UI utilities: copy data path, copy python command, reset to default, add/remove driver from UI, eyedroppers (color, id, depth), jump to target, view drop, assign to collection",
    "view2d": "2D editor navigation: pan, zoom in/out, scroll, reset view, scroller, edge pan",
    "workspace": "Workspaces: add, delete, duplicate, reorder to front/back, append from file, scene pin",
    "surface": "NURBS surface primitives: add circle, curve, cylinder, sphere, torus, surface patch",
    "pointcloud": "Point cloud editing",
    "poselib": "Pose library: create/apply/blend pose assets, copy/paste as asset",
    "ptcache": "Point cache: bake all/from cache, free bake, add/remove cache",
    "cachefile": "Alembic / USD cache files: open, reload, layer add/remove/move",
    "export_scene": "Export scene to FBX / glTF",
    "import_scene": "Import scene from FBX / glTF",
    "import_curve": "Import SVG as curves",
    "export_anim": "Export animation to BVH",
    "import_anim": "Import BVH motion capture",
    "boid": "Boid particle rules and states",
    "sculpt_curves": "Sculpt curves (hair): select grow, random mask, min distance edit",
    "script": "Scripts: reload scripts, execute preset, run Python file",
    "gizmogroup": "Gizmo group tweak",
}

# Modules whose operators shouldn't be offered as "the thing you want to do"
# (internal helpers, drag/drop plumbing). Add to taste.
SKIP_MODULES = {"gizmogroup", "uilist"}

_CATALOG = None


def _auto_description(ops, limit=10):
    labels = [label for _, label, _ in ops[:limit]]
    return "Operators: " + ", ".join(labels)


def build_catalog():
    """Return {module: [(idname, label, description), ...]} for every registered operator."""
    catalog = {}
    for mod_name in dir(bpy.ops):
        if mod_name.startswith("_") or mod_name in SKIP_MODULES:
            continue
        mod = getattr(bpy.ops, mod_name)
        ops = []
        for op_name in dir(mod):
            op = getattr(mod, op_name)
            try:
                rna = op.get_rna_type()
            except Exception:
                continue
            label = rna.name or op_name.replace("_", " ").title()
            ops.append((op.idname_py(), label, rna.description or ""))
        if ops:
            catalog[mod_name] = ops
    return catalog


def get_catalog(force=False):
    global _CATALOG
    if _CATALOG is None or force:
        _CATALOG = build_catalog()
    return _CATALOG


def module_criteria(catalog):
    """Choice criteria for the module-level question: module -> description."""
    criteria = {}
    for mod_name, ops in catalog.items():
        desc = MODULE_DESCRIPTIONS.get(mod_name)
        criteria[mod_name] = desc if desc else _auto_description(ops)
    return criteria


DESCRIPTION_CHARS = 90  # longer descriptions are cut; the first clause carries the meaning


def operator_criteria(ops):
    """Choice criteria for one operator list: idname -> 'Label: description'."""
    criteria = {}
    for idname, label, desc in ops:
        if len(desc) > DESCRIPTION_CHARS:
            desc = desc[: DESCRIPTION_CHARS - 1].rstrip() + "…"
        criteria[idname] = f"{label}: {desc}" if desc else label
    return criteria


def lookup(idname):
    for ops in get_catalog().values():
        for entry in ops:
            if entry[0] == idname:
                return entry
    return None
