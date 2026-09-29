"""Node LLM Planner: cau lenh tu nhien -> JSON plan -> validate -> publish /llm_plan."""
import json
import os
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String

from ur3_llm_control.llm_client import chat
from ur3_llm_control.task_validator import (
    extract_json, load_config, resolve_conflicts, student_targets, validate_plan)

SKILL_DOC = """pick(object)            - pick up an object from the table or a zone
place(object, zone)     - place the currently held object into a zone
home()                  - return the arm to the home pose
move_above(object)      - move the gripper above an object
move_to_zone(zone)      - move the gripper above a zone
open_gripper() / close_gripper()"""


class LLMPlanner(Node):
    def __init__(self):
        super().__init__("llm_planner")
        scene, student = load_config()
        self.objects = list(scene["objects"])
        self.zones = list(scene["zones"])
        self.temp_zones = list(scene["temp_zones"])
        self.p, self.targets = student_targets(student["student_id"])
        self.student = student
        self.state = {o: "table" for o in self.objects}
        self.pub = self.create_publisher(String, "llm_plan", 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, "world_state", self.on_state, qos)
        self.create_subscription(String, "user_command", lambda m: self.handle_command(m.data), 10)

    def on_state(self, msg):
        self.state = json.loads(msg.data)

    def system_prompt(self):
        from ament_index_python.packages import get_package_share_directory
        path = os.path.join(get_package_share_directory("ur3_llm_control"), "config", "prompt_template.txt")
        with open(path, encoding="utf-8") as f:
            t = f.read()
        mapping = "\n".join(f"{z} -> {o}" for z, o in self.targets.items())
        for k, v in {"SKILLS": SKILL_DOC, "OBJECTS": ", ".join(self.objects), "ZONES": ", ".join(self.zones),
                     "STATE": json.dumps(self.state), "STUDENT_NAME": str(self.student["student_name"]),
                     "STUDENT_ID": str(self.student["student_id"]), "MAPPING": mapping}.items():
            t = t.replace(f"<<{k}>>", v)
        return t

    @staticmethod
    def fmt(s):
        args = [s[k] for k in ("object", "zone") if k in s]
        return f"{s['skill']}({', '.join(args)})" + ("   [auto: clear target zone]" if s.get("auto") else "")

    def handle_command(self, text):
        print(f"\nUSER COMMAND:\n{text}\n")
        msgs = [{"role": "system", "content": self.system_prompt()},
                {"role": "user", "content": text}]
        errs = []
        for _ in range(2):  # 1 lan thu lai kem thong bao loi
            try:
                reply = chat(msgs)
            except Exception as e:
                print(f"LLM ERROR: {e}")
                return
            try:
                data = extract_json(reply)
            except ValueError as e:
                errs = [str(e)]
            else:
                if data.get("error") and not data.get("plan"):
                    print(f"LLM CANNOT PLAN: {data['error']}")
                    return
                errs = validate_plan(data, self.objects, self.zones)
                if not errs:
                    break
            msgs += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": "Invalid plan: " + "; ".join(errs) +
                      ". Return a corrected JSON plan only."}]
        else:
            print("PLAN REJECTED (not executed):")
            for e in errs:
                print("  -", e)
            return
        try:
            steps = resolve_conflicts(data["plan"], self.state, self.temp_zones)
        except ValueError as e:
            print(f"PLAN REJECTED: {e}")
            return
        print("LLM PLAN:")
        for s in steps:
            print("    " + self.fmt(s))
        self.pub.publish(String(data=json.dumps({"plan": steps, "command": text})))


def main():
    rclpy.init()
    node = LLMPlanner()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    print(f"Student {node.student['student_id']}: P={node.p}, target={node.targets}")
    print("Nhap lenh (Ctrl+D de thoat):")
    try:
        while True:
            cmd = input("> ").strip()
            if cmd:
                node.handle_command(cmd)
    except (EOFError, KeyboardInterrupt):
        pass
    rclpy.shutdown()
