## Tải code về workspace mới

Mở terminal mới và chạy khối này:

bash
mkdir -p ~/ws_test/src && cd ~/ws_test/src
git clone -b humble https://github.com/UniversalRobots/Universal_Robots_ROS2_Gazebo_Simulation.git
git clone https://github.com/23020736-glitch/ur3-llm-control.git ur3_llm_control
ls ur3_llm_control ur3_llm_control/config

Bạn cần thấy launch, config, package.xml, setup.py, README.md và trong config có prompt_template.txt, scene.yaml, student_config.yaml. Nếu thiếu file nào thì repo GitHub thiếu file đó, bạn quay lại đẩy bổ sung.
## Build
bash
cd ~/ws_test
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build
source install/setup.bash
## Chạy thử

Terminal 1 (đã source ~/ws_test):

bash
export PYTHONUNBUFFERED=1
ros2 launch ur3_llm_control llm_robot.launch.py

Chờ khoảng 30 giây. Tuỳ chọn, xoá ground_plane để thấy bàn:

bash
ros2 service call /delete_entity gazebo_msgs/srv/DeleteEntity "{name: 'ground_plane'}"

Terminal 2 (mở mới, nhớ source ~/ws_test/install/setup.bash, 3 biến NINEROUTER_* đã có sẵn từ .bashrc):

bash
source /opt/ros/humble/setup.bash && source ~/ws_test/install/setup.bash
ros2 run ur3_llm_control llm_planner

Gõ thử:

Please put the red cube in zone A.
Arrange all objects according to my student ID.
move the green cube to zone Z

**Sinh viên:** ( – **MSSV:** 23020736 → P = 36 mod 6 = **0**
→ **Zone A = Red, Zone B = Yellow, Zone C = Blue** (khai báo trong `config/student_config.yaml`).

## Cài đặt (Ubuntu 22.04, ROS 2 Humble)
```bash
sudo apt install ros-humble-ur ros-humble-ur-simulation-gazebo ros-humble-ur-moveit-config \
                 ros-humble-moveit ros-humble-gazebo-ros-pkgs
mkdir -p ~/ws/src && cp -r ur3_llm_control ~/ws/src/ && cd ~/ws
colcon build --packages-select ur3_llm_control && source install/setup.bash
```
## 9Router
Bật 9Router, tạo provider/combo, rồi:
```bash
export NINEROUTER_BASE_URL=http://localhost:20128/v1   
export NINEROUTER_API_KEY=<key trong dashboard>
export NINEROUTER_MODEL=<tên model hoặc combo>
```

## Chạy
```bash
# Terminal 1: Gazebo + MoveIt + executor
ros2 launch ur3_llm_control llm_robot.launch.py
# Terminal 2: planner (nhập lệnh trực tiếp)
ros2 run ur3_llm_control llm_planner
```
Ví dụ: `Please put the red cube in zone B.` · `Hãy lấy khối màu vàng và đặt nó vào ô A.` ·
`Move the blue cube to zone C.` · `Arrange all objects according to my student ID.`
