## 1. System Requirements

Recommended environment:

* Ubuntu 22.04
* ROS 2 Humble Desktop
* Python 3
* Node.js >= 18
* npm
* Git
* Gazebo
* 9Router
* Internet connection
# 2. Install Required ROS 2 Packages
mkdir -p ~/ur_gazebo/src
cd ~/ur_gazebo/src
git clone -b humble https://github.com/UniversalRobots/Universal_Robots_ROS2_Gazebo_Simulation.git

cd ~/ur_gazebo
source /opt/ros/humble/setup.bash
rosdep update
rosdep install --ignore-src --from-paths src -y
colcon build --symlink-install
source ~/ur_gazebo/install/setup.bash

Install the required Universal Robots, Gazebo and MoveIt packages:

```bash
sudo apt update
```

```bash
sudo apt install -y \
ros-humble-ur \
ros-humble-ur-simulation-gazebo \
ros-humble-ur-moveit-config \
ros-humble-moveit \
ros-humble-gazebo-ros-pkgs \
python3-colcon-common-extensions \
python3-rosdep \
git \
curl
```

Initialize rosdep if it has not been initialized before:

```bash
sudo rosdep init
```

If the command reports that rosdep has already been initialized, this step can be skipped.

Then:

```bash
rosdep update
```

---

# 3. Clone the Project

Create a ROS 2 workspace:

```bash
mkdir -p ~/ws_test/src
cd ~/ws_test/src
```

Clone the project:

```bash
git clone https://github.com/23020736-glitch/ur3-llm-control.git
```

Go back to the workspace:

```bash
cd ~/ws_test
```

Check the package:

```bash
ls src/ur3-llm-control
```

---

# 4. Install ROS 2 Dependencies

Source ROS 2:

```bash
source /opt/ros/humble/setup.bash
```

Install dependencies:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

---

# 5. Build the Workspace

Build the project:

```bash
cd ~/ws_test
colcon build
```

If the build finishes successfully, source the workspace:

```bash
source ~/ws_test/install/setup.bash
```

Check that the package is available:

```bash
ros2 pkg list | grep ur3_llm_control
```

Expected output:

```text
ur3_llm_control
```

---

# 6. Install Node.js

9Router requires Node.js version 18 or newer.

It is recommended to use NVM instead of installing Node.js globally with `sudo`.

## 6.1 Install NVM

Run:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
```

After installation, load NVM manually:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

Check NVM:

```bash
nvm --version
```

---

## 6.2 Install Node.js 20

Install Node.js 20:

```bash
nvm install 20
```

Use Node.js 20:

```bash
nvm use 20
```

Check:

```bash
node --version
npm --version
```

Expected Node.js version:

```text
v20.x.x
```

Do not use `sudo npm install` when using NVM.

---

# 7. Install 9Router

Install 9Router:

```bash
npm install -g 9router
```

Check the installation:

```bash
9router --version
```

If a version number is displayed, 9Router has been installed successfully.

---

# 8. Configure 9Router

9Router is used as the API gateway between this ROS 2 project and the selected LLM provider.

## 8.1 Start 9Router

Run:

```bash
9router
```

Keep this terminal open.

The 9Router dashboard should be available at:

```text
http://localhost:20128/dashboard
```

Open the address in a web browser.

---

## 8.2 Connect an LLM Provider

In the 9Router dashboard:

1. Open **Providers**.
2. Connect an available provider.
3. Configure the provider according to its instructions.
4. Go to **Endpoint & Key**.
5. Create an API key.

The API key normally has a format similar to:

```text
sk-xxxxxxxxxxxxxxxx
```
# 9. Configure 9Router Environment Variables

After starting 9Router, open a **new terminal**.

Load NVM:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

Use Node.js 20:

```bash
nvm use 20
```

Load ROS 2:

```bash
source /opt/ros/humble/setup.bash
```

Load this workspace:

```bash
source ~/ws_test/install/setup.bash
```

Set the 9Router URL:

```bash
export NINEROUTER_BASE_URL=http://localhost:20128/v1
```

Set the API key:

```bash
export NINEROUTER_API_KEY="YOUR_9ROUTER_API_KEY"
```

Replace:

```text
YOUR_9ROUTER_API_KEY
```

with the real key created in the 9Router dashboard.

Set the model:

```bash
export NINEROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
```

For example:

```bash
export NINEROUTER_BASE_URL=http://localhost:20128/v1
export NINEROUTER_API_KEY="sk-xxxxxxxxxxxxxxxx"
export NINEROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
```

The real API key must not be committed to GitHub.

---

# 10. Test the 9Router Connection

Before running the ROS 2 planner, test the 9Router API.

Run:

```bash
curl -s http://localhost:20128/v1/models \
  -H "Authorization: Bearer $NINEROUTER_API_KEY"
```

A successful connection should return a JSON response containing available models.

# 11. Start the UR3 Simulation

Open **Terminal 1**.

Load ROS 2:

```bash
source /opt/ros/humble/setup.bash
```

Load the workspace:

```bash
source ~/ws_test/install/setup.bash
```

Start the robot simulation:

```bash
ros2 launch ur3_llm_control llm_robot.launch.py
```

Keep this terminal running.

Gazebo/RViz should start.

---

# 12. Start the LLM Planner

Open **Terminal 2**.

Load NVM:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

Use Node.js 20:

```bash
nvm use 20
```

Load ROS 2:

```bash
source /opt/ros/humble/setup.bash
```

Load the workspace:

```bash
source ~/ws_test/install/setup.bash
```

Configure 9Router:

```bash
export NINEROUTER_BASE_URL=http://localhost:20128/v1
export NINEROUTER_API_KEY="YOUR_9ROUTER_API_KEY"
export NINEROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
```

Start the planner:

```bash
ros2 run ur3_llm_control llm_planner
```

Expected output:

```text
Student 23020736: P=0, target={'zone_a': 'red_cube', 'zone_b': 'yellow_cube', 'zone_c': 'blue_cube'}
Nhap lenh (Ctrl+D de thoat):
>
```

---

# 13. Complete Startup Procedure on a New Machine

After all dependencies have been installed, the normal startup procedure is:

## Terminal 1 — 9Router

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20
9router
```

Keep this terminal open.

---

## Terminal 2 — UR3 Simulation

```bash
source /opt/ros/humble/setup.bash
source ~/ws_test/install/setup.bash
ros2 launch ur3_llm_control llm_robot.launch.py
```

Keep this terminal open.

---

## Terminal 3 — LLM Planner

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20

source /opt/ros/humble/setup.bash
source ~/ws_test/install/setup.bash

export NINEROUTER_BASE_URL=http://localhost:20128/v1
export NINEROUTER_API_KEY="YOUR_9ROUTER_API_KEY"
export NINEROUTER_MODEL="oc/muse-spark-1.3-contributor-free"

ros2 run ur3_llm_control llm_planner
```

Then enter:

```text
Arrange all objects according to my student ID.
```





