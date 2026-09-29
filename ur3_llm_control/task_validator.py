"""Validator + xu ly xung dot zone. Khong phu thuoc ROS de test duoc doc lap."""
import json
import os
import re

import yaml

# skill -> danh sach tham so bat buoc
ALLOWED_SKILLS = {
    "home": [],
    "pick": ["object"],
    "place": ["object", "zone"],
    "move_above": ["object"],
    "move_to_zone": ["zone"],
    "open_gripper": [],
    "close_gripper": [],
}

# P = XX mod 6 -> (mau zone A, mau zone B, mau zone C)
COLORS_BY_P = {
    0: ("red", "yellow", "blue"), 1: ("red", "blue", "yellow"),
    2: ("yellow", "red", "blue"), 3: ("yellow", "blue", "red"),
    4: ("blue", "red", "yellow"), 5: ("blue", "yellow", "red"),
}


def student_targets(student_id):
    p = int(str(student_id)[-2:]) % 6
    a, b, c = COLORS_BY_P[p]
    return p, {"zone_a": f"{a}_cube", "zone_b": f"{b}_cube", "zone_c": f"{c}_cube"}


def load_config(share_dir=None):
    if share_dir is None:
        from ament_index_python.packages import get_package_share_directory
        share_dir = get_package_share_directory("ur3_llm_control")
    with open(os.path.join(share_dir, "config", "scene.yaml")) as f:
        scene = yaml.safe_load(f)
    with open(os.path.join(share_dir, "config", "student_config.yaml")) as f:
        student = yaml.safe_load(f)
    return scene, student


def extract_json(text):
    t = re.sub(r"```(?:json)?", "", text)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("no JSON object in LLM reply")
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"bad JSON: {e}")


def validate_plan(data, objects, zones):
    """Tra ve list loi (rong = hop le). Kiem tra skill/object/zone va trang thai tay gap."""
    errs = []
    steps = data.get("plan") if isinstance(data, dict) else None
    if not isinstance(steps, list) or not steps:
        return ["'plan' must be a non-empty list"]
    held = None
    for i, s in enumerate(steps, 1):
        if not isinstance(s, dict) or s.get("skill") not in ALLOWED_SKILLS:
            errs.append(f"step {i}: skill not allowed: {s.get('skill') if isinstance(s, dict) else s}")
            continue
        for p in ALLOWED_SKILLS[s["skill"]]:
            if p not in s:
                errs.append(f"step {i}: {s['skill']} missing '{p}'")
        if "object" in s and s["object"] not in objects:
            errs.append(f"step {i}: unknown object '{s['object']}'")
        if "zone" in s and s["zone"] not in zones:
            errs.append(f"step {i}: unknown zone '{s['zone']}'")
        if s["skill"] == "pick":
            if held:
                errs.append(f"step {i}: pick while already holding {held}")
            held = s.get("object")
        elif s["skill"] == "place":
            if held != s.get("object"):
                errs.append(f"step {i}: place {s.get('object')} but holding {held}")
            held = None
    return errs


def resolve_conflicts(steps, state, temp_zones):
    """Neu zone dich dang bi vat khac chiem -> chen pick/place chuyen vat do sang zone tam.
    state: {object: 'table' | zone_name}. Cac buoc chen them co co 'auto': True."""
    st = dict(state)
    out = []
    for i, s in enumerate(steps):
        if s["skill"] == "pick":
            tz = next((t["zone"] for t in steps[i + 1:]
                       if t["skill"] == "place" and t["object"] == s["object"]), None)
            occ = [o for o, l in st.items() if l == tz and o != s["object"]] if tz else []
            if occ:
                free = [t for t in temp_zones if t not in st.values()]
                if not free:
                    raise ValueError("no free temporary zone")
                o, t = occ[0], free[0]
                out += [{"skill": "pick", "object": o, "auto": True},
                        {"skill": "place", "object": o, "zone": t, "auto": True}]
                st[o] = t
            st[s["object"]] = "held"
        elif s["skill"] == "place":
            st[s["object"]] = s["zone"]
        out.append(s)
    return out
