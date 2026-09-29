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
# Node.js >= 18 (ví dụ bằng nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20 && nvm use 20

npm install -g 9router
9router          # giữ cửa sổ này mở; dashboard: http://localhost:20128/dashboard
## Trong dashboard: mở Providers và kết nối một provider (ví dụ OpenCode Free – không cần đăng nhập), vào Endpoint & Key → Create Key để lấy API key. Rồi đặt biến môi trường (terminal sẽ chạy planner):

bash
export NINEROUTER_BASE_URL=http://localhost:20128/v1
export NINEROUTER_API_KEY=sk-...                       # key của bạn (KHÔNG commit lên git)
export NINEROUTER_MODEL=oc/muse-spark-1.3-contributor-free   # tên model trong dashboard


## Chạy

# Terminal 1 – mô phỏng + MoveIt 2 + executor:
source /opt/ros/humble/setup.bash && source ~/ws/install/setup.bash
export PYTHONUNBUFFERED=1
ros2 launch ur3_llm_control llm_robot.launch.py
ros2 service call /delete_entity gazebo_msgs/srv/DeleteEntity "{name: 'ground_plane'}"
# Terminal 2 – nhập lệnh tự nhiên
source /opt/ros/humble/setup.bash && source ~/ws/install/setup.bash
ros2 run ur3_llm_control llm_planner
```
Mức	Lệnh
Cơ bản	Please put the red cube in zone A.
Cơ bản (tiếng Việt)	Hãy lấy khối màu vàng và đặt nó vào ô B.
Cơ bản	Move the blue cube to zone C.
Nâng cao	Arrange all objects according to my student ID.
Lệnh sai (bị từ chối)	move the green cube to zone Z
