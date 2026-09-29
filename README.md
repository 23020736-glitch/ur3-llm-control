# ur3_llm_control – Điều khiển UR3e bằng LLM + Skill-based Planning

**Sinh viên:** (điền tên) – **MSSV:** 23020736 → P = 36 mod 6 = **0**
→ **Zone A = Red, Zone B = Yellow, Zone C = Blue** (khai báo trong `config/student_config.yaml`).

## Kiến trúc
```
Lệnh tự nhiên → llm_planner (LLM qua 9Router) → JSON plan → validate (skill/object/zone/trạng thái tay gắp)
   → resolve_conflicts (chèn bước dùng zone tạm nếu đích bị chiếm) → /llm_plan
   → skill_executor (validate lần 2) → robot_skills → MoveIt 2 → UR3e (Gazebo)
```
- LLM chỉ chọn/sắp xếp skill: `home, pick, place, move_above, move_to_zone, open_gripper, close_gripper`.
  Skill ngoài danh sách, object/zone lạ → bị từ chối ở cả planner và executor.
- Mọi chuyển động đi qua MoveIt 2: `MoveGroup` (planning có kiểm tra va chạm, joint limit, self-collision),
  `compute_cartesian_path` + `ExecuteTrajectory` (hạ/nâng thẳng), `ApplyPlanningScene` (bàn, khối, attach/detach).
- Trả về: `SUCCESS / FAILED / INVALID_OBJECT / INVALID_ZONE / PLANNING_FAILED`.
- `/world_state` (executor → planner) cho LLM biết vật đang ở đâu.

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
export NINEROUTER_BASE_URL=http://localhost:20128/v1   # kiểm tra đúng cổng trong dashboard
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

## Cần chỉnh khi chạy thực tế
- `config/scene.yaml`: toạ độ vật/zone, `tcp_offset` (chiều dài gripper), `home_joints`, `grasp_orientation`.
  Nếu IK khó giải, dịch vật/zone lại gần base hơn (tầm với UR3 ≈ 0.5 m).
- Gripper: repo chỉ publish `/gripper_close` (Bool). Khối được "cầm" bằng attach trong planning scene MoveIt;
  trong Gazebo khối được dịch chuyển (SetEntityState) tới zone sau `place`. Nếu có gripper vật lý, nối topic này vào controller.
- Tên argument của `ur_sim_control.launch.py` / `ur_moveit.launch.py` có thể khác giữa các bản – kiểm tra bằng `ros2 launch ... --show-args`.
