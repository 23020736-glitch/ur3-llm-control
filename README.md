

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
