"""Node Skill Executor: nhan /llm_plan, validate lai, chay tung skill qua MoveIt 2, in ket qua."""
import json
import threading

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import String

from ur3_llm_control.robot_skills import SUCCESS, RobotSkills
from ur3_llm_control.task_validator import load_config, validate_plan


class SkillExecutor(Node):
    def __init__(self):
        super().__init__("skill_executor")
        scene, _ = load_config()
        self.objects = list(scene["objects"])
        self.zones = list(scene["zones"]) + list(scene["temp_zones"])
        cbg = ReentrantCallbackGroup()
        self.skills = RobotSkills(self, scene, cbg)
        self.busy = False
        self.state_pub = self.create_publisher(
            String, "world_state", QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(String, "llm_plan", self.on_plan, 10, callback_group=cbg)
        self.publish_state()

    def publish_state(self):
        self.state_pub.publish(String(data=json.dumps(self.skills.loc)))

    def on_plan(self, msg):
        if self.busy:
            print("Robot dang ban, bo qua ke hoach moi.")
            return
        self.busy = True
        threading.Thread(target=self.run, args=(msg.data,), daemon=True).start()

    def run(self, raw):
        try:
            data = json.loads(raw)
            errs = validate_plan(data, self.objects, self.zones)  # phong thu lop 2
            if errs:
                print("EXECUTOR REJECTED PLAN:", errs)
                return
            print("\nEXECUTION:")
            for s in data["plan"]:
                args = [s[k] for k in ("object", "zone") if k in s]
                label = f"{s['skill']}({', '.join(args)})"
                status = getattr(self.skills, s["skill"])(*args)
                print(f"{label} {'.' * max(2, 36 - len(label))} {status}")
                self.publish_state()
                if status != SUCCESS:
                    print("\nTASK FAILED\n")
                    return
            print("\nTASK SUCCESS\n")
        finally:
            self.busy = False


def main():
    rclpy.init()
    node = SkillExecutor()
    ex = MultiThreadedExecutor(num_threads=4)
    ex.add_node(node)
    ex.spin()
    rclpy.shutdown()
