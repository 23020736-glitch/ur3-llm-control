import os
import tempfile

import yaml
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

COLORS = {"red_cube": "1 0 0", "yellow_cube": "1 1 0", "blue_cube": "0 0 1",
          "zone_a": "0 0.8 0", "zone_b": "1 0.5 0", "zone_c": "0.6 0 0.8"}


def sdf(name, size, color, static, collision):
    sx, sy, sz = size
    col = (f"<collision name='c'><geometry><box><size>{sx} {sy} {sz}</size></box></geometry></collision>"
           if collision else "")
    mass = "" if static else ("<inertial><mass>0.05</mass><inertia><ixx>1e-5</ixx><iyy>1e-5</iyy>"
                              "<izz>1e-5</izz></inertia></inertial>")
    return (f"<?xml version='1.0'?><sdf version='1.6'><model name='{name}'><static>{str(static).lower()}</static>"
            f"<link name='l'>{mass}{col}<visual name='v'><geometry><box><size>{sx} {sy} {sz}</size></box></geometry>"
            f"<material><ambient>{color} 1</ambient><diffuse>{color} 1</diffuse></material></visual></link></model></sdf>")


def spawn_scene(context):
    with open(os.path.join(share("ur3_llm_control"), "config", "scene.yaml")) as f:
        sc = yaml.safe_load(f)
    top, cs = sc["table_top_z"], sc["cube_size"]
    tmp = tempfile.mkdtemp(prefix="ur3_scene_")
    items = [("table", sdf("table", (1.2, 1.2, 0.04), "0.6 0.5 0.4", True, True), 0, 0, top - 0.02)]
    for n, (x, y) in sc["objects"].items():
        items.append((n, sdf(n, (cs,) * 3, COLORS[n], False, True), x, y, top + cs / 2 + 0.002))
    for n, (x, y) in {**sc["zones"], **sc["temp_zones"]}.items():
        items.append((n, sdf(n, (0.08, 0.08, 0.002), COLORS.get(n, "0.6 0.6 0.6"), True, False), x, y, top + 0.001))
    nodes = []
    for n, xml, x, y, z in items:
        path = os.path.join(tmp, n + ".sdf")
        with open(path, "w") as f:
            f.write(xml)
        nodes.append(Node(package="gazebo_ros", executable="spawn_entity.py", output="screen",
                          arguments=["-file", path, "-entity", n, "-x", str(x), "-y", str(y), "-z", str(z)]))
    return nodes


def generate_launch_description():
    sim = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        os.path.join(share("ur_simulation_gazebo"), "launch", "ur_sim_control.launch.py")),
        launch_arguments={"ur_type": "ur3e", "launch_rviz": "false"}.items())
    moveit = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        os.path.join(share("ur_moveit_config"), "launch", "ur_moveit.launch.py")),
        launch_arguments={"ur_type": "ur3e", "use_sim_time": "true", "launch_rviz": "true"}.items())
    executor = Node(package="ur3_llm_control", executable="skill_executor", output="screen",
                    parameters=[{"use_sim_time": True}])
    return LaunchDescription([
        sim,
        TimerAction(period=8.0, actions=[OpaqueFunction(function=spawn_scene)]),
        TimerAction(period=12.0, actions=[moveit]),
        TimerAction(period=20.0, actions=[executor]),
    ])
