"""Robot skills chay qua MoveIt 2 (action MoveGroup / ExecuteTrajectory, service Cartesian & PlanningScene).
Khong co code nao sinh joint trajectory tu LLM: chi co cac skill co tham so object/zone."""
import math
import time

from geometry_msgs.msg import Pose
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import (AttachedCollisionObject, CollisionObject, Constraints,
                             JointConstraint, MoveItErrorCodes, OrientationConstraint,
                             PlanningScene, PositionConstraint)
from moveit_msgs.srv import ApplyPlanningScene, GetCartesianPath
from rclpy.action import ActionClient
from shape_msgs.msg import SolidPrimitive
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool

try:
    from gazebo_msgs.srv import DeleteEntity, SpawnEntity
except ImportError:  # gazebo_msgs la tuy chon
    DeleteEntity = SpawnEntity = None

SUCCESS = "SUCCESS"
FAILED = "FAILED"
INVALID_OBJECT = "INVALID_OBJECT"
INVALID_ZONE = "INVALID_ZONE"
PLANNING_FAILED = "PLANNING_FAILED"


class RobotSkills:
    def __init__(self, node, scene, cbg=None):
        self.n, self.s = node, scene
        self.frame, self.ee = scene["frame_id"], scene["ee_link"]
        self.group = scene["group_name"]
        self.tcp, self.appr = scene["tcp_offset"], scene["approach_height"]
        self.size = scene["cube_size"]
        self.cube_z = scene["table_top_z"] + self.size / 2
        self.vel = scene.get("velocity_scaling", 0.2)
        self.zones = {**scene["zones"], **scene["temp_zones"]}
        self.pos = {k: [v[0], v[1], self.cube_z] for k, v in scene["objects"].items()}
        self.loc = {k: "table" for k in self.pos}
        self.held = None
        self.ready = False
        self.mg = ActionClient(node, MoveGroup, "move_action", callback_group=cbg)
        self.ex = ActionClient(node, ExecuteTrajectory, "execute_trajectory", callback_group=cbg)
        self.cart = node.create_client(GetCartesianPath, "compute_cartesian_path", callback_group=cbg)
        self.aps = node.create_client(ApplyPlanningScene, "apply_planning_scene", callback_group=cbg)
        self.gz_del = (node.create_client(DeleteEntity, "/delete_entity", callback_group=cbg)
                       if DeleteEntity else None)
        self.gz_spawn = (node.create_client(SpawnEntity, "/spawn_entity", callback_group=cbg)
                         if SpawnEntity else None)
        self.grip_pub = node.create_publisher(Bool, "gripper_close", 10)
        self.js = {}
        node.create_subscription(JointState, "joint_states", self._on_js, 10, callback_group=cbg)

    # ---------- ha tang ----------
    def _wait(self, fut, timeout):
        t0 = time.time()
        while not fut.done():
            if time.time() - t0 > timeout:
                return False
            time.sleep(0.02)
        return True

    def _pose(self, xyz):
        p = Pose()
        p.position.x, p.position.y, p.position.z = map(float, xyz)
        p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w = self.s["grasp_orientation"]
        return p

    def _box(self, name, size, xyz, frame=None, op=CollisionObject.ADD):
        co = CollisionObject()
        co.id, co.operation = name, op
        co.header.frame_id = frame or self.frame
        p = Pose()
        p.position.x, p.position.y, p.position.z = map(float, xyz)
        p.orientation.w = 1.0
        co.primitives = [SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(map(float, size)))]
        co.primitive_poses = [p]
        return co

    def _apply(self, world=(), attached=()):
        ps = PlanningScene()
        ps.is_diff = True
        ps.world.collision_objects = list(world)
        ps.robot_state.is_diff = True
        ps.robot_state.attached_collision_objects = list(attached)
        fut = self.aps.call_async(ApplyPlanningScene.Request(scene=ps))
        if not self._wait(fut, 5.0):
            print("    apply_planning_scene: TIMEOUT", flush=True)
            return False
        ok = fut.result().success
        if not ok:
            print("    apply_planning_scene: success=False", flush=True)
        return ok

    def ensure_ready(self):
        if self.ready:
            return True
        if not (self.mg.wait_for_server(10.0) and self.aps.wait_for_service(10.0)
                and self.cart.wait_for_service(10.0) and self.ex.wait_for_server(10.0)):
            return False
        top = self.s["table_top_z"]
        objs = [self._box("table", (1.2, 1.2, 0.04), (0, 0, top - 0.02))]
        objs += [self._box(k, (self.size,) * 3, v) for k, v in self.pos.items()]
        self.ready = self._apply(world=objs)
        return self.ready

    # ---------- chuyen dong (deu qua MoveIt 2) ----------
    def _run_goal(self, goal):
        """Lap ke hoach co thu lai: RRTConnect ngau nhien, doi khi duong di sinh ra khong hop le."""
        r = FAILED
        for attempt in range(3):
            r = self._run_goal_once(goal)
            if r == SUCCESS or self.last_code not in (-1, -2):
                return r
            if attempt < 2:
                print(f"    plan khong hop le (code {self.last_code}), thu lai {attempt + 2}/3", flush=True)
        return r

    def _run_goal_once(self, goal):
        self.last_code = 0
        fut = self.mg.send_goal_async(goal)
        if not self._wait(fut, 10.0) or not fut.result().accepted:
            return FAILED
        rf = fut.result().get_result_async()
        if not self._wait(rf, 90.0):
            return FAILED
        code = rf.result().result.error_code.val
        self.last_code = code
        if code == MoveItErrorCodes.SUCCESS:
            return SUCCESS
        return PLANNING_FAILED if code == MoveItErrorCodes.PLANNING_FAILED else FAILED

    def _base_goal(self):
        g = MoveGroup.Goal()
        r = g.request
        r.group_name = self.group
        r.num_planning_attempts = 10
        r.allowed_planning_time = 5.0
        r.max_velocity_scaling_factor = self.vel
        r.max_acceleration_scaling_factor = self.vel
        g.planning_options.plan_only = False
        g.planning_options.planning_scene_diff.is_diff = True
        return g

    def _move_pose(self, xyz):
        g = self._base_goal()
        pose = self._pose(xyz)
        pc = PositionConstraint()
        pc.header.frame_id, pc.link_name, pc.weight = self.frame, self.ee, 1.0
        pc.constraint_region.primitives = [SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.005])]
        pc.constraint_region.primitive_poses = [pose]
        oc = OrientationConstraint()
        oc.header.frame_id, oc.link_name, oc.weight = self.frame, self.ee, 1.0
        oc.orientation = pose.orientation
        oc.absolute_x_axis_tolerance = oc.absolute_y_axis_tolerance = oc.absolute_z_axis_tolerance = 0.05
        c = Constraints()
        c.position_constraints, c.orientation_constraints = [pc], [oc]
        g.request.goal_constraints = [c]
        return self._run_goal(g)

    def _move_joints(self, joints):
        g = self._base_goal()
        c = Constraints()
        for n, v in zip(self.s["joint_names"], joints):
            jc = JointConstraint()
            jc.joint_name, jc.position, jc.weight = n, float(v), 1.0
            jc.tolerance_above = jc.tolerance_below = 0.01
            c.joint_constraints.append(jc)
        g.request.goal_constraints = [c]
        return self._run_goal(g)

    def _cartesian(self, xyz):
        """Di thang (ha xuong/nang len) qua MoveIt compute_cartesian_path; cho phep cham vat."""
        req = GetCartesianPath.Request()
        req.header.frame_id = self.frame
        req.start_state.is_diff = True
        req.group_name, req.link_name = self.group, self.ee
        req.waypoints = [self._pose(xyz)]
        req.max_step, req.jump_threshold, req.avoid_collisions = 0.005, 0.0, False
        fut = self.cart.call_async(req)
        if not self._wait(fut, 10.0):
            return FAILED
        res = fut.result()
        if res.fraction < 0.95:
            return PLANNING_FAILED
        self._unwrap(res.solution)
        goal = ExecuteTrajectory.Goal()
        goal.trajectory = res.solution
        gf = self.ex.send_goal_async(goal)
        if not self._wait(gf, 10.0) or not gf.result().accepted:
            return FAILED
        rf = gf.result().get_result_async()
        if not self._wait(rf, 60.0):
            return FAILED
        return SUCCESS if rf.result().result.error_code.val == MoveItErrorCodes.SUCCESS else FAILED

    def _on_js(self, msg):
        for n, v in zip(msg.name, msg.position):
            self.js[n] = v

    def _unwrap(self, traj):
        """Cong/tru 2*pi cho tung khop de quy dao lien mach voi vi tri that (tranh loi wrap-around)."""
        jt = traj.joint_trajectory
        prev = [self.js.get(n) for n in jt.joint_names]
        for pt in jt.points:
            pos = list(pt.positions)
            for k, v in enumerate(pos):
                if prev[k] is not None:
                    v -= 2 * math.pi * round((v - prev[k]) / (2 * math.pi))
                pos[k] = v
                prev[k] = v
            pt.positions = pos

    def _grip(self, close):
        self.grip_pub.publish(Bool(data=close))  # noi vao gripper that/sim neu co
        time.sleep(0.5)

    def _attach(self, obj):
        aco = AttachedCollisionObject()
        aco.link_name, aco.touch_links = self.ee, self.s["touch_links"]
        aco.object = self._box(obj, (self.size,) * 3, (0, 0, self.tcp), frame=self.ee)
        rm = CollisionObject()
        rm.id, rm.operation = obj, CollisionObject.REMOVE
        rm.header.frame_id = self.frame
        return SUCCESS if self._apply(attached=[aco]) else FAILED

    def _detach(self, obj, xyz):
        aco = AttachedCollisionObject()
        aco.link_name = self.ee
        aco.object.id, aco.object.operation = obj, CollisionObject.REMOVE
        ok = self._apply(world=[self._box(obj, (self.size,) * 3, xyz)], attached=[aco])
        return SUCCESS if ok else FAILED

    CUBE_COLORS = {"red_cube": "1 0 0", "yellow_cube": "1 1 0", "blue_cube": "0 0 1"}

    def _respawn(self, obj, xyz, collision):
        """Dat lai khoi trong Gazebo: spawn ban MOI (ten moi) truoc, thanh cong roi moi xoa ban cu."""
        if not (self.gz_del and self.gz_spawn and self.gz_del.service_is_ready()
                and self.gz_spawn.service_is_ready()):
            print("    GAZEBO: delete/spawn service khong san sang", flush=True)
            return SUCCESS
        names = self.__dict__.setdefault("gz_names", {})
        cnt = self.__dict__.get("gz_cnt", 0) + 1
        self.__dict__["gz_cnt"] = cnt
        old = names.get(obj, obj)
        new_name = f"{obj}_v{cnt}"
        sz = self.size
        col = (f"<collision name='c'><geometry><box><size>{sz} {sz} {sz}</size></box></geometry></collision>"
               if collision else "")
        color = self.CUBE_COLORS.get(obj, "0.5 0.5 0.5")
        xml = (f"<?xml version='1.0'?><sdf version='1.6'><model name='{new_name}'><static>true</static>"
               f"<link name='l'>{col}<visual name='v'><geometry><box><size>{sz} {sz} {sz}</size></box></geometry>"
               f"<material><ambient>{color} 1</ambient><diffuse>{color} 1</diffuse></material></visual></link>"
               f"</model></sdf>")
        req = SpawnEntity.Request()
        req.name, req.xml, req.reference_frame = new_name, xml, "world"
        p = Pose()
        p.position.x, p.position.y, p.position.z = map(float, xyz)
        p.orientation.w = 1.0
        req.initial_pose = p
        f = self.gz_spawn.call_async(req)
        if not self._wait(f, 8.0):
            print(f"    GAZEBO: spawn {new_name} TIMEOUT (giu nguyen {old})", flush=True)
            return FAILED
        res = f.result()
        if not res.success:
            print(f"    GAZEBO: spawn {new_name} loi: {res.status_message} (giu nguyen {old})", flush=True)
            return FAILED
        names[obj] = new_name
        f = self.gz_del.call_async(DeleteEntity.Request(name=old))
        self._wait(f, 3.0)
        return SUCCESS

    def _hover(self, obj, xyz):
        return self._respawn(obj, xyz, False)   # khoi "dang duoc cam": khong va cham

    def _teleport(self, obj, xyz):
        return self._respawn(obj, xyz, True)    # khoi dat xuong: co va cham

    def _seq(self, *steps):
        for i, st in enumerate(steps, 1):
            r = st()
            print(f"    step {i}/{len(steps)}: {r}", flush=True)
            if r != SUCCESS:
                return r
        return SUCCESS

    # ---------- SKILLS ----------
    def home(self):
        if not self.ensure_ready():
            return FAILED
        return self._move_joints(self.s["home_joints"])

    def open_gripper(self):
        self._grip(False)
        return SUCCESS

    def close_gripper(self):
        self._grip(True)
        return SUCCESS

    def move_above(self, obj):
        if obj not in self.pos:
            return INVALID_OBJECT
        if not self.ensure_ready():
            return FAILED
        x, y, z = self.pos[obj]
        return self._move_pose([x, y, z + self.tcp + self.appr])

    def move_to_zone(self, zone):
        if zone not in self.zones:
            return INVALID_ZONE
        if not self.ensure_ready():
            return FAILED
        x, y = self.zones[zone]
        return self._move_pose([x, y, self.cube_z + self.tcp + self.appr])

    def pick(self, obj):
        if obj not in self.pos:
            return INVALID_OBJECT
        if self.held or not self.ensure_ready():
            return FAILED
        x, y, z = self.pos[obj]
        grasp, pre = z + self.tcp, z + self.tcp + self.appr
        r = self._seq(lambda: self.open_gripper(), lambda: self._move_pose([x, y, pre]),
                      lambda: self._cartesian([x, y, grasp]), lambda: self._attach(obj),
                      lambda: self.close_gripper(), lambda: self._cartesian([x, y, pre]),
                      lambda: self._hover(obj, [x, y, z + self.appr]))
        if r == SUCCESS:
            self.held, self.loc[obj] = obj, "held"
        return r

    def place(self, obj, zone):
        if obj not in self.pos:
            return INVALID_OBJECT
        if zone not in self.zones:
            return INVALID_ZONE
        if self.held != obj or not self.ensure_ready():
            return FAILED
        x, y = self.zones[zone]
        z = self.cube_z
        grasp, pre = z + self.tcp + 0.005, z + self.tcp + self.appr
        r = self._seq(lambda: self._move_pose([x, y, pre]),
                      lambda: self._hover(obj, [x, y, z + self.appr]),
                      lambda: self._cartesian([x, y, grasp]),
                      lambda: self._hover(obj, [x, y, z + 0.005]),
                      lambda: self._detach(obj, [x, y, z]), lambda: self.open_gripper(),
                      lambda: self._cartesian([x, y, pre]))
        if r == SUCCESS:
            self.pos[obj], self.loc[obj], self.held = [x, y, z], zone, None
            self._teleport(obj, [x, y, z])
        return r
